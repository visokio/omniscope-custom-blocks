"""Jira connector: loads the projects visible to an account, and the issues of a project or a JQL search,
from Jira Cloud's REST API (version 2, with the enhanced JQL search)."""
import json
import re

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

PAGE_SIZE = 100
TIMEOUT = 60

# The issue fields every run returns, in output order: (field id in Jira, output field name, how to read it)
ISSUE_FIELDS = [
    ("project", "Project key", "key"),
    ("issuetype", "Issue type", "name"),
    ("summary", "Summary", None),
    ("status", "Status", "name"),
    ("status", "Status category", "category"),
    ("priority", "Priority", "name"),
    ("assignee", "Assignee", "displayName"),
    ("reporter", "Reporter", "displayName"),
    ("created", "Created", "date"),
    ("updated", "Updated", "date"),
    ("duedate", "Due date", "date"),
    ("resolutiondate", "Resolved", "date"),
    ("resolution", "Resolution", "name"),
    ("labels", "Labels", "list"),
    ("components", "Components", "list"),
    ("fixVersions", "Fix versions", "list"),
    ("parent", "Parent key", "key"),
]
PROJECT_COLUMNS = ["Project ID", "Project key", "Project name", "Project type", "Category", "Team-managed"]


def option_text(name):
    value = omniscope_api.get_option(name)
    if value is None:
        return ""
    return str(value).strip()


def base_url(instance):
    """Accepts "acme", "acme.atlassian.net" or "https://acme.atlassian.net/..." and returns the site URL."""
    instance = instance.strip().rstrip("/")
    if re.match(r"^https?://", instance, re.I):
        m = re.match(r"^(https?://[^/]+)", instance, re.I)
        return m.group(1)
    if "." in instance:
        return "https://" + instance.split("/")[0]
    return f"https://{instance}.atlassian.net"


class JiraAPI:
    def __init__(self, url, username, api_token):
        self.url = url
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, api_token)
        self.session.headers.update({"Accept": "application/json"})

    def get(self, path, params=None):
        response = self.session.get(self.url + path, params=params, timeout=TIMEOUT)
        if response.status_code in (401, 403):
            omniscope_api.abort(
                f"Jira refused the request ({response.status_code}). Check the username (your Atlassian e-mail "
                "address) and the API token, and that the account can see the project.")
        if not response.ok:
            omniscope_api.abort(f"Jira returned {response.status_code} for {path}: {error_text(response)}")
        return response.json()

    def get_projects(self):
        projects, start = [], 0
        while True:
            page = self.get("/rest/api/2/project/search",
                            {"startAt": start, "maxResults": PAGE_SIZE, "expand": "projectCategory"})
            values = page.get("values") or []
            projects.extend(values)
            start += len(values)
            if page.get("isLast", True) or not values:
                return projects

    def search_issues(self, jql, field_ids):
        issues, token = [], None
        while True:
            params = {"jql": jql, "maxResults": PAGE_SIZE, "fields": ",".join(field_ids)}
            if token:
                params["nextPageToken"] = token
            page = self.get("/rest/api/2/search/jql", params)
            issues.extend(page.get("issues") or [])
            omniscope_api.update_message(f"Jira: loaded {len(issues):,} issues")
            token = page.get("nextPageToken")
            if page.get("isLast", True) or not token:
                return issues


def error_text(response):
    try:
        body = response.json()
    except ValueError:
        return (response.text or "").strip()[:500]
    messages = list(body.get("errorMessages") or []) + [f"{k}: {v}" for k, v in (body.get("errors") or {}).items()]
    return "; ".join(messages)[:500] or json.dumps(body)[:500]


def readable(value):
    """A Jira field value as one text value: names of objects, lists joined with commas."""
    if value is None:
        return None
    if isinstance(value, list):
        parts = [readable(v) for v in value]
        return ", ".join(p for p in parts if p not in (None, "")) or None
    if isinstance(value, dict):
        for key in ("displayName", "name", "value", "key"):
            if value.get(key) not in (None, ""):
                return str(value[key])
        return json.dumps(value, ensure_ascii=False)
    return value


def read_field(value, how):
    if value is None:
        return None
    if how is None:
        return value
    if how == "category":
        return (value.get("statusCategory") or {}).get("name")
    if how == "list":
        return readable(value)
    if how == "date":
        return value
    return value.get(how)


def to_dates(df, columns):
    for c in columns:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], utc=True, errors="coerce", format="ISO8601")
    return df


def issues_frame(issues, extra_fields):
    rows = []
    for issue in issues:
        fields = issue.get("fields") or {}
        row = {"Key": issue.get("key"), "Issue ID": issue.get("id")}
        for field_id, column, how in ISSUE_FIELDS:
            row[column] = read_field(fields.get(field_id), how)
        for field_id in extra_fields:
            row[field_id] = readable(fields.get(field_id))
        rows.append(row)
    columns = ["Key", "Issue ID"] + [c for _, c, _ in ISSUE_FIELDS] + list(extra_fields)
    df = pd.DataFrame(rows, columns=columns)
    for c in columns:
        if df[c].isna().all():
            df[c] = df[c].astype(object)
    return to_dates(df, ["Created", "Updated", "Due date", "Resolved"])


def projects_frame(projects):
    rows = [{
        "Project ID": p.get("id"),
        "Project key": p.get("key"),
        "Project name": p.get("name"),
        "Project type": p.get("projectTypeKey"),
        "Category": (p.get("projectCategory") or {}).get("name"),
        "Team-managed": p.get("style") == "next-gen" if p.get("style") else None,
    } for p in projects]
    return pd.DataFrame(rows, columns=PROJECT_COLUMNS)


def build_jql(project, jql_filter):
    parts = []
    if project:
        parts.append('project = "%s"' % project.replace('"', '\\"'))
    if jql_filter:
        order = re.search(r"\border\s+by\b", jql_filter, re.I)
        condition = jql_filter[:order.start()].strip() if order else jql_filter
        if condition:
            parts.append(f"({condition})" if project else condition)
        return " AND ".join(parts) + (" " + jql_filter[order.start():] if order else "")
    return " AND ".join(parts) + " ORDER BY key ASC"


instance = option_text("jiraInstance")
username = option_text("username")
api_token = option_text("apiKey")
project = option_text("projectID")
jql_filter = option_text("jql")
extra_fields = [f.strip() for f in option_text("extraFields").split(",") if f.strip()]

if not instance or not username or not api_token:
    omniscope_api.abort("Enter the Jira site, the username and the API token.")

jira = JiraAPI(base_url(instance), username, api_token)

omniscope_api.update_message("Jira: loading projects")
omniscope_api.write_output_records(projects_frame(jira.get_projects()), output_number=0)

issue_count = None
if project or jql_filter:
    jql = build_jql(project, jql_filter)
    field_ids = list(dict.fromkeys([f for f, _, _ in ISSUE_FIELDS] + extra_fields))
    issues = issues_frame(jira.search_issues(jql, field_ids), extra_fields)
    issue_count = len(issues)
    omniscope_api.write_output_records(issues, output_number=1)

if issue_count is None:
    omniscope_api.close("Projects loaded. Enter a project key or a JQL filter to load issues.")
else:
    omniscope_api.close(f"Loaded {issue_count:,} issues.")
