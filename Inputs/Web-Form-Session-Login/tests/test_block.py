"""Tests for the Web Form Session Login block. No outside site is called: each test starts a small fake portal on
127.0.0.1 that serves the canned pages in tests/canned/, sets cookies and redirects like a real login, and records
the forms it receives."""
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
CANNED = os.path.join(HERE, "tests", "canned")
USER, PASSWORD = "analyst@example.com", "correct horse"


def page(name):
    with open(os.path.join(CANNED, name), "rb") as fh:
        return fh.read()


class Portal(BaseHTTPRequestHandler):
    posts = []

    def log_message(self, *args):
        pass

    def cookies(self):
        raw = self.headers.get("Cookie", "")
        return dict(p.strip().split("=", 1) for p in raw.split(";") if "=" in p)

    def send(self, status, body=b"", headers=()):
        self.send_response(status)
        for name, value in headers:
            self.send_header(name, value)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/login", "/simple-login"):
            self.send(200, page(self.path[1:] + ".html"), [("Set-Cookie", "csrf=tok-4b9f2e; Path=/; HttpOnly")])
        elif self.path == "/dashboard" and self.cookies().get("portal_session") == "s-7f31":
            self.send(200, page("dashboard.html"))
        elif self.path == "/dashboard":
            self.send(302, headers=[("Location", "/login")])
        elif self.path == "/old-login":
            self.send(301, headers=[("Location", "/login")])
        elif self.path == "/broken":
            self.send(500, b"<html><body>Server error</body></html>")
        else:
            self.send(404, b"<html><body>Not found</body></html>")

    def do_POST(self):
        form = {k: v[0] for k, v in parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode()).items()}
        Portal.posts.append((self.path, form, self.cookies()))
        if self.path != "/session":
            self.send(200, b"<html><body>Thanks for subscribing</body></html>")
        elif form.get("email") == "locked@example.com":
            self.send(403, b"<html><body>Account locked</body></html>")
        elif (form.get("email"), form.get("pass"), form.get("authenticity_token"), self.cookies().get("csrf")) == \
                (USER, PASSWORD, "tok-4b9f2e", "tok-4b9f2e"):
            self.send(303, headers=[("Location", "/dashboard"),
                                    ("Set-Cookie", "portal_session=s-7f31; Path=/; HttpOnly"),
                                    ("Set-Cookie", "remember_me=yes; Path=/; Expires=Wed, 01 Apr 2099 12:00:00 GMT")])
        else:
            self.send(200, page("login.html"))  # wrong password: the form again


@pytest.fixture
def portal(monkeypatch):
    for name in ("NO_PROXY", "no_proxy"):
        monkeypatch.setenv(name, "127.0.0.1,localhost")
    Portal.posts = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Portal)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def login(url, **options):
    return run_block(HERE, None, {"url": url, "username": USER, "password": PASSWORD, **options})


def test_logs_in_and_outputs_the_session(portal):
    res = login(portal + "/login").raise_for_error()
    headers, cookies = res.output(0), res.output(1)
    assert sorted(cookies["Cookie name"]) == ["csrf", "portal_session", "remember_me"]
    session = cookies[cookies["Cookie name"] == "portal_session"].iloc[0]
    assert session["Cookie value"] == "s-7f31" and session["Path"] == "/" and pd.isna(session["Expires"])
    assert cookies.loc[cookies["Cookie name"] == "remember_me", "Expires"].iloc[0] == pd.Timestamp("2099-04-01 12:00:00")
    # the redirect after the login is followed, with the new cookie
    post = headers[headers["Stage"] == "POST login"]
    assert post["Status code"].unique().tolist() == [303, 200]
    assert post.loc[post["Hop"] == 1, "Request Cookie header"].iloc[0].count("portal_session=s-7f31") == 1
    assert (headers["Is Set-Cookie"] & (headers["Header value"].str.startswith("remember_me"))).sum() == 1
    assert "status 200; 1 redirect(s); 3 cookie(s)" in res.final_message


def test_fills_in_the_login_form_not_the_newsletter_form(portal):
    # The original block took the first POST form on the page, the newsletter sign-up, and stopped with
    # "Could not locate a named password field" (it also missed type="Password" written with a capital)
    login(portal + "/login").raise_for_error()
    path, form, cookies = Portal.posts[0]
    assert path == "/session"
    assert form == {"authenticity_token": "tok-4b9f2e", "email": USER, "pass": PASSWORD, "commit": "Sign in"}
    assert cookies == {"csrf": "tok-4b9f2e"}


def test_wrong_password_stops_with_a_message(portal):
    # The original block reported "Login request completed" when the site showed the login form again
    res = login(portal + "/simple-login", password="wrong")
    assert res.status == "aborted" and "still shows a form with a password field" in res.final_message
    res = login(portal + "/simple-login", password="wrong", checkLogin=False).raise_for_error()
    assert "portal_session" not in res.output(1)["Cookie name"].tolist()
    assert "portal_session" in login(portal + "/simple-login").raise_for_error().output(1)["Cookie name"].tolist()


def test_error_status_after_login_stops_with_a_message(portal):
    # The original block reported "Login request completed with status 403"
    res = login(portal + "/simple-login", username="locked@example.com")
    assert res.status == "aborted" and "status 403" in res.final_message
    res = login(portal + "/simple-login", username="locked@example.com", checkLogin=False).raise_for_error()
    assert 403 in res.output(0)["Status code"].tolist()


def test_login_page_behind_a_redirect(portal):
    res = login(portal + "/old-login").raise_for_error()
    get = res.output(0)[res.output(0)["Stage"] == "GET login page"]
    assert get["Status code"].unique().tolist() == [301, 200]
    assert "portal_session" in res.output(1)["Cookie name"].tolist()


def test_pages_without_a_form_or_with_errors(portal):
    res = login(portal + "/missing")
    assert res.status == "aborted" and "404" in res.final_message
    res = login(portal + "/broken")
    assert res.status == "aborted" and "500" in res.final_message
    res = login("http://127.0.0.1:9/login")  # nothing listens on the discard port
    assert res.status == "aborted" and "HTTP request failed" in res.final_message


def test_session_cookie_expiry_types(portal):
    # The original wrote Expires as a number of seconds, decimal when some cookies had none
    cookies = login(portal + "/simple-login").raise_for_error().output(1)
    assert pd.api.types.is_datetime64_any_dtype(cookies["Expires"])


def test_option_checks():
    assert "Login URL" in run_block(HERE, None, {"url": "", "username": USER, "password": PASSWORD}).final_message
    assert "Username" in run_block(HERE, None, {"url": "http://x", "username": None, "password": "p"}).final_message
    assert "Password" in run_block(HERE, None, {"url": "http://x", "username": USER, "password": None}).final_message


def test_repeated_logins_are_quick(portal):
    t0 = time.time()
    for _ in range(20):
        login(portal + "/login").raise_for_error()
    assert time.time() - t0 < 30
