from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from orcaverify.provenance.chain import content_hash


@dataclass
class ProvenanceRecord:
    seq: int
    timestamp: str
    prev_hash: str
    content_hash: str
    payload: dict

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def create(
        cls, seq: int, prev_hash: str, payload: dict, timestamp: str | None = None
    ) -> ProvenanceRecord:
        ts = timestamp or datetime.now(UTC).isoformat()
        ch = content_hash(seq, ts, prev_hash, payload)
        return cls(seq=seq, timestamp=ts, prev_hash=prev_hash, content_hash=ch, payload=payload)
