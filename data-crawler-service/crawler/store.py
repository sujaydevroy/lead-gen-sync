"""File storage under CRAWLER_DATA_DIR (Phase 0 keeps everything in files; DESIGN.md §7 moves it to a `crawl`
schema later).

var/snapshots/<source>.jsonl   latest candidates of each source (a new crawl of a source replaces its file)
var/state/identity.json        matching key -> Dealer ID
var/out/                       publish output (upload file + report)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from crawler.config import Settings
from crawler.models import Candidate


def snapshot_path(settings: Settings, source_id: str) -> Path:
    return settings.snapshot_dir / f"{source_id}.jsonl"


def write_snapshot(settings: Settings, source_id: str, candidates: list[Candidate]) -> Path:
    """Atomically replace the source's snapshot (a failed crawl never leaves half a file behind)."""
    path = snapshot_path(settings, source_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".jsonl.tmp")
    with temp.open("w", encoding="utf-8") as handle:
        for candidate in candidates:
            handle.write(candidate.model_dump_json() + "\n")
    os.replace(temp, path)
    return path


def read_snapshot(path: Path) -> list[Candidate]:
    with path.open(encoding="utf-8") as handle:
        return [Candidate.model_validate_json(line) for line in handle if line.strip()]


def read_all_snapshots(settings: Settings) -> dict[str, list[Candidate]]:
    if not settings.snapshot_dir.exists():
        return {}
    return {path.stem: read_snapshot(path) for path in sorted(settings.snapshot_dir.glob("*.jsonl"))}


def read_existing_directory(path: Path | None) -> list[dict]:
    """Dealers already in the portal (a dealers.json-shaped export), so matches keep the portal's Dealer ID."""
    if not path:
        return []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, list) else data.get("dealers", [])
