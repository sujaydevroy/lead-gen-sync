"""HTML / PDF list pages (e.g. Tobacco Board registers, trade-fair exhibitor lists) — the hybrid adapter.

1. HTTP first: every <table> (or PDF table) whose header has a name column plus at least one other known column
   is read row by row, without AI.
2. AI fallback: when a page has no usable table (irregular layout, plain-text PDF), the page text goes to the
   extractor and every returned value is grounded against that text.
`adapter: ai_page` skips step 1 for pages known to have no tables. `follow_links` adds matching links
(pagination, PDF lists) from each page, up to `max_pages`.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from crawler.adapters.base import Adapter
from crawler.adapters.columns import column_map
from crawler.ai.extractor import BudgetExhausted, ground, snippet
from crawler.ai.text import Table, html_tables, html_to_text, links, pdf_text_and_tables
from crawler.fetch import FetchError, Page
from crawler.models import Candidate
from crawler.normalize import build_candidate


def is_pdf(page: Page) -> bool:
    return "pdf" in (page.content_type or "").lower() or page.content[:5] == b"%PDF-"


class HtmlAdapter(Adapter):
    use_tables = True

    def run(self) -> Iterator[Candidate]:
        queue = list(self.config.urls)
        seen: set[str] = set()
        follow = re.compile(self.config.follow_links) if self.config.follow_links else None
        while queue and len(seen) < self.config.max_pages:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            try:
                page = self.ctx.fetcher.get(url)
            except FetchError as exc:
                self.ctx.log(f"  {self.config.id}: {exc}")
                self.ctx.stats["fetch_errors"] += 1
                continue
            self.ctx.stats["pages"] += 1
            if is_pdf(page):
                text, tables = pdf_text_and_tables(page.content)
            else:
                html = page.text()
                text, tables = html_to_text(html), html_tables(html)
                if follow:
                    queue.extend(link for link, _ in links(html, page.final_url) if follow.search(link) and link not in seen)
            found = list(self._from_tables(tables, page.final_url)) if self.use_tables else []
            if found:
                self.ctx.stats["pages_read_by_tables"] += 1
                yield from found
            elif self.config.ai_fallback or not self.use_tables:
                yield from self._from_ai(text, page.final_url)
            else:
                self.ctx.log(f"  {self.config.id}: no dealer table on {page.final_url}")

    def _from_tables(self, tables: list[Table], url: str) -> Iterator[Candidate]:
        for table in tables:
            mapping = column_map(table.headers, self.config.profile, self.config.columns)
            if "dealer_name" not in mapping or len(mapping) < 2:
                continue
            for cells in table.rows:
                raw = {field: cells[i] if i < len(cells) else None for field, i in mapping.items()}
                candidate = build_candidate(
                    raw,
                    self.source_ref(url, evidence={"row": " | ".join(cells)[:500]}),
                    extractor="adapter:html_table",
                    default_type=self.config.default_dealer_type,
                )
                if candidate and self.keep(self.finish(candidate)):
                    self.ctx.stats["candidates"] += 1
                    yield candidate

    def _from_ai(self, text: str, url: str) -> Iterator[Candidate]:
        extractor = self.ctx.extractor
        if extractor is None:
            self.ctx.stats["pages_skipped_no_ai"] += 1
            self.ctx.log(f"  {self.config.id}: {url} needs AI extraction (set ANTHROPIC_API_KEY); skipped")
            return
        if not text.strip():
            return
        try:
            result = extractor.extract_dealers(text, url=url, hint=self.config.hint)
        except BudgetExhausted as exc:
            self.ctx.stats["pages_skipped_ai_budget"] += 1
            self.ctx.log(f"  {self.config.id}: {exc}; {url} skipped")
            return
        self.ctx.stats["pages_read_by_ai"] += 1
        model = getattr(extractor, "settings", None)
        label = f"ai:{model.llm_model}" if model else "ai"
        for dealer in result.dealers:
            grounded = ground(dealer, text)
            if grounded is None:
                self.ctx.stats["ai_records_rejected"] += 1
                continue
            raw, dropped = grounded
            self.ctx.stats["ai_values_dropped"] += len(dropped)
            evidence = {"snippet": snippet(text, dealer.dealer_name)}
            if dropped:
                evidence["dropped_unverified"] = dropped
            candidate = build_candidate(
                raw, self.source_ref(url, evidence=evidence), extractor=label, default_type=self.config.default_dealer_type
            )
            if candidate and self.keep(self.finish(candidate)):
                self.ctx.stats["candidates"] += 1
                yield candidate


class AiPageAdapter(HtmlAdapter):
    use_tables = False
