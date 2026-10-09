"""Source configuration (sources.yaml), run context and the adapter base class."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from crawler import classify
from crawler.config import SERVICE_DIR, Settings
from crawler.fetch import Fetcher
from crawler.models import SOURCE_KINDS, Candidate, SourceRef

if TYPE_CHECKING:
    from crawler.ai.extractor import Extractor


class SourceConfig(BaseModel):
    """One entry of sources.yaml."""

    id: str
    adapter: Literal["tabular", "html", "ai_page"]
    kind: str
    name: str
    enabled: bool = True
    source_url: str | None = None  # what dcp.dealer_sources points at (defaults to the fetched URL / dataset)
    # tabular: a data.gov.in API resource id, or a local CSV / XLSX / JSON file (relative to data-crawler-service/)
    datagov_resource: str | None = None
    api_filters: dict[str, str] = Field(default_factory=dict)
    file: str | None = None
    # html / ai_page: pages to read
    urls: list[str] = Field(default_factory=list)
    follow_links: str | None = None  # regex: also read links on those pages whose URL matches (pagination, PDFs)
    max_pages: int = 50
    profile: Literal["mca", "udyam", "generic"] = "generic"
    columns: dict[str, list[str]] = Field(default_factory=dict)  # extra header spellings per field
    filter: Literal["tobacco", "none"] = "tobacco"
    default_dealer_type: str | None = None
    default_products: list[str] = Field(default_factory=list)  # e.g. [Tobacco] for a list that is all tobacco
    ai_fallback: bool = True  # html: let the AI read a page when no table matched
    hint: str = ""  # context for the AI ("list of registered tobacco exporters")
    max_rows: int | None = None

    @model_validator(mode="after")
    def _check(self) -> SourceConfig:
        if self.kind not in SOURCE_KINDS:
            raise ValueError(f"{self.id}: unknown kind '{self.kind}' (use one of {sorted(SOURCE_KINDS)})")
        if self.adapter == "tabular" and not (self.datagov_resource or self.file):
            raise ValueError(f"{self.id}: a tabular source needs datagov_resource or file")
        if self.adapter in ("html", "ai_page") and not self.urls:
            raise ValueError(f"{self.id}: an {self.adapter} source needs urls")
        if self.default_dealer_type and self.default_dealer_type not in classify.DEALER_TYPES:
            raise ValueError(f"{self.id}: default_dealer_type must be one of {classify.DEALER_TYPES}")
        return self

    def file_path(self) -> Path | None:
        if not self.file:
            return None
        path = Path(self.file)
        return path if path.is_absolute() else SERVICE_DIR / path


def load_sources(path: Path) -> list[SourceConfig]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = [SourceConfig(**entry) for entry in data.get("sources", [])]
    ids = Counter(s.id for s in sources)
    duplicates = [i for i, n in ids.items() if n > 1]
    if duplicates:
        raise ValueError(f"duplicate source ids in {path.name}: {duplicates}")
    return sources


@dataclass
class Context:
    settings: Settings
    fetcher: Fetcher
    extractor: Extractor | None = None
    today: date = field(default_factory=date.today)
    stats: Counter[str] = field(default_factory=Counter)
    messages: list[str] = field(default_factory=list)

    def log(self, message: str) -> None:
        self.messages.append(message)
        print(message, flush=True)


def norm_header(header: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(header or "").lower())


class Adapter(ABC):
    def __init__(self, config: SourceConfig, ctx: Context):
        self.config = config
        self.ctx = ctx

    def source_ref(self, url: str | None = None, external_id: str | None = None, evidence: dict | None = None) -> SourceRef:
        return SourceRef(
            url=self.config.source_url or url or "",
            kind=self.config.kind,
            name=self.config.name,
            external_id=external_id,
            evidence=evidence,
            first_seen=self.ctx.today,
            last_seen=self.ctx.today,
        )

    def finish(self, candidate: Candidate) -> Candidate:
        """Source defaults + external id, applied to every candidate before the filter."""
        if not candidate.products and self.config.default_products:
            candidate.products = list(self.config.default_products)
        candidate.source.external_id = candidate.cin or candidate.gstin or candidate.udyam_no or candidate.other_id
        return candidate

    def keep(self, candidate: Candidate) -> bool:
        """The source's filter: tobacco = a tobacco industry code or tobacco products in the activity text."""
        if self.config.filter == "none":
            return True
        return classify.is_tobacco_nic(candidate.nic_code) or bool(candidate.products)

    @abstractmethod
    def run(self) -> Iterator[Candidate]: ...
