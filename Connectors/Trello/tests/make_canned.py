"""Writes the invented Trello API responses in tests/canned/ that the tests (and sample-data/placeholder.csv) use.

Run from the block folder: python3 tests/make_canned.py
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "canned")

WS = "64a0c0ffee0000000000w001"
BOARD = "64b0c0ffee0000000000b001"
lists = [("To plan", 1), ("Writing", 2), ("Design", 3), ("Scheduled", 4), ("Published", 5)]
list_ids = {name: f"64c0c0ffee00000000000l0{i}" for name, i in lists}
labels = {"Blog": "green", "Newsletter": "blue", "Social": "purple", "Webinar": "orange", "": "red"}
members = {"m1": "Aisha", "m2": "Ben", "m3": "Chloe"}

titles = [
    ("Spring product update post", "Published", ["Blog"], "2025-03-04"),
    ("March newsletter", "Published", ["Newsletter"], "2025-03-06"),
    ("Customer story: Fernhill Garden Centre", "Published", ["Blog", "Social"], "2025-03-11"),
    ("Webinar: planning the summer season", "Scheduled", ["Webinar"], "2025-04-02"),
    ("Webinar follow-up e-mail", "Scheduled", ["Newsletter", "Webinar"], "2025-04-03"),
    ("April newsletter", "Design", ["Newsletter"], "2025-04-08"),
    ("Five ways to cut delivery costs", "Design", ["Blog"], "2025-04-10"),
    ("Price list refresh announcement", "Writing", ["Blog", ""], "2025-04-14"),
    ("Social posts for the trade show", "Writing", ["Social"], "2025-04-16"),
    ("Trade show stand photos", "Writing", ["Social"], None),
    ("Guide: choosing compost", "Writing", ["Blog"], "2025-04-22"),
    ("May newsletter", "To plan", ["Newsletter"], "2025-05-06"),
    ("Customer story: Willow Bank Landscapes", "To plan", ["Blog"], None),
    ("Summer webinar series outline", "To plan", ["Webinar"], None),
    ("Refresh the FAQ page", "To plan", [], None),
    ("Year in review draft", "To plan", ["Blog"], None),
]


def label(name):
    return {"id": "lbl-" + (name or "red").lower(), "idBoard": BOARD, "name": name, "color": labels[name]}


def card(i, title, list_name, lbls, due):
    published = list_name == "Published"
    return {
        "id": f"64d0c0ffee000000000c{i:04d}",
        "name": title,
        "desc": "" if i % 3 else f"Brief for {title.lower()}.",
        "closed": False,
        "idList": list_ids[list_name],
        "idBoard": BOARD,
        "due": f"{due}T09:00:00.000Z" if due else None,
        "dueComplete": published,
        "start": None,
        "dateLastActivity": f"2025-03-{1 + i:02d}T1{i % 10}:30:00.000Z",
        "labels": [label(n) for n in lbls],
        "idMembers": [m for j, m in enumerate(members) if (i + j) % 3 == 0],
        "url": f"https://trello.com/c/Card{i:04d}/{i}",
        "shortUrl": f"https://trello.com/c/Card{i:04d}",
        "pos": 16384 * (i + 1),
        "badges": {
            "checkItems": 4 if i % 4 == 0 else 0,
            "checkItemsChecked": (4 if published else 2) if i % 4 == 0 else 0,
            "comments": i % 5,
            "attachments": 0,
            "attachmentsByType": {"trello": {"board": 0, "card": 0}},
        },
    }


cards = [card(i, *t) for i, t in enumerate(titles)]
boards = [
    {
        "id": BOARD,
        "name": "Content calendar",
        "desc": "Posts, newsletters and webinars, by stage.",
        "closed": False,
        "url": "https://trello.com/b/Board0001/content-calendar",
        "shortUrl": "https://trello.com/b/Board0001",
        "dateLastActivity": "2025-03-17T10:30:00.000Z",
        "idOrganization": WS,
    },
    {
        "id": "64b0c0ffee0000000000b002",
        "name": "Trade show 2025",
        "desc": "",
        "closed": False,
        "url": "https://trello.com/b/Board0002/trade-show-2025",
        "shortUrl": "https://trello.com/b/Board0002",
        "dateLastActivity": "2025-03-12T15:05:00.000Z",
        "idOrganization": WS,
    },
    {
        "id": "64b0c0ffee0000000000b003",
        "name": "Website fixes (archived)",
        "desc": "",
        "closed": True,
        "url": "https://trello.com/b/Board0003/website-fixes",
        "shortUrl": "https://trello.com/b/Board0003",
        "dateLastActivity": "2024-11-02T08:00:00.000Z",
        "idOrganization": WS,
    },
]
list_objs = [{"id": list_ids[n], "name": n, "closed": False, "pos": 16384 * p, "idBoard": BOARD} for n, p in lists]
items = [
    {
        "id": f"64e0c0ffee00000000000i0{k}",
        "name": n,
        "state": s,
        "idChecklist": "64f0c0ffee000000000cl001",
        "pos": 16384 * (k + 1),
        "due": None,
        "idMember": None,
    }
    for k, (n, s) in enumerate(
        [
            ("Draft text", "complete"),
            ("Pick photos", "complete"),
            ("Check prices with sales", "incomplete"),
            ("Book the e-mail send", "incomplete"),
        ]
    )
]
checklists = [
    {
        "id": "64f0c0ffee000000000cl001",
        "name": "Before sending",
        "idCard": cards[0]["id"],
        "idBoard": BOARD,
        "pos": 16384,
        "checkItems": items,
    }
]
search = {
    "options": {"terms": [{"text": "newsletter"}], "modelTypes": ["cards"]},
    "cards": [c for c in cards if "newsletter" in c["name"].lower()],
}

os.makedirs(OUT, exist_ok=True)
files = {
    "boards.json": boards,
    "lists.json": list_objs,
    "cards-board.json": cards,
    "cards-list.json": [c for c in cards if c["idList"] == list_ids["Writing"]],
    "checklists.json": checklists,
    "checkitems.json": items,
    "search.json": search,
}
for name, body in files.items():
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        json.dump(body, fh, indent=1)
        fh.write("\n")
print("wrote", ", ".join(files))
