"""Minimal file adapter shared by indexing and artifact backfill."""

from pathlib import Path


class StoredFile:
    def __init__(self, path: str, name: str):
        self.path, self.name = Path(path), name

    def getvalue(self) -> bytes:
        return self.path.read_bytes()
