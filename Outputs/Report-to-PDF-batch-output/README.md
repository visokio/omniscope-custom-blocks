# Multi-tenant Report to PDF

Prints one Report tab once per scenario of a multi-tenant configuration, saving a PDF file per scenario in a folder.

A multi-tenant Report shows each customer, region or user their own data from one Report design. When each of them also needs a PDF (a monthly statement, a regional summary), this block prints the same tab once for every scenario in the configuration and saves `<Report>-<scenario>.pdf` for each.

- Connect the **multi-tenant configuration**: one record per scenario. The scenario IDs are read from the **scenario field** (by default the field called `scenario`).
- Enter the **Report tab URL** once, as copied from the browser or the Report's sharing dialog, without a scenario: `http://127.0.0.1:24679/Folder/Project.iox/r/Report/#Tab`. The Report must use the same multi-tenant configuration.
- For each scenario the block prints `.../r/Report/s/<scenario>/` in Omniscope's print layout with Chrome and saves `<Report>-<scenario>.pdf` in the **output folder** (created if missing). Scenario IDs are encoded for the address (`Acme Ltd` becomes `Acme%20Ltd`); characters a file name can't hold become `_`. A repeated scenario gets `-2`, `-3` added instead of overwriting.
- **Page width and height** (pixels) override the Report's page size. **Username and password**, for Basic Authentication, are used only to open the page. Chrome sends them in the address (`user:password@host`), so over `http://` to another machine they travel unencrypted: use `https://`, or the server's own address (`127.0.0.1`).
- Records with an empty scenario are skipped.

## Language and libraries

Python. It uses visokio-omniprint (MIT; Visokio's printing package, whose source is in this repository under [`visokio-omniprint/`](../../visokio-omniprint)) and pandas (BSD 3-Clause). visokio-omniprint drives Chrome with selenium (Apache License 2.0) and installs it with webdriver-manager (Apache License 2.0) and get-chrome-driver (MIT); it also brings fpdf (LGPL v3), python-pptx (MIT) and tinify (MIT), which this block doesn't use.

Omniscope installs visokio-omniprint with pip on first run (the manifest's `dependencies`). **Chrome** is needed too: on a server that runs custom blocks in Docker, the block uses its own image with Chrome included (the manifest's `docker` settings); otherwise Chrome must be installed on the machine running Omniscope.

## Inputs

- **Input 1**: the multi-tenant configuration, one record per scenario to print.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Report tab URL | `report` | Text | The address of the tab to print, without a scenario. |
| Scenario field | `scenarioField` | Field | The field holding the scenario IDs. Empty: the field called `scenario`. |
| Output folder | `outputFolder` | File (folder) | Where the PDFs are saved, on the machine running Omniscope. Created if missing; files with the same name are replaced. |
| Page width (pixels) | `pageWidth` | Integer | Optional. Overrides the Report's page size. |
| Page height (pixels) | `pageHeight` | Integer | Optional. Overrides the Report's page size. |
| Loading delay (seconds) | `chromeDelay` | Integer | Extra wait after the Report has finished drawing, before printing. Default 3. |
| Username | `auth_username` | Text | Optional, for Basic Authentication. |
| Password | `auth_password` | Password | Optional, for Basic Authentication. Not written to the output. |

## Outputs

- **PDFs** (`Output Data`): one record per PDF written: `Scenario`, `URL` (the tab's address for that scenario, without any login), `PDF filename`, `PDF path`.

## Limits

- The block needs the Omniscope server itself: Chrome must reach the Report at the address given, and the PDF is what Omniscope's print layout draws for that scenario. Its tests check the addresses, file names and files with a stand-in for Chrome; printing itself is not tested off a server.
- Chrome's PDF is A4 portrait; the page width and height change how the Report lays itself out for printing.
- The output folder holds every scenario's PDF, each with that tenant's data: keep it private to the people allowed to see all of them, and check the join to recipients before the files are sent.
- If one scenario can't be printed, the block stops with the scenario and Chrome's message; PDFs written before it stay in the folder.
- [Report tab to PDF](../Report-tab-to-PDF) does the same for a list of tab addresses (one per record) and prints these scenario addresses too, given them in a field (`.../r/Report/s/<scenario>/#Tab`, built with a formula).

## Source

[script.py](script.py)

The sample data in `sample-data/` is invented.
