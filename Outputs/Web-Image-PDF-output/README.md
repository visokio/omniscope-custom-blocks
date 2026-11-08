# Web Image-PDF output

Saves a screenshot (PNG) of the web page at each input record's URL, at a chosen size, and optionally one PDF with a page per screenshot.

Dashboards and web pages often need to travel as pictures: a chart in an email, a daily snapshot for an archive, a set of pages in one PDF. This block opens each URL in its input in Chrome, at the size you choose, and saves what the page shows.

- Each input record holds a **URL**: a Report tab, or any web page the server can reach.
- The **screenshot size** (for example 1280x720) is the size of each PNG: Chrome's page area is set to it. **Portrait** turns the size on its side (720x1280).
- PNGs are saved in the **output folder** (created if missing) as `screenshot_0.png`, `screenshot_1.png`, ..., numbered by record from 0.
- **Create PDF** also makes one PDF (`screenshots.pdf` unless named), one page per screenshot, each page the size of the screenshot.
- **Shrink with Tinify** shrinks each PNG to a width with the Tinify web service (needs an API key); the PDF is made from the full-size screenshots first.
- **Username and password**, for pages behind Basic Authentication, are used only to open the page: the output holds the URL as given. Chrome sends them in the address (`user:password@host`), so over `http://` to another machine they travel unencrypted: use `https://`, or the server's own address (`127.0.0.1`).
- Records with an empty URL are skipped.

## Language and libraries

Python. It uses visokio-omniprint (MIT; Visokio's printing package, whose source is in this repository under [`visokio-omniprint/`](../../visokio-omniprint)) and pandas (BSD 3-Clause). visokio-omniprint drives Chrome with selenium (Apache License 2.0), installs it with webdriver-manager (Apache License 2.0) and get-chrome-driver (MIT), makes the PDF with fpdf (LGPL v3) and calls Tinify with tinify (MIT).

Omniscope installs visokio-omniprint with pip on first run (the manifest's `dependencies`). **Chrome** is needed too: on a server that runs custom blocks in Docker, the block uses its own image with Chrome included (the manifest's `docker` settings); otherwise Chrome must be installed on the machine running Omniscope.

## Inputs

- **Input 1**: one record per page to capture, with its URL.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| URL field | `url_field` | Field (text) | The field holding each page's address. |
| Screenshot size | `resolution` | Choice | 3840x2160, 2560x1440, 1920x1080, 1600x1200, 1280x960, 1280x720 (the default), 1024x768, or A4 (1123x794). |
| Orientation | `orientation` | Choice | Landscape (`L`, the default) or Portrait (`P`, the size turned on its side). |
| Output folder | `folder_path` | File (folder) | Where the PNGs and the PDF are saved. Created if missing; files with the same names are replaced. |
| Page load delay (seconds) | `sleep_seconds` | Integer | Extra wait after the page has finished loading. Default 3. |
| Shrink with Tinify | `tinify` | Yes/no | Shrink each PNG with the Tinify service. |
| Tinify API key | `tinify_key` | Password | Needed with Tinify. |
| Shrunk width (pixels) | `tinify_width` | Integer | Needed with Tinify; the height keeps the proportions. |
| Create PDF | `create_pdf` | Yes/no | Also make one PDF of all the screenshots. |
| PDF file name | `pdf_file_name` | Text | Optional. Empty: `screenshots.pdf`; `.pdf` is added if missing. |
| Compress the PDF | `compression` | Yes/no | Lossless compression of the PDF's page descriptions; the screenshots are stored compressed either way, so the size hardly changes. |
| Username | `auth_username` | Text | Optional, for Basic Authentication. |
| Password | `auth_password` | Password | Optional, for Basic Authentication. Not written to the output. |

## Outputs

- **Screenshots** (`Output Data`): one record per screenshot: `URL` (as given), `Screenshot path`, `Screenshot filename`, `PDF` (the PDF's path, or empty).

## Limits

- Chrome must reach each page from the machine running Omniscope. The tests use a stand-in for Chrome that checks the addresses, sizes and files; a run with real Chrome (headless Chromium 156) gave screenshots of exactly the chosen size and a PDF with pages of the same size.
- A screenshot shows the page area only: a page longer than the window is cut at the bottom. Choose a taller size, or Portrait, for long pages.
- One Chrome session per record: expect a few seconds per page, plus the delay.
- If one page can't be opened, the block stops with the record number and Chrome's message.
- Tinify sends each PNG to the Tinify service (api.tinify.com) and counts against the key's monthly allowance.

## Source

[script.py](script.py)

The sample data in `sample-data/` is invented; `example.com` addresses are reserved for examples.
