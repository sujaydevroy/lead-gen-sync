"""Shared test helpers: settings in a temp folder, a fake web (httpx MockTransport) and a fake AI extractor."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from crawler.ai.extractor import BusinessProfile, DealerList
from crawler.config import REPO_DIR, Settings
from crawler.fetch import Fetcher

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "var",
        contact_email="crawler@test.example",
        delay_seconds=0.0,
        data_gov_in_api_key=None,
        llm_max_calls=20,
        sector_file=REPO_DIR / "sector.json",
        sources_file=tmp_path / "sources.yaml",
    )


class FakeWeb:
    """Routes URL -> (status, body, content type); robots.txt is 404 (= allowed) unless set."""

    def __init__(self, pages: dict[str, tuple[int, str | bytes, str]] | None = None):
        self.pages = dict(pages or {})
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url).split("?")[0]
        if url not in self.pages:
            return httpx.Response(404, text="not found")
        status, body, content_type = self.pages[url]
        content = body.encode() if isinstance(body, str) else body
        return httpx.Response(status, content=content, headers={"content-type": content_type})

    def fetcher(self, settings: Settings, sleep: Callable[[float], None] = lambda s: None) -> Fetcher:
        client = httpx.Client(transport=httpx.MockTransport(self.handler), follow_redirects=True)
        return Fetcher(settings, client=client, sleep=sleep)


class FakeExtractor:
    """Returns canned answers; records what it was asked."""

    def __init__(self, dealers: DealerList | None = None, profile: BusinessProfile | None = None):
        self.dealers = dealers or DealerList(is_business_list=False)
        self.profile = profile or BusinessProfile(is_business_site=False)
        self.calls = 0
        self.asked: list[str] = []

    def extract_dealers(self, text: str, *, url: str, hint: str) -> DealerList:
        self.calls += 1
        self.asked.append(url)
        return self.dealers

    def extract_profile(self, text: str, *, url: str, expected_name: str | None) -> BusinessProfile:
        self.calls += 1
        self.asked.append(url)
        return self.profile
