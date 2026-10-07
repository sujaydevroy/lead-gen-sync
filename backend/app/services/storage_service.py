"""File storage for attachments and uploaded workbooks.

Only the local-disk backend is implemented. Keys are generated server-side; user-supplied file
names are sanitised and never used to build directory paths.
"""

from __future__ import annotations

import re
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings


class Storage(Protocol):
    backend: str

    def save(self, key: str, content: bytes) -> str: ...
    def read(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def physical_path(self, key: str) -> str: ...


def safe_file_name(name: str, fallback: str = "file") -> str:
    """Keep a readable, filesystem-safe base name (no paths, no control characters)."""
    base = Path(name.replace("\\", "/")).name
    base = re.sub(r"[^A-Za-z0-9._ -]+", "_", base).strip(" .")
    return (base or fallback)[:120]


def build_key(*parts: str, file_name: str) -> str:
    return "/".join([*parts, uuid.uuid4().hex, safe_file_name(file_name)])


class LocalStorage:
    backend = "local"

    def __init__(self, root: Path):
        self.root = root.resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Invalid storage key.")
        return path

    def save(self, key: str, content: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return key

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def physical_path(self, key: str) -> str:
        """Absolute location of the stored file on this server's disk."""
        return str(self._path(key))


@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    return LocalStorage(settings.storage_local_dir)
