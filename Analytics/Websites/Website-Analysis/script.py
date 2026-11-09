"""Website Analysis: follows the links of a website from a start page and lists its pages (with their text), the
links between them and their images."""
import asyncio
import re
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
from omniscope.api import OmniscopeApi

api = OmniscopeApi()

url = (api.get_option("url") or "").strip()
max_depth = api.get_option("max_depth")
n_workers = api.get_option("n_workers")
max_pages = api.get_option("max_pages")
respect_robots = api.get_option("respect_robots")

if not url:
    api.abort("Enter the website address to start from, for example https://www.example.com/.")
if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
    url = "https://" + url
if urlparse(url).scheme not in ("http", "https") or not urlparse(url).netloc:
    api.abort(f"{url} is not a web address (it should start with https:// or http://).")
max_depth = 4 if max_depth is None else int(max_depth)
n_workers = 5 if n_workers is None else int(n_workers)
max_pages = 100 if max_pages is None else int(max_pages)
if max_depth < 0:
    api.abort("Link depth must be 0 or more (0 analyses only the start page).")
if not 1 <= n_workers <= 20:
    api.abort("Pages fetched at once must be between 1 and 20.")
if max_pages < 1:
    api.abort("Maximum pages must be at least 1.")

import httpx  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

USER_AGENT = "Mozilla/5.0 (compatible; Omniscope Website Analysis block)"
TIMEOUT = 20.0
HTML_TYPES = ("text/html", "application/xhtml+xml")


def host(u):
    return (urlparse(u).hostname or "").lower()


def clean(u):
    """Absolute address without its #fragment; a bare host gets its "/"."""
    u = urldefrag(u)[0]
    parts = urlparse(u)
    if parts.scheme in ("http", "https") and parts.netloc and not parts.path:
        u = parts._replace(path="/").geturl()
    return u


def page_text(soup):
    """The visible text of the page body, on one line."""
    root = soup.body or soup
    for tag in root(["script", "style", "noscript", "template"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", root.get_text(" ")).strip()
    return re.sub(r" ([.,;:!?])(?=\s|$)", r"\1", text)


def tag_text(tag):
    return re.sub(r"\s+", " ", tag.get_text(" ")).strip() if tag is not None else None


class Site:
    def __init__(self, start):
        self.start = start
        self.site_host = host(start)
        self.pages, self.links, self.images = [], [], []
        self.seen = set()
        self.robots = None
        self.skipped_robots = 0
        self.truncated = False

    def allowed(self, u):
        return self.robots is None or self.robots.can_fetch(USER_AGENT, u)

    async def load_robots(self, client):
        robots_url = urljoin(self.start, "/robots.txt")
        try:
            resp = await client.get(robots_url)
        except httpx.HTTPError:
            return
        if resp.status_code == 200:
            parser = RobotFileParser()
            parser.parse(resp.text.splitlines())
            self.robots = parser

    async def fetch(self, client, u, depth, semaphore):
        """Returns the page record, its links and images, and the same-site addresses it links to."""
        record = {"url": u, "text": None, "title": None, "h1": None, "depth": depth, "status": pd.NA,
                  "content_type": None, "final_url": None, "error": None}
        links, images, found = [], [], []
        async with semaphore:
            try:
                async with client.stream("GET", u) as resp:
                    record["status"] = resp.status_code
                    record["final_url"] = clean(str(resp.url))
                    ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
                    record["content_type"] = ctype or None
                    if resp.status_code >= 400:
                        record["error"] = f"HTTP {resp.status_code} {resp.reason_phrase}".strip()
                        return record, links, images, found
                    if ctype and ctype not in HTML_TYPES:
                        return record, links, images, found  # a file such as a PDF: listed, not downloaded
                    await resp.aread()
                    body = resp.text
            except httpx.HTTPError as exc:
                record["error"] = f"{type(exc).__name__}: {exc}".strip()
                return record, links, images, found
        if depth == 0:
            self.site_host = host(record["final_url"])  # the start page may redirect, say to www.
        soup = BeautifulSoup(body, "html.parser")
        base_tag = soup.find("base", href=True)
        base = urljoin(record["final_url"], base_tag["href"]) if base_tag else record["final_url"]
        record["title"] = tag_text(soup.find("title"))
        record["h1"] = tag_text(soup.find("h1"))
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            target = clean(urljoin(base, href))
            scheme = urlparse(target).scheme
            internal = scheme in ("http", "https") and host(target) == self.site_host
            links.append({"parent": u, "url": target, "link_text": tag_text(a) or None, "internal": internal})
            if internal:
                found.append(target)
        for img in soup.find_all("img", src=True):
            images.append({"page": u, "image": urljoin(base, img["src"].strip()), "alt": img.get("alt")})
        record["text"] = page_text(soup)
        return record, links, images, found

    async def run(self, depth_limit, page_limit, workers):
        limits = httpx.Limits(max_connections=workers)
        async with httpx.AsyncClient(follow_redirects=True, timeout=TIMEOUT, limits=limits,
                                     headers={"User-Agent": USER_AGENT}) as client:
            if respect_robots:
                await self.load_robots(client)
            semaphore = asyncio.Semaphore(workers)
            level, depth = [self.start], 0
            self.seen.add(self.start)
            # Breadth first, one depth at a time, in a fixed order: the same site gives the same pages
            while level and len(self.pages) < page_limit:
                todo = []
                for u in level:
                    if not self.allowed(u):
                        self.skipped_robots += 1
                        continue
                    if len(self.pages) + len(todo) >= page_limit:
                        self.truncated = True
                        break
                    todo.append(u)
                results = await asyncio.gather(*(self.fetch(client, u, depth, semaphore) for u in todo))
                next_level = []
                for record, links, images, found in results:
                    self.pages.append(record)
                    self.links += links
                    self.images += images
                    if record["final_url"]:
                        self.seen.add(clean(record["final_url"]))
                    if depth < depth_limit:
                        for target in found:
                            if target not in self.seen:
                                self.seen.add(target)
                                next_level.append(target)
                level, depth = next_level, depth + 1
            if level and any(self.allowed(u) for u in level):
                self.truncated = True


site = Site(clean(url))
asyncio.run(site.run(max_depth, max_pages, n_workers))

pages = pd.DataFrame(site.pages, columns=["url", "text", "title", "h1", "depth", "status", "content_type",
                                          "final_url", "error"])
pages["depth"] = pages["depth"].astype("int64")
pages["status"] = pd.array(pages["status"].tolist(), dtype="Int64")
for c in ("url", "text", "title", "h1", "content_type", "final_url", "error"):
    pages[c] = pages[c].astype(object)

links = pd.DataFrame(site.links, columns=["parent", "url", "link_text", "internal"])
links["internal"] = links["internal"].astype(bool)
for c in ("parent", "url", "link_text"):
    links[c] = links[c].astype(object)

images = pd.DataFrame(site.images, columns=["page", "image", "alt"])
for c in images.columns:
    images[c] = images[c].astype(object)

api.write_output(pages, "Output Data")
api.write_output(links, "Output Data 2")
api.write_output(images, "Output Data 3")

failed = int(pages["error"].notna().sum())
message = f"{len(pages)} pages analysed, {len(links)} links and {len(images)} images found."
if failed:
    message += f" {failed} pages could not be read (see the error field)."
if site.truncated:
    message += f" Stopped at the maximum of {max_pages} pages."
if site.skipped_robots:
    message += f" {site.skipped_robots} pages skipped because the site's robots.txt asks not to fetch them."
api.commit(message)
