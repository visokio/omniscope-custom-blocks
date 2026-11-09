# Jira

Loads the projects in a Jira Cloud site and the issues of a project or a JQL search, one record per issue with its status, people, dates, labels and components.

Jira's own exports are one-off files; reporting on issue flow (what is open, who has what, how long things take) needs the issues as records that refresh. This block reads them from Jira Cloud's REST API each time the workflow runs.

- The **Projects** output lists every project the account can see: id, key, name, type, category, and whether it is team-managed.
- The **Issues** output has one record per issue of the chosen **project key**, of a **JQL filter**, or of both combined.
- Every page of results is loaded (Jira returns 100 issues per request).
- Issue fields come out ready to use: **dates as dates** (UTC), people and statuses **by name**, labels, components and fix versions **joined with commas**.
- **Extra fields**, such as story points (`customfield_10016` on many sites), are added by their Jira field id.

The block uses the API token of one Atlassian account and sees exactly what that account can see.

## Language and libraries

Python. It uses requests (Apache License 2.0) for the HTTP calls and pandas (BSD 3-Clause) for the output. Omniscope installs requests on first run if it is missing (the manifest's `dependencies`); pandas is part of Omniscope's Python environment.

## Inputs

None. The block is a source: it reads from Jira.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Jira site | `jiraInstance` | Text | Your Jira Cloud site: `your-company` for https://your-company.atlassian.net, or the whole address. |
| Username | `username` | Text | The e-mail address you sign in to Atlassian with. |
| API token | `apiKey` | Password | Create one at https://id.atlassian.com/manage-profile/security/api-tokens. |
| Project key | `projectID` | Text | Load the issues of this project, such as `SHOP` (a project id also works). Empty: projects only, or the JQL filter alone. |
| JQL filter | `jql` | Text | Optional Jira Query Language condition, such as `status != Done AND created >= -30d`. Combined with the project key when both are set; may end with `ORDER BY`. |
| Extra fields | `extraFields` | Text | Optional comma-separated field ids to add, such as `customfield_10016, environment`. Objects are written by their name, lists joined with commas. |

## Outputs

- **Projects** (`Projects`): Project ID, Project key, Project name, Project type, Category, Team-managed.
- **Issues** (`Issues`): Key, Issue ID, Project key, Issue type, Summary, Status, Status category, Priority, Assignee, Reporter, Created, Updated, Due date, Resolved, Resolution, Labels, Components, Fix versions, Parent key, then any extra fields. Empty unless a project key or JQL filter is set.

With a project key alone, issues are sorted by key. A JQL filter keeps its own `ORDER BY`; without one, Jira's default order applies.

## Limits

- Jira Cloud only (sites at `atlassian.net`). Jira Data Center and Server use other sign-in methods.
- Descriptions and comments are not loaded; add `description` under Extra fields for the description as text.
- A JQL filter with no condition at all (only `ORDER BY`) is rejected by Jira; give a project key or a condition.
- In tests, 20,000 issues (200 pages of canned responses) loaded in a few seconds; against a real site, time is mostly Jira's response time, one request per 100 issues.

## Source

[script.py](script.py)

The tests in `tests/` run the script against invented Jira responses (`tests/canned/`, written by `tests/make_canned.py`); `sample-data/placeholder.csv` is the Issues output for those responses, for trying a workflow without a Jira site.
