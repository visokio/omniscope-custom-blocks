"""Writes the invented Jira API responses in tests/canned/ that the tests (and sample-data/placeholder.csv) use.

Run from the block folder: python3 tests/make_canned.py
"""

import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "canned")
rng = random.Random(7)

people = ["Priya Natarajan", "Tom Okafor", "Elena Rossi", "Sam Whitfield", "Hannah Lowe"]
statuses = [("To Do", "To Do"), ("In Progress", "In Progress"), ("In Review", "In Progress"), ("Done", "Done")]
types = ["Story", "Bug", "Task"]
priorities = ["Highest", "High", "Medium", "Low"]
components = ["Checkout", "Search", "Accounts", "Mobile app"]
summaries = [
    "Basket total ignores voucher after page refresh",
    "Add postcode lookup to delivery form",
    "Search results slow for long queries",
    "Password reset e-mail goes to spam",
    "Show stock level on product page",
    "Mobile app crashes on order history",
    "Export order list to CSV",
    "Wrong VAT rate on gift cards",
    "Remember last used delivery address",
    "Filter search by brand",
    "Order confirmation shows wrong delivery date",
    "Add dark mode to mobile app",
    "Duplicate accounts after social sign-in",
    "Paginate order history",
    "Improve product image loading",
    "Allow nicknames on saved cards",
    "Search misses products with accents",
    "Track parcel from order page",
    "Account page times out for large orders",
    "Collect consent for marketing e-mails",
    "Retry failed card payments",
]

projects = [
    {
        "id": "10001",
        "key": "SHOP",
        "name": "Web Shop",
        "projectTypeKey": "software",
        "style": "classic",
        "projectCategory": {"id": "10000", "name": "Customer facing"},
        "avatarUrls": {"48x48": "https://example.atlassian.net/avatar/10001"},
    },
    {
        "id": "10002",
        "key": "APP",
        "name": "Mobile App",
        "projectTypeKey": "software",
        "style": "next-gen",
        "avatarUrls": {"48x48": "https://example.atlassian.net/avatar/10002"},
    },
    {
        "id": "10003",
        "key": "OPS",
        "name": "Operations Desk",
        "projectTypeKey": "service_desk",
        "style": "classic",
        "projectCategory": {"id": "10001", "name": "Internal"},
        "avatarUrls": {"48x48": "https://example.atlassian.net/avatar/10003"},
    },
]


def user(name):
    return (
        None if name is None else {"accountId": "acc-" + name.split()[0].lower(), "displayName": name, "active": True}
    )


def issue(n):
    status, category = statuses[n % 4] if n % 7 else statuses[3]
    created_day = 1 + (n * 2) % 27
    done = category == "Done"
    fields = {
        "project": {"id": "10001", "key": "SHOP", "name": "Web Shop"},
        "issuetype": {"name": types[n % 3], "subtask": False},
        "summary": summaries[n % len(summaries)] + ("" if n < len(summaries) else " (follow-up)"),
        "status": {"name": status, "statusCategory": {"key": category.lower().replace(" ", ""), "name": category}},
        "priority": {"name": priorities[rng.randrange(4)]},
        "assignee": user(None if n % 9 == 4 else people[n % 5]),
        "reporter": user(people[(n + 2) % 5]),
        "created": f"2025-09-{created_day:02d}T{9 + n % 8:02d}:15:00.000+0100",
        "updated": f"2025-10-{1 + n % 28:02d}T14:{n % 60:02d}:00.000+0100",
        "duedate": f"2025-11-{1 + n % 28:02d}" if n % 3 == 0 else None,
        "resolutiondate": f"2025-10-{1 + n % 28:02d}T16:00:00.000+0100" if done else None,
        "resolution": {"name": "Done"} if done else None,
        "labels": [l for l, k in (("customer-reported", n % 4 == 1), ("tech-debt", n % 5 == 2)) if k],
        "components": [{"id": str(200 + n % 4), "name": components[n % 4]}],
        "fixVersions": [{"id": "300", "name": "2025.11"}] if n % 2 == 0 else [],
        "parent": {"id": "5000", "key": "SHOP-1"} if n % 6 == 5 else None,
        "customfield_10016": [1, 2, 3, 5, 8][n % 5] if n % 3 else None,
    }
    return {
        "id": str(20000 + n),
        "key": f"SHOP-{n + 2}",
        "self": f"https://example.atlassian.net/rest/api/2/issue/{20000 + n}",
        "fields": fields,
    }


issues = [issue(n) for n in range(42)]
os.makedirs(OUT, exist_ok=True)
pages = {
    "projects.json": {"startAt": 0, "maxResults": 100, "total": 3, "isLast": True, "values": projects},
    "issues-page-1.json": {"issues": issues[:25], "nextPageToken": "page-2-token", "isLast": False},
    "issues-page-2.json": {"issues": issues[25:], "isLast": True},
}
for name, body in pages.items():
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        json.dump(body, fh, indent=1)
        fh.write("\n")
print("wrote", ", ".join(pages))
