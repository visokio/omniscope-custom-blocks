from omniscope.api import OmniscopeApi

import json
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TIMEOUT_SECONDS = 30

# Set to False only while diagnosing the original 303 response.
FOLLOW_REDIRECTS = True


# ---------------------------------------------------------------------------
# Omniscope setup and options
# ---------------------------------------------------------------------------

omniscope_api = OmniscopeApi()

login_url = omniscope_api.get_option("url")
username = omniscope_api.get_option("username")
password = omniscope_api.get_option("password")
check_login = omniscope_api.get_option("checkLogin")
check_login = True if check_login is None else bool(check_login)

if not login_url:
    omniscope_api.abort(message="The Login URL option is required.")

if not username:
    omniscope_api.abort(message="The Username option is required.")

if password is None:
    omniscope_api.abort(message="The Password option is required.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_raw_header_pairs(response):
    """
    Return every response header while preserving repeated headers.

    This matters for Set-Cookie because a response can contain multiple
    separate Set-Cookie headers.
    """
    pairs = []

    raw_response = getattr(response, "raw", None)
    raw_headers = getattr(raw_response, "headers", None)

    if raw_headers is not None and hasattr(raw_headers, "getlist"):
        for header_name in raw_headers.keys():
            header_values = raw_headers.getlist(header_name)

            for header_position, header_value in enumerate(
                header_values,
                start=1,
            ):
                pairs.append(
                    (
                        str(header_name),
                        str(header_value),
                        header_position,
                    )
                )

        return pairs

    # Fallback if the underlying HTTP client does not expose raw headers.
    for header_name, header_value in response.headers.items():
        pairs.append(
            (
                str(header_name),
                str(header_value),
                1,
            )
        )

    return pairs


def collect_response_headers(stage, response):
    """
    Produce one output row per header for the complete redirect chain.
    """
    rows = []

    complete_chain = list(response.history) + [response]

    for hop_number, hop_response in enumerate(complete_chain):
        request = hop_response.request

        request_cookie = request.headers.get("Cookie", "")
        location = hop_response.headers.get("Location", "")

        header_pairs = get_raw_header_pairs(hop_response)

        # Normally every HTTP response has headers. Keep one status-only row
        # if the server somehow returned none.
        if not header_pairs:
            header_pairs = [("", "", 1)]

        for header_name, header_value, header_position in header_pairs:
            rows.append(
                {
                    "Stage": stage,
                    "Hop": hop_number,
                    "Request method": request.method,
                    "Request URL": request.url,
                    "Request Cookie header": request_cookie,
                    "Status code": int(hop_response.status_code),
                    "Reason": str(hop_response.reason or ""),
                    "Is redirect": bool(hop_response.is_redirect),
                    "Redirect location": location,
                    "Header name": header_name,
                    "Header occurrence": int(header_position),
                    "Header value": header_value,
                    "Is Set-Cookie": (
                        header_name.lower() == "set-cookie"
                    ),
                }
            )

    return rows


def has_password_input(form):
    return any(
        str(element.get("type", "")).lower() == "password"
        for element in form.find_all("input")
    )


def find_login_form(html, page_url):
    """
    Locate the login form: the first form with a password field (a POST
    one first). A search or newsletter form earlier in the page is not
    a login form. Fall back to the first POST form.
    """
    soup = BeautifulSoup(html, "html.parser")
    forms = soup.find_all("form")

    def is_post(form):
        return str(form.get("method", "get")).lower() == "post"

    for form in forms:
        if has_password_input(form) and is_post(form):
            return form

    for form in forms:
        if has_password_input(form):
            return form

    for form in forms:
        if is_post(form):
            return form

    return None


def score_username_input(input_element):
    """
    Give likely username/email fields a score.
    """
    input_type = str(input_element.get("type", "text")).lower()

    if input_type not in ("text", "email", "tel", ""):
        return -1

    name = str(input_element.get("name", "")).lower()
    element_id = str(input_element.get("id", "")).lower()
    autocomplete = str(
        input_element.get("autocomplete", "")
    ).lower()

    searchable = " ".join([name, element_id, autocomplete])

    score = 0

    if input_type == "email":
        score += 20

    if "username" in searchable:
        score += 30

    if "user_login" in searchable:
        score += 30

    if "login" in searchable:
        score += 15

    if "email" in searchable:
        score += 15

    if "user" in searchable:
        score += 10

    if autocomplete == "username":
        score += 30

    return score


def build_login_payload(form, username_value, password_value):
    """
    Preserve hidden inputs such as CSRF tokens, then add the username
    and password using the fields detected from the HTML form.
    """
    payload = {}

    for input_element in form.find_all("input"):
        field_name = input_element.get("name")

        if not field_name:
            continue

        input_type = str(
            input_element.get("type", "text")
        ).lower()

        if input_type == "hidden":
            payload[field_name] = input_element.get("value", "")

    password_element = next(
        (
            element
            for element in form.find_all("input")
            if str(element.get("type", "")).lower() == "password"
        ),
        None,
    )

    if password_element is None or not password_element.get("name"):
        raise RuntimeError(
            "Could not locate a named password field in the login form."
        )

    password_field = password_element.get("name")

    username_candidates = []

    for input_element in form.find_all("input"):
        field_name = input_element.get("name")

        if not field_name:
            continue

        score = score_username_input(input_element)

        if score >= 0:
            username_candidates.append(
                (score, input_element)
            )

    username_candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    if username_candidates:
        username_element = username_candidates[0][1]
        username_field = username_element.get("name")
    else:
        # Common fallback. Change this if the login page is unusual.
        username_field = "username"

    payload[username_field] = username_value
    payload[password_field] = password_value

    # Submit buttons can carry a required name/value.
    submit_element = form.find(
        ["input", "button"],
        attrs={"type": "submit"},
    )

    if submit_element is not None:
        submit_name = submit_element.get("name")

        if submit_name:
            payload[submit_name] = submit_element.get(
                "value",
                submit_element.get_text(strip=True),
            )

    return payload, username_field, password_field


def cookie_rows_from_session(session):
    rows = []

    for cookie in session.cookies:
        rows.append(
            {
                "Cookie name": str(cookie.name),
                "Cookie value": str(cookie.value),
                "Domain": str(cookie.domain or ""),
                "Path": str(cookie.path or ""),
                "Secure": bool(cookie.secure),
                # Seconds since 1970 in the cookie jar; a date (UTC) in the output.
                # Session cookies (no expiry) are empty.
                "Expires": (
                    pd.Timestamp(int(cookie.expires), unit="s")
                    if cookie.expires is not None
                    else pd.NaT
                ),
                "Additional attributes": json.dumps(
                    getattr(cookie, "_rest", {}),
                    default=str,
                ),
            }
        )

    return rows


# ---------------------------------------------------------------------------
# Execute browser-style login
# ---------------------------------------------------------------------------

header_rows = []

session = requests.Session()

session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.8",
    }
)

try:
    omniscope_api.update_message(
        "Loading the login page and establishing the session..."
    )

    # Step 1: load the login page. This captures initial cookies and CSRF data.
    login_page_response = session.get(
        login_url,
        timeout=TIMEOUT_SECONDS,
        allow_redirects=True,
    )

    header_rows.extend(
        collect_response_headers(
            "GET login page",
            login_page_response,
        )
    )

    login_page_response.raise_for_status()

    login_form = find_login_form(
        login_page_response.text,
        login_page_response.url,
    )

    if login_form is None:
        raise RuntimeError(
            "No HTML login form containing a POST or password field "
            "was found at the supplied URL."
        )

    form_action = login_form.get("action") or login_page_response.url

    post_url = urljoin(
        login_page_response.url,
        form_action,
    )

    payload, username_field, password_field = build_login_payload(
        login_form,
        username,
        password,
    )

    omniscope_api.update_message(
        "Submitting the login form and inspecting redirects..."
    )

    # Step 2: submit credentials in the SAME requests.Session.
    # requests.Session stores Set-Cookie values and sends them on redirects.
    login_response = session.post(
        post_url,
        data=payload,
        timeout=TIMEOUT_SECONDS,
        allow_redirects=FOLLOW_REDIRECTS,
        headers={
            "Referer": login_page_response.url,
            "Origin": (
                requests.utils.urlparse(post_url).scheme
                + "://"
                + requests.utils.urlparse(post_url).netloc
            ),
        },
    )

    header_rows.extend(
        collect_response_headers(
            "POST login",
            login_response,
        )
    )

    headers_df = pd.DataFrame(
        header_rows,
        columns=[
            "Stage",
            "Hop",
            "Request method",
            "Request URL",
            "Request Cookie header",
            "Status code",
            "Reason",
            "Is redirect",
            "Redirect location",
            "Header name",
            "Header occurrence",
            "Header value",
            "Is Set-Cookie",
        ],
    )

    if check_login:
        if login_response.status_code >= 400:
            raise RuntimeError(
                f"The site answered the login with status "
                f"{login_response.status_code} {login_response.reason or ''}"
                f"; the login failed. Untick 'Stop if the login fails' "
                f"to see the headers."
            )

        final_page = BeautifulSoup(login_response.text, "html.parser")
        if any(has_password_input(form) for form in final_page.find_all("form")):
            raise RuntimeError(
                "After logging in, the site still shows a form with a "
                "password field, so the login probably failed (wrong "
                "user name or password, or a form this block cannot "
                f"fill in). Fields used: {username_field}, "
                f"{password_field}. Untick 'Stop if the login fails' "
                "to see the headers anyway."
            )

    cookie_rows = cookie_rows_from_session(session)

    cookies_df = pd.DataFrame(
        cookie_rows,
        columns=[
            "Cookie name",
            "Cookie value",
            "Domain",
            "Path",
            "Secure",
            "Expires",
            "Additional attributes",
        ],
    )
    cookies_df["Expires"] = pd.to_datetime(cookies_df["Expires"])

    # Output 1: every header from every request/redirect response.
    omniscope_api.write_output(
        headers_df,
        "Headers",
    )

    # Output 2: the resulting persistent session cookie jar.
    omniscope_api.write_output(
        cookies_df,
        "Cookies",
    )

    redirect_count = len(login_response.history)

    omniscope_api.commit(
        message=(
            f"Login request completed with status "
            f"{login_response.status_code}; "
            f"{redirect_count} redirect(s); "
            f"{len(cookie_rows)} cookie(s). "
            f"Detected fields: {username_field}, {password_field}."
        )
    )

except requests.RequestException as error:
    omniscope_api.abort(
        message=f"HTTP request failed: {error}"
    )

except Exception as error:
    omniscope_api.abort(
        message=f"Login block failed: {error}"
    )