"""Writes the invented HubSpot API responses in tests/canned/ used by the tests and sample-data/placeholder.csv.

Run from the block folder: python3 tests/make_canned.py
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "canned")

companies = [
    ("Fernhill Garden Centre", "fernhill-garden.example", "Retail", "Leeds"),
    ("Marsh Lane Hardware", "marshlane.example", "Retail", "York"),
    ("Brookside Allotment Society", "brookside-allotments.example", "Non-profit", "Harrogate"),
    ("Willow Bank Landscapes", "willowbank.example", "Construction", "Bradford"),
    ("Oakfield Nurseries", "oakfield-nurseries.example", "Agriculture", "Wakefield"),
    ("Greenway Estates", "greenway-estates.example", "Real estate", "Leeds"),
    ("Kestrel Facilities", "kestrel-fm.example", "Facilities services", "Sheffield"),
    ("Riverside Parks Trust", "riverside-parks.example", "Non-profit", "Hull"),
    ("Pennine Tools", "pennine-tools.example", "Wholesale", "Huddersfield"),
    ("Hollins Garden Design", "hollins-design.example", "Design", "Ilkley"),
    ("Dalesway Hotels", "dalesway-hotels.example", "Hospitality", "Skipton"),
    ("Abbey Fields School", "abbeyfields.example", "Education", "Selby"),
]


def company(i, name, domain, industry, city):
    created = f"2024-{1 + i % 12:02d}-{3 + i:02d}T09:{10 + i:02d}:00Z"
    return {
        "id": str(9001 + i),
        "properties": {
            "name": name,
            "domain": domain,
            "industry": industry,
            "city": city,
            "createdate": created.replace("Z", ".000Z"),
            "hs_lastmodifieddate": f"2025-03-{1 + i:02d}T12:00:00.000Z",
            "hs_object_id": str(9001 + i),
        },
        "createdAt": created.replace("Z", ".000Z"),
        "updatedAt": f"2025-03-{1 + i:02d}T12:00:00.000Z",
        "archived": False,
    }


all_companies = [company(i, *c) for i, c in enumerate(companies)]

people = [
    ("Priya", "Natarajan", "fernhill-garden.example", "customer"),
    ("Tom", "Okafor", "marshlane.example", "lead"),
    ("Elena", "Rossi", "brookside-allotments.example", "customer"),
    ("Sam", "Whitfield", "willowbank.example", "opportunity"),
    ("Hannah", "Lowe", "oakfield-nurseries.example", "lead"),
    ("Owen", "Pryce", "greenway-estates.example", "subscriber"),
]
contacts = [
    {
        "id": str(501 + i),
        "properties": {
            "email": f"{f.lower()}.{l.lower()}@{d}",
            "firstname": f,
            "lastname": l,
            "lifecyclestage": stage,
            "createdate": f"2025-01-{10 + i:02d}T08:00:00.000Z",
            "lastmodifieddate": f"2025-02-{10 + i:02d}T08:00:00.000Z",
            "hs_object_id": str(501 + i),
        },
        "createdAt": f"2025-01-{10 + i:02d}T08:00:00.000Z",
        "updatedAt": f"2025-02-{10 + i:02d}T08:00:00.000Z",
        "archived": False,
    }
    for i, (f, l, d, stage) in enumerate(people)
]

pages = {
    "companies-page-1.json": {
        "results": all_companies[:8],
        "paging": {"next": {"after": "9009", "link": "https://api.hubapi.com/crm/v3/objects/companies?after=9009"}},
    },
    "companies-page-2.json": {"results": all_companies[8:]},
    "contacts.json": {"results": contacts},
    "search-contacts.json": {"total": 1, "results": [contacts[2]]},
    "associations.json": {
        "status": "COMPLETE",
        "results": [
            {"from": {"id": "501"}, "to": [{"id": "9001", "type": "contact_to_company"}]},
            {
                "from": {"id": "503"},
                "to": [{"id": "9003", "type": "contact_to_company"}, {"id": "9008", "type": "contact_to_company"}],
            },
        ],
    },
    "lists.json": {
        "offset": 2,
        "hasMore": False,
        "total": 2,
        "lists": [
            {
                "listId": "11",
                "name": "Spring newsletter",
                "processingType": "MANUAL",
                "objectTypeId": "0-1",
                "size": 240,
                "createdAt": "2025-02-01T10:00:00.000Z",
                "filtersUpdatedAt": None,
            },
            {
                "listId": "12",
                "name": "Trade customers",
                "processingType": "DYNAMIC",
                "objectTypeId": "0-1",
                "size": 75,
                "createdAt": "2025-02-14T10:00:00.000Z",
                "filterBranch": {"filterBranchType": "OR", "filters": []},
            },
        ],
    },
    "forms.json": [
        {
            "guid": "3f1c0f9e-0000-4000-8000-000000000001",
            "name": "Catalogue request",
            "createdAt": 1735725600000,
            "formFieldGroups": [{"fields": [{"name": "email"}]}],
        }
    ],
    "form-submissions.json": {
        "results": [
            {
                "conversionId": "c-1",
                "submittedAt": 1736935200000,
                "pageUrl": "https://example.com/catalogue",
                "values": [{"name": "email", "value": "ben@example.com"}, {"name": "firstname", "value": "Ben"}],
            },
            {
                "conversionId": "c-2",
                "submittedAt": 1737021600000,
                "pageUrl": "https://example.com/catalogue",
                "values": [{"name": "email", "value": "chloe@example.com"}],
            },
        ]
    },
}
os.makedirs(OUT, exist_ok=True)
for name, body in pages.items():
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        json.dump(body, fh, indent=1)
        fh.write("\n")
print("wrote", ", ".join(pages))
