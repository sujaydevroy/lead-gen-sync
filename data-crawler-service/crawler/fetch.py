"""Polite HTTP fetching: robots.txt, one request per host per CRAWLER_DELAY_SECONDS, retries, on-disk cache.

* robots.txt is honoured (RFC 9309): a 4xx robots.txt means "allowed", an unreachable one means "not allowed".
* Every response body is cached gzip-compressed under var/cache/, keyed by URL + parameters. Secret parameters
  (api-key, key, token) are left out of the cache key and of everything written to disk.
* A cached page younger than CRAWLER_CACHE_DAYS is used without a request; an older one is re-validated with
  If-None-Match / If-Modified-Since when the server gave an ETag / Last-Modified.
* 429 / 5xx / network errors are retried 3 times with back-off (Retry-After is honoured, capped at 60 s).
* No login walls, CAPTCHAs or anti-bot workarounds: a blocked page is reported, never bypassed.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

from crawler.config import Settings

SECRET_PARAMS = {"api-key", "api_key", "apikey", "key", "token", "access_token"}
MAX_BYTES = 25 * 1024 * 1024
RETRY_STATUSES = {429, 500, 502, 503, 504}
ATTEMPTS = 3


class FetchError(Exception):
    """The page could not be fetched (HTTP error, blocked by robots.txt, too large, network failure)."""


@dataclass
class Page:
    url: str  # requested URL without secret parameters
    final_url: str
    status: int
    content: bytes
    content_type: str
    fetched_at: datetime
    from_cache: bool = False

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()

    def text(self) -> str:
        match = re.search(r"charset=([\w-]+)", self.content_type or "", re.I)
        for encoding in (match.group(1) if match else None, "utf-8", "cp1252"):
            if not encoding:
                continue
            try:
                return self.content.decode(encoding)
            except (LookupError, UnicodeDecodeError):
                continue
        return self.content.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text())


def public_url(url: str, params: dict[str, Any] | None = None) -> str:
    """URL + query parameters without secrets (for cache keys, logs and the sources written to the output)."""
    visible = {k: v for k, v in (params or {}).items() if k.lower() not in SECRET_PARAMS}
    if not visible:
        return url
    return f"{url}{'&' if '?' in url else '?'}{urlencode(sorted(visible.items()), doseq=True)}"


def strip_secrets(url: str) -> str:
    """The same URL without secret query parameters (a redirect target can carry the api-key)."""
    parts = urlsplit(url)
    if not parts.query:
        return url
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in SECRET_PARAMS]
    return urlunsplit(parts._replace(query=urlencode(kept)))


class Fetcher:
    def __init__(
        self,
        settings: Settings,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.settings = settings
        self.client = client or httpx.Client(
            headers={"User-Agent": settings.user_agent, "Accept-Language": "en-IN,en;q=0.8"},
            follow_redirects=True,
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        self._sleep = sleep
        self._clock = clock
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}
        self.requests_made = 0

    # -- public -----------------------------------------------------------------------------------------------

    def get(self, url: str, *, params: dict[str, Any] | None = None, use_cache: bool = True) -> Page:
        visible = public_url(url, params)
        cached = self._read_cache(visible) if use_cache else None
        if cached and cached[0].fetched_at > datetime.now(UTC) - timedelta(days=self.settings.cache_days):
            return cached[0]
        if not self.allowed(url):
            raise FetchError(f"robots.txt does not allow fetching {visible}")

        headers: dict[str, str] = {}
        if cached:
            meta = cached[1]
            if meta.get("etag"):
                headers["If-None-Match"] = meta["etag"]
            if meta.get("last_modified"):
                headers["If-Modified-Since"] = meta["last_modified"]

        response = self._request(url, params=params, headers=headers)
        if response.status_code == 304 and cached:
            page = cached[0]
            page.fetched_at = datetime.now(UTC)
            self._write_cache(visible, page, cached[1].get("etag"), cached[1].get("last_modified"))
            return page
        if response.status_code >= 400:
            raise FetchError(f"HTTP {response.status_code} for {visible}")
        content = response.content
        if len(content) > MAX_BYTES:
            raise FetchError(f"{visible} is larger than {MAX_BYTES // (1024 * 1024)} MB")
        page = Page(
            url=visible,
            final_url=strip_secrets(str(response.url)),
            status=response.status_code,
            content=content,
            content_type=response.headers.get("content-type", ""),
            fetched_at=datetime.now(UTC),
        )
        self._write_cache(visible, page, response.headers.get("etag"), response.headers.get("last-modified"))
        return page

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            self._robots[origin] = self._load_robots(origin)
        robots = self._robots[origin]
        return robots is None or robots.can_fetch(self.settings.user_agent, url)

    # -- internals --------------------------------------------------------------------------------------------

    def _load_robots(self, origin: str) -> RobotFileParser | None:
        """None = everything allowed (no robots.txt). Unreachable robots.txt = nothing allowed."""
        parser = RobotFileParser()
        try:
            response = self._request(f"{origin}/robots.txt")
        except FetchError:
            parser.parse(["User-agent: *", "Disallow: /"])
            return parser
        if 400 <= response.status_code < 500:
            return None
        if response.status_code >= 500:
            parser.parse(["User-agent: *", "Disallow: /"])
            return parser
        parser.parse(response.text.splitlines())
        return parser

    def _wait_for_host(self, url: str) -> None:
        host = urlsplit(url).netloc
        last = self._last_request.get(host)
        if last is not None:
            remaining = self.settings.delay_seconds - (self._clock() - last)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request[host] = self._clock()

    def _request(self, url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None):
        error: Exception | None = None
        for attempt in range(ATTEMPTS):
            self._wait_for_host(url)
            try:
                response = self.client.get(url, params=params, headers=headers)
                self.requests_made += 1
            except httpx.HTTPError as exc:
                error = exc
                self._sleep(2**attempt)
                continue
            if response.status_code in RETRY_STATUSES and attempt < ATTEMPTS - 1:
                retry_after = response.headers.get("retry-after", "")
                self._sleep(min(float(retry_after), 60.0) if retry_after.isdigit() else 2**attempt)
                continue
            return response
        raise FetchError(f"{public_url(url, params)} could not be fetched: {error}")

    def _cache_paths(self, visible_url: str) -> tuple[Path, Path]:
        key = hashlib.sha256(visible_url.encode()).hexdigest()
        folder = self.settings.cache_dir / key[:2]
        return folder / f"{key}.gz", folder / f"{key}.json"

    def _read_cache(self, visible_url: str) -> tuple[Page, dict[str, Any]] | None:
        body, meta_path = self._cache_paths(visible_url)
        if not (body.exists() and meta_path.exists()):
            return None
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        page = Page(
            url=visible_url,
            final_url=meta["final_url"],
            status=meta["status"],
            content=gzip.decompress(body.read_bytes()),
            content_type=meta.get("content_type", ""),
            fetched_at=datetime.fromisoformat(meta["fetched_at"]),
            from_cache=True,
        )
        return page, meta

    def _write_cache(self, visible_url: str, page: Page, etag: str | None, last_modified: str | None) -> None:
        body, meta_path = self._cache_paths(visible_url)
        body.parent.mkdir(parents=True, exist_ok=True)
        body.write_bytes(gzip.compress(page.content))
        meta = {
            "url": visible_url,
            "final_url": page.final_url,
            "status": page.status,
            "content_type": page.content_type,
            "fetched_at": page.fetched_at.isoformat(),
            "sha256": page.sha256,
            "etag": etag,
            "last_modified": last_modified,
        }
        meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
