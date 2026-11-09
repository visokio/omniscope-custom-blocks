# Report to PowerPoint

Takes a screenshot of each Report tab in the input and makes a PowerPoint file with one slide per tab.

Reviews and board meetings often run from a slide deck, while the figures live in an Omniscope Report. This block turns the Report's tabs into slides: it takes a screenshot of each tab whose URL is in the input and puts them, in input order, into one `.pptx` file, each screenshot filling its slide.

- Each input record holds a **URL**: a Report tab (a **Project metadata** block lists every tab with its URL), or any web page the server can reach.
- The **screenshot size** (for example 1280x720) is the size of each screenshot: Chrome's page area is set to it. **Portrait** turns it on its side.
- The **slides take the shape of the screenshots**, the long side 13.33 inches as in PowerPoint's widescreen slide: 13.33 x 7.5 inches for 16:9, 13.33 x 10 for 4:3, 7.5 x 13.33 for 16:9 Portrait. Each screenshot fills its slide.
- The file goes in the **output folder** (created if missing) as `report.pptx`, or the **file name** given (`.pptx` added if missing). The PNGs are kept beside it: `screenshot_0.png`, `screenshot_1.png`, ...
- **Shrink with Tinify** shrinks each PNG to a width with the Tinify web service before it goes on its slide (needs an API key). The screenshots, and so the Report's figures, are uploaded to Tinify (api.tinify.com) to be shrunk: leave it unticked for confidential Reports.
- **Username and password**, for a Report behind Basic Authentication, are used only to open the page. Chrome sends them in the address (`user:password@host`), so over `http://` to another machine they travel unencrypted: use `https://`, or the server's own address (`127.0.0.1`).
- Records with an empty URL are skipped; with no URLs at all, no file is written.

## Language and libraries

Python. It uses visokio-omniprint (MIT; Visokio's printing package, whose source is in this repository under [`visokio-omniprint/`](../../visokio-omniprint)), python-pptx (MIT) and pandas (BSD 3-Clause). visokio-omniprint drives Chrome with selenium (Apache License 2.0), installs it with webdriver-manager (Apache License 2.0) and get-chrome-driver (MIT), and calls Tinify with tinify (MIT); it also brings fpdf (LGPL v3), which this block doesn't use.

Omniscope installs visokio-omniprint, and with it python-pptx, with pip on first run (the manifest's `dependencies`). **Chrome** is needed too: on a server that runs custom blocks in Docker, the block uses its own image with Chrome included (the manifest's `docker` settings); otherwise Chrome must be installed on the machine running Omniscope.

## Inputs

- **Input 1**: one record per slide, with the tab's URL.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| URL field | `url_field` | Field (text) | The field holding each tab's address. |
| Screenshot size | `resolution` | Choice | 3840x2160, 2560x1440, 1920x1080, 1600x1200, 1280x960, 1280x720 (the default), 1024x768, or A4 (1123x794). |
| Orientation | `orientation` | Choice | Landscape (`L`, the default) or Portrait (`P`). |
| Output folder | `folder_path` | File (folder) | Where the PowerPoint file and the PNGs are saved. Created if missing; files with the same names are replaced. |
| Page load delay (seconds) | `sleep_seconds` | Integer | Extra wait after the page has finished loading. Default 3. |
| Shrink with Tinify | `tinify` | Yes/no | Shrink each PNG with the Tinify service. |
| Tinify API key | `tinify_key` | Password | Needed with Tinify. |
| Shrunk width (pixels) | `tinify_width` | Integer | Needed with Tinify. |
| PowerPoint file name | `output_file_name` | Text | Optional. Empty: `report.pptx`. |
| Username | `auth_username` | Text | Optional, for Basic Authentication. |
| Password | `auth_password` | Password | Optional, for Basic Authentication. Not written to the output. |

## Outputs

- **Slides** (`Output Data`): one record per slide: `URL` (as given), `Screenshot path`, `Screenshot filename`, `PowerPoint file`.

## Limits

- Chrome must reach each page from the machine running Omniscope. The tests use a stand-in for Chrome and the real python-pptx (the file is read back); a run with real headless Chromium gave screenshots of exactly the chosen size on slides of the same shape.
- The slides are pictures: the charts can't be edited in PowerPoint.
- A screenshot shows the page area only: a tab longer than the window is cut at the bottom.
- If one page can't be opened, the block stops with the record number and Chrome's message; no PowerPoint file is written.

## Source

[script.py](script.py)

The sample data in `sample-data/` is invented.
