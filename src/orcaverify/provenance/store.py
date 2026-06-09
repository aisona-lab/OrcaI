from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path


class ProvenanceStore(ABC):
    """Where records live. Swap FileStore for Postgres/S3 later without touching the ledger."""

    @abstractmethod
    def append(self, record: dict) -> None: ...

    @abstractmethod
    def read(self) -> list[dict]: ...


class FileStore(ProvenanceStore):
    """Append-only JSONL file. One record per line."""

    def __init__(self, path):
        self.path = Path(path)

    def append(self, record: dict) -> None:
        with self.path.open("a") as fh:
            fh.write(json.dumps(record) + "\n")

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open() as fh:
            return [json.loads(line) for line in fh if line.strip()]


class InMemoryStore(ProvenanceStore):
    """For tests and ephemeral use."""

    def __init__(self):
        self._records: list[dict] = []

    def append(self, record: dict) -> None:
        self._records.append(record)

    def read(self) -> list[dict]:
        return list(self._records)
