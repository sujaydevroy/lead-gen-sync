"""Settings from environment variables or data-crawler-service/.env (never hard-coded secrets).

CRAWLER_DATA_DIR        where the page cache, source snapshots, identity map and outputs go (default: ./var)
CRAWLER_CONTACT_EMAIL   put in the User-Agent so site owners can reach us (recommended)
CRAWLER_DELAY_SECONDS   minimum seconds between two requests to the same host (default 1.0)
CRAWLER_CACHE_DAYS      re-use a cached page for this many days before asking the server again (default 7)
DATA_GOV_IN_API_KEY     free key from data.gov.in (My Account -> API key) for the open-data API adapters
ANTHROPIC_API_KEY       enables AI extraction (read by the anthropic SDK itself)
CRAWLER_LLM_MODEL       extraction model (default claude-haiku-5-5, as priced in DESIGN.md §9)
CRAWLER_LLM_RETRY_MODEL model for a retry when the first model fails on a page (default claude-sonnet-5-5)
CRAWLER_LLM_MAX_CALLS   hard cap on AI calls per command (default 200), so a run can't overspend
CRAWLER_SECTOR_FILE     sector.json used to map products to sectors (default: ../sector.json, the repo's file)
CRAWLER_SOURCES_FILE    source list (default: sources.yaml next to this package)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = SERVICE_DIR.parent


def load_env_file(path: Path = SERVICE_DIR / ".env") -> None:
    """KEY=VALUE lines from data-crawler-service/.env (gitignored); variables already set in the shell win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _float(name: str, default: float) -> float:
    value = os.environ.get(name)
    return float(value) if value else default


def _int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value else default


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("CRAWLER_DATA_DIR") or SERVICE_DIR / "var"))
    contact_email: str | None = field(default_factory=lambda: os.environ.get("CRAWLER_CONTACT_EMAIL") or None)
    delay_seconds: float = field(default_factory=lambda: _float("CRAWLER_DELAY_SECONDS", 1.0))
    cache_days: int = field(default_factory=lambda: _int("CRAWLER_CACHE_DAYS", 7))
    data_gov_in_api_key: str | None = field(default_factory=lambda: os.environ.get("DATA_GOV_IN_API_KEY") or None)
    llm_model: str = field(default_factory=lambda: os.environ.get("CRAWLER_LLM_MODEL") or "claude-haiku-5-5")
    llm_retry_model: str = field(default_factory=lambda: os.environ.get("CRAWLER_LLM_RETRY_MODEL") or "claude-sonnet-5-5")
    llm_max_calls: int = field(default_factory=lambda: _int("CRAWLER_LLM_MAX_CALLS", 200))
    sector_file: Path = field(default_factory=lambda: Path(os.environ.get("CRAWLER_SECTOR_FILE") or REPO_DIR / "sector.json"))
    sources_file: Path = field(
        default_factory=lambda: Path(os.environ.get("CRAWLER_SOURCES_FILE") or SERVICE_DIR / "sources.yaml")
    )

    @property
    def user_agent(self) -> str:
        contact = f"; contact: {self.contact_email}" if self.contact_email else ""
        return f"DealerConnectBot/0.1 (+business directory research{contact})"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def snapshot_dir(self) -> Path:
        """Latest extracted candidates per source (one JSON-lines file per source)."""
        return self.data_dir / "snapshots"

    @property
    def state_dir(self) -> Path:
        return self.data_dir / "state"

    @property
    def output_dir(self) -> Path:
        return self.data_dir / "out"

    @property
    def ai_enabled(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
