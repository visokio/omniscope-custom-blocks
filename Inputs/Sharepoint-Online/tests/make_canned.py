"""Writes the canned Microsoft Graph responses in tests/canned/ (all invented: a fictional company's Finance site)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CANNED = os.path.join(HERE, "canned")
HOST = "https://contoso.sharepoint.com"
SITE_ID = "contoso.sharepoint.com,5f2a1c0e-1111-4c4c-9b9b-000000000001,7d3e2b1a-2222-4d4d-8c8c-000000000002"
DRIVE = "b!Docs0000000000000000000000000000000000000000000000000001"
BOARD = "b!Board000000000000000000000000000000000000000000000000002"
FOLDER_ID = "01FOLDERREPORTS0000000000000000001"
FILES = {  # name: (id, modified)
    "budget-2025.csv": ("01FILEBUDGET000000000000000000001", "2025-03-10T08:12:45Z"),
    "headcount.csv": ("01FILEHEADCOUNT00000000000000002", "2025-03-11T16:40:02Z"),
    "suppliers.csv": ("01FILESUPPLIERS00000000000000003", "2025-02-27T11:05:30Z"),
}


def item(name, id_, modified):
    size = os.path.getsize(os.path.join(CANNED, "files", name))
    return {"id": id_, "name": name, "size": size, "lastModifiedDateTime": modified,
            "webUrl": f"{HOST}/sites/Finance/Shared%20Documents/Reports/{name}",
            "file": {"mimeType": "text/csv"},
            "parentReference": {"driveType": "documentLibrary", "driveId": DRIVE, "id": FOLDER_ID,
                                "path": "/drives/" + DRIVE + "/root:/Reports"}}


def write(name, body):
    with open(os.path.join(CANNED, name), "w", encoding="utf-8") as fh:
        json.dump(body, fh, indent=2)
        fh.write("\n")


write("token.json", {"token_type": "Bearer", "expires_in": 3599, "ext_expires_in": 3599,
                     "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.invented-test-token."})
write("token-error.json", {"error": "invalid_client",
                           "error_description": "AADSTS7000215: Invalid client secret provided. Ensure the secret "
                                                "being sent in the request is the client secret value, not the client "
                                                "secret ID.\r\nTrace ID: 00000000-0000-0000-0000-000000000000",
                           "error_codes": [7000215]})
write("site.json", {"id": SITE_ID, "name": "Finance", "displayName": "Finance", "webUrl": f"{HOST}/sites/Finance"})
write("drives.json", {"value": [
    {"id": DRIVE, "name": "Documents", "driveType": "documentLibrary", "webUrl": f"{HOST}/sites/Finance/Shared%20Documents"},
    {"id": BOARD, "name": "Board papers", "driveType": "documentLibrary", "webUrl": f"{HOST}/sites/Finance/Board%20papers"},
]})
write("item-file.json", item("budget-2025.csv", *FILES["budget-2025.csv"]))
write("item-folder.json", {"id": FOLDER_ID, "name": "Reports", "folder": {"childCount": 4},
                           "webUrl": f"{HOST}/sites/Finance/Shared%20Documents/Reports",
                           "parentReference": {"driveType": "documentLibrary", "driveId": DRIVE, "path": "/drives/" + DRIVE + "/root:"}})
names = sorted(FILES)
write("children-page-1.json", {
    "value": [item("suppliers.csv", *FILES["suppliers.csv"]),
              {"id": "01FOLDERARCHIVE0000000000000000004", "name": "Archive", "folder": {"childCount": 12},
               "parentReference": {"driveId": DRIVE, "id": FOLDER_ID}}],
    "@odata.nextLink": f"https://graph.microsoft.com/v1.0/drives/{DRIVE}/items/{FOLDER_ID}/children?$skiptoken=page2"})
write("children-page-2.json", {"value": [item("headcount.csv", *FILES["headcount.csv"]),
                                         item("budget-2025.csv", *FILES["budget-2025.csv"])]})
write("not-found.json", {"error": {"code": "itemNotFound", "message": "The resource could not be found."}})
write("forbidden.json", {"error": {"code": "accessDenied", "message": "Access denied"}})
print("written")
