# Report tab to PDF

Prints a Report tab to a PDF file for each input record, from the tab's address in a field, saving the files in a folder.

Board packs, monthly summaries and client reports often have to leave Omniscope as PDF files: to be emailed, archived or uploaded. This block prints each Report tab listed in its input, in Omniscope's print layout, and saves one PDF per tab, so a workflow can produce the files on every run without anyone opening a browser.

- Each input record holds a **Report tab URL**, such as `http://127.0.0.1:24679/Folder/Project.iox/r/Report/#Tab`. A **Project metadata** block lists every tab of a project with its URL.
- The tab is opened in **print mode** by Chrome and saved as a PDF in the **output folder** (created if it doesn't exist).
- File names come from an optional **file name field** (with or without `.pdf`); otherwise `<Report>-<Tab>-<n>.pdf`, where n counts the records from 0. Characters that can't be in a file name (`/ \ : * ? " < > |`) become `_`. Two records with the same name get `-2`, `-3` added instead of overwriting each other.
- **Page width and height** (pixels) override the Report's own page size (A4, or the Report's fixed size).
- **Username and password**, for a Report behind Basic Authentication, are used only to open the page: the output holds the URL as given. Chrome sends them in the address (`user:password@host`), so over `http://` to another machine they travel unencrypted: use `https://`, or the server's own address (`127.0.0.1`).
- Records with an empty URL are skipped; the block's message says how many.

## Language and libraries

Python. It uses visokio-omniprint (MIT; Visokio's printing package, whose source is in this repository under [`visokio-omniprint/`](../../visokio-omniprint)) and pandas (BSD 3-Clause). visokio-omniprint drives Chrome with selenium (Apache License 2.0) and installs it with webdriver-manager (Apache License 2.0) and get-chrome-driver (MIT); it also brings fpdf (LGPL v3), python-pptx (MIT) and tinify (MIT), which this block doesn't use.

Omniscope installs visokio-omniprint with pip on first run (the manifest's `dependencies`). **Chrome** is needed too: on a server that runs custom blocks in Docker, the block uses its own image with Chrome included (the manifest's `docker` settings); otherwise Chrome must be installed on the machine running Omniscope.

## Inputs

- **Input 1**: one record per tab to print, with its URL (and optionally a file name).

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Report tab URL field | `report` | Field (text) | The field holding each Report tab's address. |
| File name field | `fileName` | Field (text) | Optional. Each PDF's file name, without `.pdf`. Empty: `<Report>-<Tab>-<n>.pdf`. |
| Output folder | `outputFolder` | File (folder) | Where the PDFs are saved, on the machine running Omniscope. Created if missing; files with the same name are replaced. |
| Page width (pixels) | `pageWidth` | Integer | Optional. Overrides the Report's page size. |
| Page height (pixels) | `pageHeight` | Integer | Optional. Overrides the Report's page size. |
| Loading delay (seconds) | `chromeDelay` | Integer | Extra wait after the Report has finished drawing, before printing. Default 3. |
| Username | `auth_username` | Text | Optional, for Basic Authentication. |
| Password | `auth_password` | Password | Optional, for Basic Authentication. Not written to the output. |

## Outputs

- **PDFs** (`Output Data`): one record per PDF written: `URL` (as given), `PDF filename`, `PDF path`.

## How the print address is made

`http://host/Folder/Project.iox/r/Report/#Tab` is printed as `http://host/Folder/Project.iox/r/Report/#device=printer&tab=Tab` (with `&pageWidth=...&pageHeight=...` when set). The `/` before `#` may be left out. Anything after the tab name in the address (`#Tab&...`) is passed on.

## Limits

- The block needs the Omniscope server itself: Chrome must reach the Report at the address given, and the PDF is what Omniscope's print layout draws. Its tests check the addresses, file names and files with a stand-in for Chrome; printing itself is not tested off a server.
- Chrome's PDF is A4 portrait; the page width and height change how the Report lays itself out for printing.
- One Chrome session per record: expect a few seconds per tab, plus the loading delay.
- If one tab can't be printed (Chrome error, page not reachable), the block stops with the record number and Chrome's message; PDFs written before it stay in the folder.

## Source

[script.py](script.py)

The sample data in `sample-data/` is invented. To print one tab once for each scenario of a multi-tenant Report, see [Multi-tenant Report to PDF](../Report-to-PDF-batch-output).
