# Website Analysis

Follows the links of a website from a start page and lists its pages with their title, heading, text and status, the links on each page, and the images.

Use it to take stock of a website: which pages it has and how they are titled, which links are broken, which pages are many clicks from the home page, which images have no alternative text, or to collect the text of a site's pages for searching or text analysis.

How it works:

- It reads the **start page**, then the pages it links to on the **same site** (the same host name; after a redirect, the host it redirected to), then the pages those link to, up to the **link depth** you set. Links to other sites, e-mail addresses and the like are listed but not visited.
- Pages are read one depth at a time, in the order their links appear, so the same site gives the same pages in the same order. It stops at the **maximum pages**.
- Links are resolved against the page they are on (and its `<base>` tag, if any), with any `#fragment` removed, so `team.html` on `/about/` is `/about/team.html` and `tools.html#trowels` is the same page as `tools.html`.
- **Redirects** are followed; the address a page ended up at is in `final_url`.
- Pages that fail (a 404, a server error, a timeout, a host that can't be reached) are listed with their `status` and an `error`; their links are not followed.
- Addresses that are not web pages (a PDF, an image, a ZIP file) are listed with their `content_type` but not downloaded.
- The **text** is the visible text of the page body on one line: scripts and styles are left out.
- With **Respect robots.txt** ticked (the default), it reads the site's `/robots.txt` first and skips the pages it asks crawlers not to fetch. Requests carry the user agent `Mozilla/5.0 (compatible; Omniscope Website Analysis block)`.

## Language
Python

## Inputs
None. The block starts from the address in its options.

## Options

| Option | Name in script | Type | Default | Description |
|---|---|---|---|---|
| Website address | `url` | Text | | The page to start from, for example `https://www.example.com/`. `https://` is added if you leave it out. |
| Link depth | `max_depth` | Whole number | 4 | How many links to follow away from the start page. 0 reads only the start page. |
| Maximum pages | `max_pages` | Whole number | 100 | The run stops after this many pages. |
| Pages fetched at once | `n_workers` | Whole number | 5 | How many pages are requested at the same time (1 to 20). |
| Respect robots.txt | `respect_robots` | Yes/no | ticked | Skip pages that the site's robots.txt asks crawlers not to fetch. |

## Outputs
- **Pages** (`Output Data`): one record per address visited: `url`, `text`, `title`, `h1` (the first heading), `depth` (clicks from the start page), `status` (the HTTP status, such as 200 or 404), `content_type`, `final_url` (after redirects) and `error` (empty when the page was read).
- **Links** (`Output Data 2`): one record per link on each page read: `parent` (the page it is on), `url` (where it points, made absolute), `link_text` and `internal` (true when it points to the same site).
- **Images** (`Output Data 3`): one record per image on each page read: `page`, `image` (its address, made absolute) and `alt` (its alternative text, empty when it has none).

## Limits
- Pages are read as the server sends them. Content that a page's scripts load after it opens in a browser is not seen, so sites built entirely in JavaScript may show little text and few links.
- Links to other sites are not checked; only same-site pages are fetched and get a status.
- Pages that need a login are not reachable: the block sends no login details or cookies.
- Each page has a 20-second time limit.
- The server running Omniscope fetches the pages, so it needs access to the website (directly or through its proxy). Only analyse sites you are allowed to, keep **Pages fetched at once** low on sites you don't run, and leave **Respect robots.txt** ticked unless the site is yours.
- In tests (with the website simulated, so without network delays), 400 pages took under a second to process. A real site's speed depends on the site.

## Dependencies
HTTPX (version 0.23 or later, BSD licence) for the requests and Beautiful Soup (`beautifulsoup4`, MIT licence) for reading the pages, both listed in the block's dependencies, so Omniscope installs them with pip on first run if they are missing. pandas (BSD licence) comes with Omniscope's Python environment.

## Source
[script.py](script.py)

The tests run against a small simulated website in `tests/canned/` (an invented garden supplies shop at `www.example.com`); no real site is contacted. `sample-data/placeholder.csv` is the Pages output for that simulated site.
