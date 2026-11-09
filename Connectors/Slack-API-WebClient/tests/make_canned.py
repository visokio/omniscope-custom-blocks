"""Writes the invented Slack Web API responses in tests/canned/ used by the tests and sample-data/placeholder.csv.

Run from the block folder: python3 tests/make_canned.py
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "canned")

names = [
    "general",
    "random",
    "sales-uk",
    "sales-europe",
    "support",
    "support-escalations",
    "marketing",
    "product-updates",
    "release-notes",
    "office-leeds",
    "office-london",
    "events",
    "hiring",
    "finance",
    "it-help",
    "social",
    "customer-feedback",
    "partners",
    "data-team",
    "announcements",
    "standups",
    "design",
    "warehouse",
    "deliveries",
]


def channel(i, name):
    return {
        "id": f"C0{1000 + i}EXAMPLE",
        "name": name,
        "is_channel": True,
        "is_private": name in ("finance", "hiring"),
        "is_archived": name == "office-leeds",
        "is_general": name == "general",
        "created": 1704067200 + i * 86400 * 9,
        "creator": f"U0{100 + i % 4}EXAMPLE",
        "num_members": [
            212,
            198,
            14,
            11,
            37,
            9,
            22,
            140,
            61,
            0,
            48,
            73,
            6,
            8,
            95,
            120,
            31,
            12,
            17,
            212,
            44,
            19,
            26,
            15,
        ][i],
        "topic": {"value": f"About #{name}" if i % 3 else "", "creator": "", "last_set": 0},
        "purpose": {"value": f"Talk about {name.replace('-', ' ')}", "creator": "", "last_set": 0},
        "previous_names": ["sales"] if name == "sales-uk" else [],
    }


channels = [channel(i, n) for i, n in enumerate(names)]
files = {
    "conversations-list-1.json": {
        "ok": True,
        "channels": channels[:15],
        "response_metadata": {"next_cursor": "dGVhbTpDMDE1"},
    },
    "conversations-list-2.json": {"ok": True, "channels": channels[15:], "response_metadata": {"next_cursor": ""}},
    "users-profile-get.json": {
        "ok": True,
        "profile": {
            "real_name": "Ada Example",
            "display_name": "ada",
            "title": "Analyst",
            "email": "ada@example.com",
            "status_text": "In the office",
            "status_emoji": ":office:",
            "fields": {},
        },
    },
    "chat-postMessage.json": {
        "ok": True,
        "channel": "C01000EXAMPLE",
        "ts": "1735732800.000100",
        "message": {
            "type": "message",
            "text": "Weekly sales report is ready",
            "user": "U0BOT",
            "ts": "1735732800.000100",
            "blocks": [{"type": "rich_text"}],
        },
    },
    "error-missing-scope.json": {
        "ok": False,
        "error": "missing_scope",
        "needed": "channels:read",
        "provided": "chat:write",
    },
}
os.makedirs(OUT, exist_ok=True)
for name, body in files.items():
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        json.dump(body, fh, indent=1)
        fh.write("\n")
print("wrote", ", ".join(files))
