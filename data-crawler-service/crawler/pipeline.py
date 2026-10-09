"""crawl -> enrich -> publish (see DESIGN.md §6).

crawl     run source adapters, replace each source's snapshot with what it found
enrich    read websites of merged dealers that miss contacts / products (HTTP first, AI if still missing)
publish   merge all snapshots into dealers, decide their status, write the upload file + a report
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from crawler.adapters import ADAPTERS, Context, SourceConfig
from crawler.config import Settings
from crawler.decide import decide
from crawler.enrich import enrich_dealer, needs_enrichment
from crawler.fetch import Fetcher, FetchError
from crawler.models import Candidate, Dealer
from crawler.resolve import IdentityMap, group, merge
from crawler.store import read_all_snapshots, read_snapshot, snapshot_path, write_snapshot

WEBSITE_SNAPSHOT = "website"
ROWS_PER_FILE = 5000  # the portal's upload accepts up to 20,000 rows per file; smaller files are easier to review


def make_context(settings: Settings, *, use_ai: bool = True, fetcher: Fetcher | None = None, extractor=None) -> Context:
    if extractor is None and use_ai and settings.ai_enabled:
        from crawler.ai.claude import ClaudeExtractor

        extractor = ClaudeExtractor(settings)
    return Context(settings=settings, fetcher=fetcher or Fetcher(settings), extractor=extractor)


def crawl(ctx: Context, sources: list[SourceConfig]) -> dict[str, int]:
    """Candidates found per source id; -1 = the source failed (its previous snapshot is kept)."""
    found: dict[str, int] = {}
    for config in sources:
        ctx.log(f"Crawling {config.id}: {config.name}")
        adapter = ADAPTERS[config.adapter](config, ctx)
        try:
            candidates = list(adapter.run())
        except (FetchError, FileNotFoundError, RuntimeError, ValueError) as exc:
            ctx.log(f"  {config.id} failed: {exc} (previous snapshot kept)")
            found[config.id] = -1
            continue
        write_snapshot(ctx.settings, config.id, candidates)
        found[config.id] = len(candidates)
        ctx.log(f"  {config.id}: {len(candidates)} dealer record(s)")
    return found


def build_dealers(settings: Settings, existing: list[dict[str, Any]] | None = None) -> list[tuple[Dealer, list[Candidate]]]:
    """All snapshots merged into dealers (with status). Website candidates join the dealer they were read for."""
    snapshots = read_all_snapshots(settings)
    identities = IdentityMap(settings.state_dir / "identity.json", existing or [])
    base: list[Candidate] = []
    linked: dict[str, list[Candidate]] = defaultdict(list)
    for source_id in sorted(snapshots):
        for candidate in snapshots[source_id]:
            if candidate.links_to:
                linked[candidate.links_to].append(candidate)
            else:
                base.append(candidate)

    dealers: list[tuple[Dealer, list[Candidate]]] = []
    used: set[str] = set()
    # Clusters with a registration number first, so they claim their codes before phone / email matches do.
    for cluster in sorted(group(base), key=lambda c: not any(x.cin or x.gstin or x.udyam_no for x in c)):
        dealer = merge(cluster, identities, settings.sector_file, used)
        extra = linked.pop(dealer.dealer_code, [])
        if extra:
            cluster = cluster + extra
            dealer = merge(cluster, identities, settings.sector_file, used, code=dealer.dealer_code)
        dealer.status, dealer.status_reason = decide(dealer, cluster)
        dealers.append((dealer, cluster))
    identities.save()
    dealers.sort(key=lambda item: (item[0].state or "", item[0].dealer_name.lower()))
    return dealers


def enrich(ctx: Context, *, limit: int, existing: list[dict[str, Any]] | None = None) -> int:
    """Read up to `limit` dealer websites; returns how many dealers got a website record."""
    dealers = [dealer for dealer, _ in build_dealers(ctx.settings, existing) if needs_enrichment(dealer)]
    path = snapshot_path(ctx.settings, WEBSITE_SNAPSHOT)
    kept = {c.links_to: c for c in (read_snapshot(path) if path.exists() else []) if c.links_to}
    ctx.log(f"Enriching {min(limit, len(dealers))} of {len(dealers)} dealer(s) that have a website and miss details")
    added = 0
    for dealer in dealers[:limit]:
        candidate = enrich_dealer(dealer, ctx)
        if candidate:
            kept[dealer.dealer_code] = candidate
            added += 1
    write_snapshot(ctx.settings, WEBSITE_SNAPSHOT, list(kept.values()))
    return added


def publish(settings: Settings, *, existing: list[dict[str, Any]] | None = None, today: date | None = None) -> dict[str, Any]:
    """Write var/out/dealers_<stamp>[_partN].json for the admin Dealer Upload and report_<stamp>.md / .json."""
    today = today or date.today()
    dealers = build_dealers(settings, existing)
    rows = [dealer.to_upload_row(today) for dealer, _ in dealers]
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    settings.output_dir.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []
    parts = [rows[i : i + ROWS_PER_FILE] for i in range(0, len(rows), ROWS_PER_FILE)] or [[]]
    for number, part in enumerate(parts, start=1):
        suffix = f"_part{number}" if len(parts) > 1 else ""
        path = settings.output_dir / f"dealers_{stamp}{suffix}.json"
        path.write_text(json.dumps(part, ensure_ascii=False, indent=1), encoding="utf-8")
        files.append(path)

    report = _report(dealers, files)
    (settings.output_dir / f"report_{stamp}.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    (settings.output_dir / f"report_{stamp}.md").write_text(_report_markdown(report), encoding="utf-8")
    return report


def _report(dealers: list[tuple[Dealer, list[Candidate]]], files: list[Path]) -> dict[str, Any]:
    reasons: Counter[str] = Counter()
    for dealer, _ in dealers:
        if dealer.status == "Pending":
            for reason in dealer.status_reason.split("; "):
                reasons[reason.split(" (")[0]] += 1
    count = lambda attr: dict(Counter(getattr(d, attr) or "(none)" for d, _ in dealers).most_common())  # noqa: E731
    return {
        "dealers": len(dealers),
        "files": [str(f) for f in files],
        "by_status": count("status"),
        "by_type": count("dealer_type"),
        "by_region": count("region"),
        "by_state": count("state"),
        "pending_reasons": dict(reasons.most_common()),
        "with_phone": sum(1 for d, _ in dealers if d.phone),
        "with_email": sum(1 for d, _ in dealers if d.email),
        "with_website": sum(1 for d, _ in dealers if d.website),
        "sources": dict(Counter(s.name for d, _ in dealers for s in d.sources).most_common()),
        "merged_from_several_records": sum(1 for d, _ in dealers if d.candidate_count > 1),
    }


def _report_markdown(report: dict[str, Any]) -> str:
    def table(title: str, data: dict[str, int]) -> str:
        lines = [f"### {title}", "", "| Value | Dealers |", "|---|---|"]
        lines += [f"| {key} | {value} |" for key, value in data.items()]
        return "\n".join(lines) + "\n"

    total = report["dealers"] or 1
    parts = [
        "# Crawl publish report",
        "",
        f"**{report['dealers']} dealers** in {len(report['files'])} upload file(s):",
        *[f"- `{f}`" for f in report["files"]],
        "",
        f"Phone: {report['with_phone']} ({report['with_phone'] * 100 // total}%), email: {report['with_email']} "
        f"({report['with_email'] * 100 // total}%), website: {report['with_website']}; merged from several records: "
        f"{report['merged_from_several_records']}.",
        "",
        table("Status", report["by_status"]),
        table("Why dealers are Pending", report["pending_reasons"]),
        table("Dealer type", report["by_type"]),
        table("Region", report["by_region"]),
        table("State", report["by_state"]),
        table("Sources", report["sources"]),
        "Upload the file(s) in the portal: Dealer Upload (System Administrator). Re-uploading the next run's file "
        "updates the same dealers (stable Dealer IDs).",
    ]
    return "\n".join(parts) + "\n"
