"""Omniscope custom block: Salesforce REST connector.

Authentication: OAuth 2.0 Client Credentials using a Salesforce External Client App.
Data access: Salesforce REST API (SOQL Query / QueryAll, sObjects, Describe).
"""

import json
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import pandas as pd
import requests
from omniscope.api import OmniscopeApi


class SalesforceConnectorError(RuntimeError):
    pass


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FIELD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def option(api: OmniscopeApi, name: str, default: Any = None) -> Any:
    value = api.get_option(name)
    if value is None:
        return default
    if isinstance(value, str) and value.strip() == "":
        return default
    return value


def required_option(api: OmniscopeApi, name: str, title: str) -> str:
    value = option(api, name)
    if value is None:
        raise SalesforceConnectorError("%s is required." % title)
    value = str(value).strip()
    if not value:
        raise SalesforceConnectorError("%s is required." % title)
    return value


def positive_int(value: Any, title: str, default: int, allow_zero: bool = False) -> int:
    if value is None or str(value).strip() == "":
        return default
    try:
        parsed = int(str(value).strip())
    except ValueError:
        raise SalesforceConnectorError("%s must be an integer." % title)
    minimum = 0 if allow_zero else 1
    if parsed < minimum:
        if allow_zero:
            raise SalesforceConnectorError("%s must be 0 or greater." % title)
        raise SalesforceConnectorError("%s must be greater than 0." % title)
    return parsed


def normalize_base_url(raw_url: str) -> str:
    url = raw_url.strip().rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise SalesforceConnectorError(
            "Salesforce My Domain URL must be a valid HTTPS URL, for example "
            "https://acme.my.salesforce.com."
        )
    return url


def normalize_api_version(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    value = str(raw).strip().lower()
    if not value or value == "auto":
        return None
    if value.startswith("v"):
        value = value[1:]
    if not re.match(r"^\d+(?:\.\d+)?$", value):
        raise SalesforceConnectorError(
            "API version must be 'auto' or a number such as 67.0."
        )
    if "." not in value:
        value += ".0"
    return "v" + value


def response_error(response: requests.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        text = (response.text or "").strip()
        return text[:1000] if text else "No response body"

    if isinstance(payload, list):
        parts = []
        for item in payload[:5]:
            if isinstance(item, dict):
                code = item.get("errorCode") or item.get("error")
                message = item.get("message") or item.get("error_description")
                parts.append("%s: %s" % (code, message) if code else str(message or item))
            else:
                parts.append(str(item))
        return "; ".join(parts)[:1000]

    if isinstance(payload, dict):
        code = payload.get("errorCode") or payload.get("error")
        message = payload.get("message") or payload.get("error_description")
        if code or message:
            return ("%s: %s" % (code, message) if code else str(message))[:1000]
        return json.dumps(payload, ensure_ascii=False)[:1000]

    return str(payload)[:1000]


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    timeout: int,
    *,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    data: Optional[Dict[str, str]] = None,
    max_attempts: int = 4,
) -> Any:
    last_error: Optional[str] = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = session.request(
                method,
                url,
                headers=headers,
                params=params,
                data=data,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            last_error = str(exc)
            if attempt == max_attempts:
                break
            time.sleep(min(2 ** (attempt - 1), 8))
            continue

        if response.ok:
            try:
                return response.json()
            except ValueError as exc:
                raise SalesforceConnectorError(
                    "Salesforce returned a non-JSON response from %s: %s" % (url, exc)
                )

        error_text = response_error(response)
        last_error = "HTTP %s - %s" % (response.status_code, error_text)

        # Retry rate limits and transient Salesforce/server failures.
        if response.status_code == 429 or 500 <= response.status_code <= 599:
            if attempt < max_attempts:
                retry_after = response.headers.get("Retry-After")
                try:
                    wait = float(retry_after) if retry_after else min(2 ** (attempt - 1), 8)
                except ValueError:
                    wait = min(2 ** (attempt - 1), 8)
                time.sleep(max(0.0, min(wait, 30.0)))
                continue

        raise SalesforceConnectorError("Salesforce request failed: %s" % last_error)

    raise SalesforceConnectorError(
        "Salesforce request failed after %d attempts: %s" % (max_attempts, last_error or "unknown error")
    )


def authenticate_client_credentials(
    session: requests.Session,
    auth_base_url: str,
    client_id: str,
    client_secret: str,
    timeout: int,
) -> Tuple[str, str]:
    token_url = auth_base_url + "/services/oauth2/token"
    payload = request_json(
        session,
        "POST",
        token_url,
        timeout,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )

    if not isinstance(payload, dict):
        raise SalesforceConnectorError("Unexpected OAuth token response from Salesforce.")

    access_token = payload.get("access_token")
    instance_url = payload.get("instance_url")
    if not access_token or not instance_url:
        raise SalesforceConnectorError(
            "OAuth succeeded but the token response did not include access_token and instance_url."
        )
    return str(access_token), str(instance_url).rstrip("/")


def discover_latest_api_version(
    session: requests.Session,
    instance_url: str,
    headers: Dict[str, str],
    timeout: int,
) -> str:
    versions = request_json(
        session,
        "GET",
        instance_url + "/services/data/",
        timeout,
        headers=headers,
    )
    if not isinstance(versions, list) or not versions:
        raise SalesforceConnectorError("Could not discover Salesforce REST API versions.")

    candidates = []
    for item in versions:
        if not isinstance(item, dict):
            continue
        version = item.get("version")
        try:
            numeric = float(version)
        except (TypeError, ValueError):
            continue
        candidates.append((numeric, "v" + str(version)))

    if not candidates:
        raise SalesforceConnectorError("Salesforce returned no usable REST API version.")
    candidates.sort(key=lambda x: x[0])
    return candidates[-1][1]


def flatten_record(record: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """Flatten Salesforce relationship objects into dotted column names."""
    flat: Dict[str, Any] = {}
    for key, value in record.items():
        if key == "attributes":
            continue
        column = "%s.%s" % (prefix, key) if prefix else key
        if isinstance(value, dict):
            nested = {k: v for k, v in value.items() if k != "attributes"}
            if nested:
                flat.update(flatten_record(nested, column))
            else:
                flat[column] = None
        elif isinstance(value, list):
            flat[column] = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        else:
            flat[column] = value
    return flat


def validate_builder_fields(object_name: str, fields_text: str) -> List[str]:
    if not _IDENTIFIER_RE.match(object_name):
        raise SalesforceConnectorError(
            "Object API name is invalid. Use an API name such as Account or CustomObject__c."
        )

    fields = [field.strip() for field in fields_text.split(",") if field.strip()]
    if not fields:
        raise SalesforceConnectorError("At least one field is required in Query Builder mode.")
    invalid = [field for field in fields if not _FIELD_RE.match(field)]
    if invalid:
        raise SalesforceConnectorError(
            "Invalid field API name(s) in Query Builder mode: %s. "
            "Use Custom SOQL mode for expressions or aggregate functions." % ", ".join(invalid[:10])
        )
    return fields


def build_soql(
    object_name: str,
    fields_text: str,
    where_clause: Optional[str],
    order_by: Optional[str],
) -> str:
    fields = validate_builder_fields(object_name, fields_text)
    query = "SELECT %s FROM %s" % (", ".join(fields), object_name)
    if where_clause:
        query += " WHERE " + where_clause.strip()
    if order_by:
        query += " ORDER BY " + order_by.strip()
    return query


def query_records(
    session: requests.Session,
    instance_url: str,
    api_version: str,
    headers: Dict[str, str],
    timeout: int,
    soql: str,
    include_deleted: bool,
    max_records: int,
    api: OmniscopeApi,
) -> List[Dict[str, Any]]:
    endpoint = "queryAll" if include_deleted else "query"
    url = "%s/services/data/%s/%s" % (instance_url, api_version, endpoint)
    params: Optional[Dict[str, str]] = {"q": soql}
    records: List[Dict[str, Any]] = []

    while url:
        payload = request_json(
            session,
            "GET",
            url,
            timeout,
            headers=headers,
            params=params,
        )
        params = None  # nextRecordsUrl already contains the query locator

        if not isinstance(payload, dict):
            raise SalesforceConnectorError("Unexpected response from Salesforce Query API.")

        page_records = payload.get("records") or []
        if not isinstance(page_records, list):
            raise SalesforceConnectorError("Salesforce Query API returned an invalid records payload.")

        for record in page_records:
            if isinstance(record, dict):
                records.append(flatten_record(record))
                if max_records and len(records) >= max_records:
                    return records

        api.update_message("Salesforce: loaded %s records" % format(len(records), ","))

        if payload.get("done") is True:
            break
        next_url = payload.get("nextRecordsUrl")
        if not next_url:
            break
        if str(next_url).startswith("http"):
            url = str(next_url)
        else:
            url = instance_url + str(next_url)

    return records


def get_object_description(
    session: requests.Session,
    instance_url: str,
    api_version: str,
    headers: Dict[str, str],
    timeout: int,
    object_name: str,
) -> Dict[str, Any]:
    """Return Salesforce Describe metadata for one sObject."""
    if not _IDENTIFIER_RE.match(object_name):
        raise SalesforceConnectorError("Object API name is invalid.")

    payload = request_json(
        session,
        "GET",
        "%s/services/data/%s/sobjects/%s/describe" % (instance_url, api_version, object_name),
        timeout,
        headers=headers,
    )
    if not isinstance(payload, dict):
        raise SalesforceConnectorError(
            "Salesforce returned an unexpected Describe response for %s." % object_name
        )
    return payload


def discover_object_fields(
    session: requests.Session,
    instance_url: str,
    api_version: str,
    headers: Dict[str, str],
    timeout: int,
    object_name: str,
) -> List[str]:
    """Discover all readable field API names exposed by sObject Describe.

    Describe is permission-aware, so the returned fields reflect what the OAuth
    Run As user can see. Deprecated/hidden fields are skipped. The resulting
    names are used to generate a normal REST SOQL SELECT statement; FIELDS(ALL)
    is deliberately not used because Salesforce bounds that form of query.
    """
    payload = get_object_description(
        session, instance_url, api_version, headers, timeout, object_name
    )
    fields = payload.get("fields") or []
    names: List[str] = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        if field.get("deprecatedAndHidden") is True:
            continue
        name = field.get("name")
        if isinstance(name, str) and _FIELD_RE.match(name):
            names.append(name)

    # Preserve Describe order while removing any accidental duplicates.
    names = list(dict.fromkeys(names))
    if not names:
        raise SalesforceConnectorError(
            "Salesforce Describe returned no readable fields for %s. Check the Run As user's object and field permissions."
            % object_name
        )
    return names


def build_all_fields_soql(object_name: str, field_names: List[str]) -> str:
    if not _IDENTIFIER_RE.match(object_name):
        raise SalesforceConnectorError("Object API name is invalid.")
    if not field_names:
        raise SalesforceConnectorError("No Salesforce fields were discovered for %s." % object_name)
    return "SELECT %s FROM %s" % (", ".join(field_names), object_name)


def list_objects(
    session: requests.Session,
    instance_url: str,
    api_version: str,
    headers: Dict[str, str],
    timeout: int,
) -> pd.DataFrame:
    payload = request_json(
        session,
        "GET",
        "%s/services/data/%s/sobjects" % (instance_url, api_version),
        timeout,
        headers=headers,
    )
    objects = payload.get("sobjects", []) if isinstance(payload, dict) else []
    rows = []
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        rows.append(
            {
                "name": obj.get("name"),
                "label": obj.get("label"),
                "labelPlural": obj.get("labelPlural"),
                "keyPrefix": obj.get("keyPrefix"),
                "queryable": obj.get("queryable"),
                "retrieveable": obj.get("retrieveable"),
                "searchable": obj.get("searchable"),
                "createable": obj.get("createable"),
                "updateable": obj.get("updateable"),
                "deletable": obj.get("deletable"),
                "custom": obj.get("custom"),
            }
        )
    return pd.DataFrame(rows)


def describe_fields(
    session: requests.Session,
    instance_url: str,
    api_version: str,
    headers: Dict[str, str],
    timeout: int,
    object_name: str,
) -> pd.DataFrame:
    payload = get_object_description(
        session, instance_url, api_version, headers, timeout, object_name
    )
    fields = payload.get("fields", []) if isinstance(payload, dict) else []
    rows = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        rows.append(
            {
                "name": field.get("name"),
                "label": field.get("label"),
                "type": field.get("type"),
                "length": field.get("length"),
                "precision": field.get("precision"),
                "scale": field.get("scale"),
                "nillable": field.get("nillable"),
                "unique": field.get("unique"),
                "externalId": field.get("externalId"),
                "calculated": field.get("calculated"),
                "createable": field.get("createable"),
                "updateable": field.get("updateable"),
                "filterable": field.get("filterable"),
                "sortable": field.get("sortable"),
                "groupable": field.get("groupable"),
                "relationshipName": field.get("relationshipName"),
                "referenceTo": ",".join(field.get("referenceTo") or []),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    api = OmniscopeApi()
    try:
        auth_base_url = normalize_base_url(required_option(api, "authBaseUrl", "Salesforce My Domain URL"))
        client_id = required_option(api, "clientId", "OAuth Client ID / Consumer Key")
        client_secret = required_option(api, "clientSecret", "OAuth Client Secret / Consumer Secret")
        timeout = positive_int(option(api, "timeoutSeconds", "60"), "HTTP timeout", 60)
        max_records = positive_int(option(api, "maxRecords", "100000"), "Maximum records", 100000, allow_zero=True)

        operation = str(option(api, "operation", "query")).strip()
        api.update_message("Salesforce: authenticating with OAuth 2.0")

        session = requests.Session()
        session.headers.update({"Accept": "application/json", "Accept-Encoding": "gzip"})
        access_token, instance_url = authenticate_client_credentials(
            session,
            auth_base_url,
            client_id,
            client_secret,
            timeout,
        )
        headers = {"Authorization": "Bearer " + access_token}

        requested_version = normalize_api_version(option(api, "apiVersion", "auto"))
        if requested_version is None:
            api.update_message("Salesforce: discovering REST API version")
            api_version = discover_latest_api_version(session, instance_url, headers, timeout)
        else:
            api_version = requested_version

        api.update_message("Salesforce: using REST API %s" % api_version)

        if operation == "list_objects":
            output = list_objects(session, instance_url, api_version, headers, timeout)
            api.write_output_records(output, output_number=0)
            api.close(message="Loaded %s Salesforce objects using REST API %s." % (len(output), api_version))
            return

        object_name = str(option(api, "objectName", "Account")).strip()

        if operation == "describe_fields":
            output = describe_fields(session, instance_url, api_version, headers, timeout, object_name)
            api.write_output_records(output, output_number=0)
            api.close(
                message="Loaded %s field definitions for %s using REST API %s."
                % (len(output), object_name, api_version)
            )
            return

        if operation != "query":
            raise SalesforceConnectorError("Unknown operation: %s" % operation)

        query_mode = str(option(api, "queryMode", "simple")).strip()
        if query_mode == "simple":
            simple_object = str(option(api, "simpleObject", "Account")).strip()
            api.update_message("Salesforce: discovering fields for %s" % simple_object)
            field_names = discover_object_fields(
                session, instance_url, api_version, headers, timeout, simple_object
            )
            soql = build_all_fields_soql(simple_object, field_names)
            object_name = simple_object
            api.update_message(
                "Salesforce: found %s fields for %s" % (format(len(field_names), ","), simple_object)
            )
        elif query_mode == "builder":
            fields_text = str(option(api, "fields", "Id, Name"))
            where_clause = option(api, "whereClause")
            order_by = option(api, "orderBy")
            soql = build_soql(object_name, fields_text, where_clause, order_by)
        elif query_mode == "soql":
            soql = required_option(api, "soql", "SOQL query")
        else:
            raise SalesforceConnectorError("Unknown query mode: %s" % query_mode)

        include_deleted = str(option(api, "includeDeleted", "false")).lower() == "true"
        api.update_message("Salesforce: loading %s via REST API" % object_name)
        records = query_records(
            session,
            instance_url,
            api_version,
            headers,
            timeout,
            soql,
            include_deleted,
            max_records,
            api,
        )

        if records:
            output = pd.DataFrame.from_records(records)
            api.write_output_records(output, output_number=0)
            api.close(
                message="Loaded %s Salesforce records using REST API %s."
                % (format(len(output), ","), api_version)
            )
        else:
            api.close(message="Salesforce query returned 0 records using REST API %s." % api_version)

    except SystemExit:
        raise
    except Exception as exc:
        # Do not include credentials or request bodies in errors/logs.
        api.abort(message="Salesforce connector failed: %s" % str(exc))


if __name__ == "__main__":
    main()
