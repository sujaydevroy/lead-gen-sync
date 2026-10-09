from __future__ import annotations

import json

import pytest

from crawler.fetch import FetchError
from tests.conftest import FakeWeb


def test_cache_is_reused_and_secrets_never_stored(settings):
    web = FakeWeb({"https://api.example/data": (200, '{"records": []}', "application/json")})
    fetcher = web.fetcher(settings)
    page = fetcher.get("https://api.example/data", params={"api-key": "SECRET123", "offset": 0})
    assert page.url == "https://api.example/data?offset=0" and "SECRET123" not in page.final_url
    again = fetcher.get("https://api.example/data", params={"api-key": "SECRET123", "offset": 0})
    assert again.from_cache and fetcher.requests_made == 2  # robots.txt + the page, nothing for the second get
    for path in settings.cache_dir.rglob("*"):
        if path.is_file() and path.suffix == ".json":
            assert "SECRET123" not in path.read_text()
    assert json.loads(again.text()) == {"records": []}


def test_robots_txt_is_honoured(settings):
    web = FakeWeb(
        {
            "https://site.example/robots.txt": (200, "User-agent: *\nDisallow: /private", "text/plain"),
            "https://site.example/public": (200, "ok", "text/html"),
        }
    )
    fetcher = web.fetcher(settings)
    assert fetcher.get("https://site.example/public").text() == "ok"
    with pytest.raises(FetchError, match="robots.txt"):
        fetcher.get("https://site.example/private/list")


def test_unreachable_robots_txt_means_not_allowed(settings):
    web = FakeWeb({"https://down.example/robots.txt": (503, "busy", "text/plain")})
    with pytest.raises(FetchError, match="robots.txt"):
        web.fetcher(settings).get("https://down.example/page")


def test_retries_and_per_host_delay(settings):
    settings.delay_seconds = 1.0
    attempts = {"n": 0}
    web = FakeWeb()

    def flaky(request):
        if str(request.url).endswith("/robots.txt"):
            return web_response(404, "")
        attempts["n"] += 1
        return web_response(503, "busy") if attempts["n"] == 1 else web_response(200, "fine")

    import httpx

    def web_response(status, body):
        return httpx.Response(status, text=body)

    slept: list[float] = []
    fetcher = web.fetcher(settings, sleep=slept.append)
    fetcher.client = httpx.Client(transport=httpx.MockTransport(flaky))
    assert fetcher.get("https://slow.example/list").text() == "fine"
    assert attempts["n"] == 2 and any(s >= 1 for s in slept)  # back-off after the 503


def test_http_errors_raise(settings):
    web = FakeWeb({"https://site.example/gone": (410, "gone", "text/html")})
    with pytest.raises(FetchError, match="HTTP 410"):
        web.fetcher(settings).get("https://site.example/gone")
