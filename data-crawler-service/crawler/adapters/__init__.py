"""Source adapters: `tabular` (open-data API / files), `html` (tables first, AI fallback), `ai_page` (AI only)."""

from crawler.adapters.base import Adapter, Context, SourceConfig, load_sources
from crawler.adapters.html import AiPageAdapter, HtmlAdapter
from crawler.adapters.tabular import TabularAdapter

ADAPTERS: dict[str, type[Adapter]] = {"tabular": TabularAdapter, "html": HtmlAdapter, "ai_page": AiPageAdapter}

__all__ = ["ADAPTERS", "Adapter", "Context", "SourceConfig", "load_sources"]
