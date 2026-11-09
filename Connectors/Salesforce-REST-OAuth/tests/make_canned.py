"""Writes the invented Salesforce REST API responses in tests/canned/ used by the tests and
sample-data/placeholder.csv.

Run from the block folder: python3 tests/make_canned.py
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "canned")
INSTANCE = "https://acme-dev.my.salesforce.com"

accounts = [
    ("Fernhill Garden Centre", "Customer - Direct", "Retail", "12 Mill Road", "Leeds", "LS1 4AB", 2400000, 38),
    ("Marsh Lane Hardware", "Customer - Direct", "Retail", "4 Marsh Lane", "York", "YO1 7HH", 860000, 12),
    (
        "Brookside Allotment Society",
        "Customer - Channel",
        "Not For Profit",
        "Brookside",
        "Harrogate",
        "HG1 2RS",
        None,
        4,
    ),
    ("Willow Bank Landscapes", "Prospect", "Construction", "7 Willow Bank", "Bradford", "BD1 3QT", 1300000, 21),
    ("Oakfield Nurseries", "Customer - Direct", "Agriculture", "Oakfield Farm", "Wakefield", "WF1 2DD", 3100000, 55),
    ("Greenway Estates", "Prospect", "Real Estate", "1 Greenway", "Leeds", "LS6 1AA", 9800000, 140),
    ("Kestrel Facilities", "Customer - Channel", "Facilities", "Unit 5, Don Park", "Sheffield", "S9 2RT", 5200000, 230),
    ("Riverside Parks Trust", "Other", "Not For Profit", "Riverside", "Hull", "HU1 1NQ", None, 9),
    ("Pennine Tools", "Customer - Direct", "Wholesale", "Pennine Works", "Huddersfield", "HD1 6PL", 7400000, 88),
    ("Hollins Garden Design", "Prospect", "Design", "3 Hollins Way", "Ilkley", "LS29 8AA", 410000, 6),
    ("Dalesway Hotels", "Customer - Direct", "Hospitality", "Dalesway House", "Skipton", "BD23 1JD", 12500000, 310),
    ("Abbey Fields School", "Other", "Education", "Abbey Fields", "Selby", "YO8 4QS", None, 95),
]


def account(i, name, kind, industry, street, city, postcode, revenue, staff):
    return {
        "attributes": {"type": "Account", "url": f"/services/data/v62.0/sobjects/Account/001A{i:014d}"},
        "Id": f"001A{i:014d}",
        "IsDeleted": False,
        "Name": name,
        "Type": kind,
        "Industry": industry,
        "BillingStreet": street,
        "BillingCity": city,
        "BillingPostalCode": postcode,
        "BillingCountry": "United Kingdom",
        "AnnualRevenue": revenue,
        "NumberOfEmployees": staff,
        "OwnerId": f"005A{i % 3:014d}",
        "CreatedDate": f"2024-{1 + i:02d}-0{1 + i % 9}T09:30:00.000+0000",
        "LastActivityDate": None if i % 4 == 3 else f"2025-0{1 + i % 6}-{10 + i:02d}",
    }


records = [account(i, *a) for i, a in enumerate(accounts)]

fields = [
    ("Id", "Account ID", "id"),
    ("IsDeleted", "Deleted", "boolean"),
    ("Name", "Account Name", "string"),
    ("Type", "Account Type", "picklist"),
    ("Industry", "Industry", "picklist"),
    ("BillingStreet", "Billing Street", "textarea"),
    ("BillingCity", "Billing City", "string"),
    ("BillingPostalCode", "Billing Zip/Postal Code", "string"),
    ("BillingCountry", "Billing Country", "string"),
    ("BillingAddress", "Billing Address", "address"),
    ("AnnualRevenue", "Annual Revenue", "currency"),
    ("NumberOfEmployees", "Employees", "int"),
    ("OwnerId", "Owner ID", "reference"),
    ("CreatedDate", "Created Date", "datetime"),
    ("LastActivityDate", "Last Activity", "date"),
    ("Jigsaw", "Data.com Key", "string"),
]
describe = {
    "name": "Account",
    "label": "Account",
    "queryable": True,
    "fields": [
        {
            "name": n,
            "label": l,
            "type": t,
            "length": 255 if t in ("string", "textarea") else 0,
            "precision": 18 if t == "currency" else 0,
            "scale": 2 if t == "currency" else 0,
            "nillable": n not in ("Id", "Name", "IsDeleted"),
            "unique": False,
            "externalId": False,
            "calculated": False,
            "createable": n not in ("Id", "CreatedDate"),
            "updateable": n not in ("Id", "CreatedDate"),
            "filterable": True,
            "sortable": t != "textarea",
            "groupable": t not in ("textarea", "currency"),
            "relationshipName": "Owner" if n == "OwnerId" else None,
            "referenceTo": ["User"] if n == "OwnerId" else [],
            "deprecatedAndHidden": n == "Jigsaw",
        }
        for n, l, t in fields
    ],
}

files = {
    "token.json": {
        "access_token": "00Dxx0000000001!AQ0AQtest",
        "instance_url": INSTANCE,
        "id": f"{INSTANCE}/id/00Dxx0000000001EAA/005xx000001X8UzAAK",
        "token_type": "Bearer",
        "issued_at": "1735732800000",
        "signature": "test",
    },
    "versions.json": [
        {"label": "Winter '25", "url": "/services/data/v62.0", "version": "62.0"},
        {"label": "Summer '24", "url": "/services/data/v61.0", "version": "61.0"},
        {"label": "Spring '24", "url": "/services/data/v60.0", "version": "60.0"},
    ],
    "describe-account.json": describe,
    "query-accounts-1.json": {
        "totalSize": 12,
        "done": False,
        "records": records[:7],
        "nextRecordsUrl": "/services/data/v62.0/query/01gA0000000Example-2000",
    },
    "query-accounts-2.json": {"totalSize": 12, "done": True, "records": records[7:]},
    "sobjects.json": {
        "encoding": "UTF-8",
        "maxBatchSize": 200,
        "sobjects": [
            {
                "name": n,
                "label": l,
                "labelPlural": p,
                "keyPrefix": k,
                "queryable": True,
                "retrieveable": True,
                "searchable": True,
                "createable": True,
                "updateable": True,
                "deletable": True,
                "custom": c,
                "urls": {"sobject": f"/services/data/v62.0/sobjects/{n}"},
            }
            for n, l, p, k, c in [
                ("Account", "Account", "Accounts", "001", False),
                ("Contact", "Contact", "Contacts", "003", False),
                ("Opportunity", "Opportunity", "Opportunities", "006", False),
                ("Delivery_Route__c", "Delivery Route", "Delivery Routes", "a01", True),
            ]
        ],
    },
    "query-contacts-owner.json": {
        "totalSize": 3,
        "done": True,
        "records": [
            {
                "attributes": {"type": "Contact"},
                "Id": "003A1",
                "LastName": "Natarajan",
                "Owner": {"attributes": {"type": "User"}, "Name": "Ada Example"},
                "Account": None,
            },
            {
                "attributes": {"type": "Contact"},
                "Id": "003A2",
                "LastName": "Okafor",
                "Owner": None,
                "Account": {"attributes": {"type": "Account"}, "Name": "Marsh Lane Hardware"},
            },
            {
                "attributes": {"type": "Contact"},
                "Id": "003A3",
                "LastName": "Rossi",
                "Owner": {"attributes": {"type": "User"}, "Name": "Ben Example"},
                "Account": None,
            },
        ],
    },
}
os.makedirs(OUT, exist_ok=True)
for name, body in files.items():
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        json.dump(body, fh, indent=1)
        fh.write("\n")
print("wrote", ", ".join(files))
