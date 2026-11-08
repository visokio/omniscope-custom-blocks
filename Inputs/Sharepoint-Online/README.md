# SharePoint Online Downloader

Downloads a file, or every file in a folder, from a SharePoint Online document library to the Omniscope server, ready for an Append files block to load.

Budgets, headcount sheets and supplier lists often live in SharePoint or Teams. This block downloads them through Microsoft Graph each time the workflow runs and outputs one record per file with its path on the Omniscope server; an **Append files** or **File** block then loads the contents.

- Paste the **address of a file or a folder** as the browser shows it, including addresses copied from the Office web apps (`/:x:/r/sites/...`) and sharing links.
- A **folder** downloads every file in it (sub-folders are skipped), following Graph's pages of results.
- Signs in as an **app registered in Microsoft Entra ID**, with a client ID and client secret, so it runs unattended without a person's password or a multi-factor prompt.
- Clear messages when the sign-in is refused (with Microsoft's reason), when the app lacks permission, or when the address is not found.

Earlier versions of this block signed in with a person's user name and password through SharePoint's legacy sign-in, which Microsoft retired on 1 May 2026 and which never worked for accounts with multi-factor sign-in. Projects that used it need the app sign-in options filled in.

## Language and libraries

Python, with requests (Apache License 2.0) for the calls to Microsoft Graph and pandas (BSD 3-Clause). pandas is part of Omniscope's Python environment; Omniscope installs requests with pip on first run if it is missing (the manifest's `dependencies`).

## Setting up the app

1. In the Microsoft Entra admin centre, register an application (App registrations > New registration).
2. Under API permissions, add the Microsoft Graph **application** permission **Sites.Read.All**, or **Sites.Selected** to limit it to chosen sites (an administrator then grants the app read access to each site). Have an administrator grant consent.
3. Under Certificates & secrets, create a client secret and copy its **value**.
4. Enter the tenant ID, the application (client) ID and the secret value in the block.

## Inputs

None. The block reads from SharePoint Online.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Tenant ID | `tenantId` | Text | Your Microsoft Entra tenant: its ID or a domain such as `contoso.onmicrosoft.com`. |
| Client ID | `clientId` | Text | The application (client) ID of the registered app. |
| Client secret | `clientSecret` | Password | A client secret value of that app. Secrets expire. |
| File or folder URL | `fileUrl` | Text | The address of a file or folder in a document library, such as `https://contoso.sharepoint.com/sites/Finance/Shared Documents/Reports/budget.xlsx`. |
| Download to folder | `localFolder` | Text | A folder on the Omniscope server for the files (created if missing). Empty: the block's own working folder. |

## Outputs

- **Files** (`Output Data`): File path (on the Omniscope server), File name, Size (bytes), Modified (in SharePoint, UTC), SharePoint URL. For a folder, sorted by file name.

## Loading the files

Connect the output to an **Append files** block set to take the file names from the upstream block, using the **File path** field; for a single file, a File block with the path also works.

## Limits

- SharePoint Online (Microsoft 365) only, not SharePoint Server.
- Sites under `/sites/` or `/teams/` and the root site; files in sub-sites are not found by address.
- One folder level: sub-folders are not entered.
- Every file is downloaded on every run; files of the same name in the download folder are replaced.

## Source

[script.py](script.py)

The tests in `tests/` run the script against invented Microsoft Graph responses (`tests/canned/`, written by `tests/make_canned.py`); no call reaches Microsoft. `sample-data/placeholder.csv` is the block's output for the canned folder, for trying a workflow without a Microsoft 365 tenant.
