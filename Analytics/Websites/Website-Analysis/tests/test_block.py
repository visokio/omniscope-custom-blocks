"""Tests against a canned website (tests/canned): no request leaves the machine. httpx.AsyncClient is replaced
by one whose transport answers from routes.json and records every request."""
import json
import os
import time

import httpx
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
CANNED = os.path.join(HERE, "tests", "canned")
SITE = "https://www.example.com/"
PAGE_FIELDS = ["url", "text", "title", "h1", "depth", "status", "content_type", "final_url", "error"]


class FakeSite:
    def __init__(self, routes=None, extra=None):
        with open(os.path.join(CANNED, "routes.json"), encoding="utf-8") as fh:
            self.routes = routes or json.load(fh)
        self.extra = extra  # optional function(request) -> response or None, tried first
        self.requests = []

    def __call__(self, request):
        self.requests.append(str(request.url))
        if self.extra:
            resp = self.extra(request)
            if resp is not None:
                return resp
        if request.url.scheme == "http":
            return httpx.Response(301, headers={"Location": str(request.url.copy_with(scheme="https"))})
        if request.url.host == "example.com":
            return httpx.Response(301, headers={"Location": str(request.url.copy_with(host="www.example.com"))})
        if request.url.host != "www.example.com":
            raise httpx.ConnectError("no such host in the canned site", request=request)
        route = self.routes.get(request.url.path)
        if route is None:
            return httpx.Response(404, html="<html><title>Not found</title><h1>Page not found</h1></html>")
        if "redirect" in route:
            return httpx.Response(301, headers={"Location": route["redirect"]})
        if "file" in route:
            with open(os.path.join(CANNED, route["file"]), "rb") as fh:
                body = fh.read()
        else:
            body = route["body"].encode()
        return httpx.Response(route.get("status", 200), content=body,
                              headers={"Content-Type": route.get("type", "text/html; charset=utf-8")})


@pytest.fixture
def site(monkeypatch):
    fake = FakeSite()
    real = httpx.AsyncClient

    class CannedClient(real):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(fake)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", CannedClient)
    return fake


def run(opts):
    return run_block(HERE, None, opts).raise_for_error()


def test_whole_canned_site(site):
    res = run({"url": SITE})
    pages, links, images = res.output(0), res.output(1), res.output(2)
    assert list(pages.columns) == PAGE_FIELDS
    assert list(links.columns) == ["parent", "url", "link_text", "internal"]
    assert list(images.columns) == ["page", "image", "alt"]
    p = pages.set_index("url")
    assert p.index.tolist() == [
        SITE,
        SITE + "about/", SITE + "products/index.html", SITE + "contact", SITE + "old-offers.html",
        SITE + "about/team.html", SITE + "products/pots.html", SITE + "products/tools.html",
        SITE + "products/catalogue.pdf",
        SITE + "products/deep/spades.html",
    ]
    assert p["depth"].tolist() == [0, 1, 1, 1, 1, 2, 2, 2, 2, 3]
    home = p.loc[SITE]
    assert home["title"] == "Fernhill Garden Supplies" and home["h1"] == "Welcome to Fernhill"
    assert "Pots, compost and tools" in home["text"]
    assert "tracking" not in home["text"] and "font-family" not in home["text"]  # no script or style
    assert home["text"].startswith("Skip to content")  # the body's text: the title is in its own field
    # a broken link is listed with its status and an error
    assert p.loc[SITE + "old-offers.html", "status"] == 404
    assert p.loc[SITE + "old-offers.html", "error"] == "HTTP 404 Not Found"
    # a redirect is followed, and the final address recorded
    assert p.loc[SITE + "contact", "status"] == 200 and p.loc[SITE + "contact", "final_url"] == SITE + "contact/"
    assert p.loc[SITE + "contact", "title"] == "Contact"
    # a PDF is listed, not parsed
    pdf = p.loc[SITE + "products/catalogue.pdf"]
    assert pdf["content_type"] == "application/pdf" and pd.isna(pdf["text"]) and pd.isna(pdf["error"])
    # robots.txt: the private page is never requested
    assert SITE + "private/stock.html" not in p.index
    assert not any("/private/" in u for u in site.requests)
    assert "1 pages skipped because the site's robots.txt" in res.final_message

    # links: relative to the page, fragments removed, other sites and mail listed but not followed
    home_links = links[links["parent"] == SITE]
    assert home_links["url"].tolist() == [
        SITE, SITE + "about/", SITE + "products/index.html", SITE + "contact", SITE + "private/stock.html",
        "https://social.example.org/fernhill", "mailto:hello@example.com", SITE + "old-offers.html"]
    assert home_links["internal"].tolist() == [True] * 5 + [False, False, True]
    assert home_links["link_text"].tolist()[1] == "About us"
    assert not any("social.example.org" in u for u in site.requests)
    assert len(links) == 17

    assert images["image"].tolist() == [SITE + "img/logo.png", SITE + "img/shop.jpg", SITE + "img/team.jpg",
                                        SITE + "products/pot-30.jpg"]
    assert images["alt"].tolist()[:2] == ["Fernhill logo", "The shop"] and pd.isna(images["alt"].iloc[2])
    assert res.final_message.startswith("10 pages analysed, 17 links and 4 images found. 1 pages could not")


def test_relative_links_resolve_against_their_page(site):
    # The original joined every link to the site's root, so "team.html" on /about/ became /team.html (a 404),
    # and the real page was never found
    pages = run({"url": SITE + "about/", "max_depth": 1}).output(0)
    assert SITE + "about/team.html" in pages["url"].tolist()
    assert SITE + "team.html" not in pages["url"].tolist()
    assert pages["error"].isna().all()


def test_a_start_address_that_redirects_is_followed(site):
    # The original did not follow redirects: an http:// address (or one without www.) gave an empty page and
    # nothing else. Here both redirect to https://www.example.com/.
    for start in ("http://www.example.com/", "example.com"):
        res = run({"url": start, "max_depth": 1})
        pages = res.output(0)
        assert pages.loc[0, "final_url"] == SITE and pages.loc[0, "title"] == "Fernhill Garden Supplies"
        assert len(pages) == 5, start  # the start page and its four same-site links


def test_fragments_do_not_make_duplicate_pages(site):
    # The original treated tools.html#trowels and tools.html as two pages and fetched both
    pages = run({"url": SITE + "products/index.html", "max_depth": 1}).output(0)
    assert pages["url"].tolist().count(SITE + "products/tools.html") == 1
    assert not any("#" in u for u in pages["url"])
    assert sum(u.endswith("/products/tools.html") for u in site.requests) == 1


def test_depth_and_page_limits(site):
    only_start = run({"url": SITE, "max_depth": 0})
    assert only_start.output(0)["url"].tolist() == [SITE]
    assert len(only_start.output(1)) == 8  # its links are still listed
    capped = run({"url": SITE, "max_pages": 3})
    assert capped.output(0)["url"].tolist() == [SITE, SITE + "about/", SITE + "products/index.html"]
    assert "Stopped at the maximum of 3 pages" in capped.final_message


def test_robots_txt_can_be_ignored(site):
    pages = run({"url": SITE, "max_depth": 1, "respect_robots": False}).output(0)
    assert SITE + "private/stock.html" in pages["url"].tolist()


def test_unreachable_site_gives_empty_but_well_formed_outputs(site):
    # The original wrote nothing at all when the start page failed, so the outputs had no fields
    res = run({"url": "https://unreachable.example.net/"})
    pages = res.output(0)
    assert list(pages.columns) == PAGE_FIELDS and len(pages) == 1
    assert pages.loc[0, "error"].startswith("ConnectError")
    assert len(res.output(1)) == 0 and list(res.output(1).columns) == ["parent", "url", "link_text", "internal"]
    assert len(res.output(2)) == 0 and list(res.output(2).columns) == ["page", "image", "alt"]


def test_bad_options_abort(site):
    for opts, words in (({"url": None}, "Enter the website address"), ({"url": "ftp://example.com/"}, "not a web"),
                        ({"url": SITE, "max_depth": -1}, "0 or more"), ({"url": SITE, "n_workers": 50}, "1 and 20"),
                        ({"url": SITE, "max_pages": 0}, "at least 1")):
        res = run_block(HERE, None, opts)
        assert res.status == "aborted" and words in res.final_message, (opts, res.final_message)
    assert site.requests == []


def test_larger_site(monkeypatch):
    # 400 generated pages, each linking to the next ten: the page limit and timing on a bigger site
    def generated(request):
        n = int(request.url.path.strip("/").split("-")[-1] or 0) if request.url.path.startswith("/p-") else 0
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        body = f"<html><title>Page {n}</title><h1>Page {n}</h1><p>{'word ' * 200}</p>" + "".join(
            f'<a href="/p-{m}">Page {m}</a>' for m in range(n + 1, n + 11) if m < 400) + "</html>"
        return httpx.Response(200, html=body)

    fake = FakeSite(extra=generated)
    real = httpx.AsyncClient

    class CannedClient(real):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(fake)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", CannedClient)
    t0 = time.time()
    res = run({"url": SITE, "max_depth": 1000, "max_pages": 400, "n_workers": 10})
    assert time.time() - t0 < 60
    assert len(res.output(0)) == 400 and res.output(0)["error"].isna().all()
    assert len(res.output(1)) == sum(min(10, 399 - n) for n in range(400))


def test_placeholder_file_is_the_pages_output_of_the_canned_site(site):
    pages = run({"url": SITE}).output(0)
    saved = pd.read_csv(os.path.join(HERE, "sample-data", "placeholder.csv"))
    assert saved["url"].tolist() == pages["url"].tolist()
    assert saved["text"].fillna("").tolist() == pages["text"].fillna("").tolist()
    assert saved["status"].tolist() == pages["status"].tolist()
