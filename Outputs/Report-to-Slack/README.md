# Send Report to Slack

Takes a screenshot of the Report tab at each input record's URL and posts it to a Slack channel with the record's message and the link; optionally also one PDF of all screenshots.

A link to a dashboard is easy to ignore; a picture of it, in the channel, with a line saying what changed, gets read. This block posts a screenshot of each Report tab in its input to a Slack channel, with its message and a link to the live Report.

- Each input record holds a **Report URL** (a Report tab, or any web page the server can reach) and a **message**.
- The tab is opened in Chrome with its page area at the **screenshot size** (Portrait turns it on its side), and the PNG is posted to the channel with the message and the link. The link is added after the message unless the message already holds the URL.
- Web addresses in the message become links; `&`, `<` and `>` are escaped. A link ends at the first space.
- **Also post a PDF** (ticked by default): after the screenshots, one PDF with a page per screenshot is posted.
- **Shrink with Tinify** shrinks each PNG to a width with the Tinify web service before posting (needs an API key). The screenshots are uploaded to Tinify (api.tinify.com) as well as to Slack.
- **Username and password**, for a Report behind Basic Authentication, are used only to open the page: the link posted to Slack is the URL as given. Chrome sends them in the address (`user:password@host`), so over `http://` to another machine they travel unencrypted: use `https://`, or the server's own address (`127.0.0.1`).
- The same URL is opened by Chrome and posted as the link, so for a link that works in Slack, use an address its readers can open (the server's name rather than `127.0.0.1`).
- Records with an empty URL are skipped. A record that fails (the page doesn't open, Slack refuses) is listed in the Errors output and the others carry on; if nothing at all could be posted, the block stops with the first error, so a scheduled run shows as failed.
- The screenshots and the PDF are made in a temporary folder, deleted at the end.

## Language and libraries

Python. It uses visokio-omniprint (MIT; Visokio's printing package, whose source is in this repository under [`visokio-omniprint/`](../../visokio-omniprint)), requests (Apache License 2.0) for Slack's Web API, and pandas (BSD 3-Clause). visokio-omniprint drives Chrome with selenium (Apache License 2.0), installs it with webdriver-manager (Apache License 2.0) and get-chrome-driver (MIT), makes the PDF with fpdf (LGPL v3) and calls Tinify with tinify (MIT).

Omniscope installs visokio-omniprint and requests with pip on first run (the manifest's `dependencies`). **Chrome** is needed too: on a server that runs custom blocks in Docker, the block uses its own image with Chrome included (the manifest's `docker` settings); otherwise Chrome must be installed on the machine running Omniscope.

## Setting up Slack

1. Create an app at [api.slack.com/apps](https://api.slack.com/apps) (From scratch), in your workspace.
2. Under **OAuth & Permissions**, add the bot token scope `files:write`.
3. Install the app in the workspace and copy the **Bot User OAuth Token** (`xoxb-...`).
4. In the channel, `/invite @your-app`. The **channel ID** is at the bottom of the channel's details (About tab), such as `C0123ABCD`.

## Inputs

- **Input 1**: one record per screenshot to post, with its URL and message.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Report URL field | `url_field` | Field (text) | The field holding each page's address. |
| Username | `auth_username` | Text | Optional, for Basic Authentication. |
| Password | `auth_password` | Password | Optional, for Basic Authentication. Never posted. |
| Screenshot size | `resolution` | Choice | 3840x2160 to 1024x768, or A4 (1123x794); default 1280x720. |
| Orientation | `orientation` | Choice | Landscape (`L`, the default) or Portrait (`P`). |
| Page load delay (seconds) | `sleep_seconds` | Integer | Extra wait after the page has finished loading. Default 3. |
| Also post a PDF | `create_pdf` | Yes/no | Post one PDF of all the screenshots after them. Ticked by default. |
| Compress the PDF | `compression` | Yes/no | Lossless; the size hardly changes. |
| Shrink with Tinify | `tinify` | Yes/no | Shrink each PNG with the Tinify service. |
| Tinify API key | `tinify_key` | Password | Needed with Tinify. |
| Shrunk width (pixels) | `tinify_width` | Integer | Needed with Tinify. |
| Channel ID | `channelID` | Text | Such as `C0123ABCD`. The app must be in the channel. |
| Bot User OAuth token | `authToken` | Password | Starts with `xoxb-`. |
| Message field | `message` | Field | The field holding each record's message. |

## Outputs

- **Results** (`Output Data`): one record per input record: `Row` (from 0), `Status` (`posted`, `skipped` or `error`), `SlackFileId`.
- **Errors** (`Output Data 2`): one record per error: `Row` (or `PDF`) and `Error` (the page's or Slack's message, with any password hidden).

## Limits

- Chrome must reach each page from the machine running Omniscope. The tests use stand-ins for Chrome and for Slack's API (canned replies in `tests/canned/`) and check every request; nothing is sent to Slack.
- Everyone in the channel sees the screenshots, whatever their permissions on the Report: choose the channel as you would choose who gets the Report by email.
- A screenshot shows the page area only: a tab longer than the window is cut at the bottom.
- Each screenshot is a separate post; Slack limits how fast an app can upload files, so post tens of screenshots per run, not thousands.

## Source

[script.py](script.py)

The sample data in `sample-data/` is invented.
