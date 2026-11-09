# Web Form Session Login

Logs in to a website through its HTML login form, as a browser would, and outputs the session cookies and every response header, for later HTTP requests that need the session.

Some portals and older web applications have no API key: data can only be fetched after logging in through a form, which sets a session cookie. This block does that login on the Omniscope server and outputs the cookies, so the requests that follow (for example a File block reading a CSV export from the portal) can send them.

- Loads the login page in a session, keeping its cookies and **hidden fields** such as anti-forgery tokens.
- Finds the **login form** (the form with a password field, so a search or newsletter form earlier on the page is not used) and the likeliest **user name or e-mail field**.
- Submits the form and **follows the redirects**, sending the new cookies at each step.
- **Stops with a message** when the site answers the login with an error status, or still shows a password field afterwards (a wrong password, usually). Untick **Stop if the login fails** to get the outputs anyway, for diagnosis.

The outputs hold a live session: anyone with the cookie values can act as the logged-in user until the session ends. Treat them like a password and do not publish them in a Report.

## Language and libraries

Python, with requests (Apache License 2.0) for the HTTP session, Beautiful Soup 4 (MIT) to read the login form, and pandas (BSD 3-Clause). pandas is part of Omniscope's Python environment; Omniscope installs requests and beautifulsoup4 with pip on first run if they are missing (the manifest's `dependencies`).

## Inputs

None.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Login page URL | `url` | Text | The address of the page with the login form. |
| User name | `username` | Text | Typed into the form's user name or e-mail field. |
| Password | `password` | Password | Typed into the form's password field. |
| Stop if the login fails | `checkLogin` | Yes/no | Ticked (the default): stop on an error status (400 or above) or a password field still shown after the login. |

## Outputs

- **Headers** (`Headers`): one record per response header of every request and redirect: Stage (`GET login page` or `POST login`), Hop, Request method, Request URL, Request Cookie header, Status code, Reason, Is redirect, Redirect location, Header name, Header occurrence (for repeated headers such as Set-Cookie), Header value, Is Set-Cookie.
- **Cookies** (`Cookies`): Cookie name, Cookie value, Domain, Path, Secure, Expires (UTC; empty for session cookies), Additional attributes (such as HttpOnly, as JSON).

## Limits

- HTML forms only: logins built in JavaScript, with a CAPTCHA, or with a second step (a code by text message or an authenticator app) cannot be done this way.
- The user name field is guessed from the field's type and name (`email`, `username`, `login`, `user`); a form with several text fields may need the script adjusted.
- The block sends a desktop browser's User-Agent; some sites still refuse automated logins.
- Check that the site's terms allow automated access.

## Source

[script.py](script.py)

The tests in `tests/` log in to a small fake portal on the test machine, which serves the invented pages in `tests/canned/`. `sample-data/placeholder.csv` is the Cookies output of a successful login to it (domain changed to `portal.example.com`), for trying a workflow without a site.
