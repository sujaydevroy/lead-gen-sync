"""Command line.

python -m crawler sources                         list the sources in sources.yaml and their last snapshot
python -m crawler crawl [--source ID ...] [--no-ai]
python -m crawler enrich [--limit 50] [--no-ai]   read dealer websites for missing phone / email / products
python -m crawler publish [--existing dealers.json]
python -m crawler run [--source ID ...] [--limit 50] [--no-ai] [--existing dealers.json]   all three
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from crawler.adapters import load_sources
from crawler.config import Settings, load_env_file
from crawler.pipeline import crawl, enrich, make_context, publish
from crawler.store import read_existing_directory, snapshot_path


def _select(settings: Settings, ids: list[str] | None):
    sources = load_sources(settings.sources_file)
    if not ids:
        return [s for s in sources if s.enabled]
    by_id = {s.id: s for s in sources}
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        raise SystemExit(f"Unknown source id(s): {', '.join(unknown)}. Run: python -m crawler sources")
    return [by_id[i] for i in ids]


def _summary(ctx) -> None:
    if ctx.stats:
        print("Counts: " + ", ".join(f"{k}={v}" for k, v in sorted(ctx.stats.items())))
    extractor = ctx.extractor
    if extractor is not None and getattr(extractor, "usage", None):
        print("AI usage: " + ", ".join(f"{k}={v}" for k, v in extractor.usage.items()))
        for failure in getattr(extractor, "failures", [])[:10]:
            print(f"  AI: {failure}")
    elif extractor is None:
        print("AI: off (set ANTHROPIC_API_KEY to read pages without tables and dealer websites)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m crawler", description="DealerConnect dealer crawler")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sources", help="List configured sources")
    for name in ("crawl", "run"):
        command = sub.add_parser(name, help="Crawl sources" if name == "crawl" else "crawl + enrich + publish")
        command.add_argument("--source", action="append", help="Source id (repeatable); default: all enabled")
        command.add_argument("--no-ai", action="store_true", help="Never call the AI (tables / open data only)")
    enrich_cmd = sub.add_parser("enrich", help="Read dealer websites")
    enrich_cmd.add_argument("--no-ai", action="store_true")
    publish_cmd = sub.add_parser("publish", help="Write the upload file + report")
    for command in (enrich_cmd, publish_cmd, sub.choices["run"]):
        command.add_argument("--existing", type=Path, help="dealers.json-shaped export of the portal's dealers")
    for command in (enrich_cmd, sub.choices["run"]):
        command.add_argument("--limit", type=int, default=50, help="Max websites to read (default 50)")
    args = parser.parse_args(argv)

    load_env_file()
    settings = Settings()
    if args.command == "sources":
        for source in load_sources(settings.sources_file):
            path = snapshot_path(settings, source.id)
            last = f"{sum(1 for _ in path.open(encoding='utf-8'))} records" if path.exists() else "never crawled"
            state = "" if source.enabled else " (disabled)"
            print(f"{source.id:<28} {source.adapter:<8} {source.kind:<16} {last}{state}  {source.name}")
        return 0

    existing = read_existing_directory(getattr(args, "existing", None))
    if args.command == "publish":
        report = publish(settings, existing=existing)
        print(f"{report['dealers']} dealers -> {', '.join(report['files'])}")
        print("Status: " + ", ".join(f"{k} {v}" for k, v in report["by_status"].items()))
        return 0

    ctx = make_context(settings, use_ai=not args.no_ai)
    if args.command in ("crawl", "run"):
        results = crawl(ctx, _select(settings, args.source))
        if args.command == "crawl":
            _summary(ctx)
            return 1 if results and all(v < 0 for v in results.values()) else 0
    if args.command in ("enrich", "run"):
        added = enrich(ctx, limit=args.limit, existing=existing)
        print(f"Website records: {added}")
    _summary(ctx)
    if args.command == "run":
        report = publish(settings, existing=existing)
        print(f"{report['dealers']} dealers -> {', '.join(report['files'])}")
        print("Status: " + ", ".join(f"{k} {v}" for k, v in report["by_status"].items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
