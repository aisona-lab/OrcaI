from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

GENESIS = "0" * 64


def content_hash(seq: int, timestamp: str, prev_hash: str, payload: dict) -> str:
    """SHA-256 over the canonical JSON of the record's signed fields."""
    canonical = json.dumps(
        {"seq": seq, "timestamp": timestamp, "prev_hash": prev_hash, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class ChainResult:
    ok: bool
    broken_at: int | None = None
    reason: str | None = None


def verify_records(records: list[dict]) -> ChainResult:
    """Re-walk the chain and recompute every hash. Detects edits, deletes, reorders."""
    prev = GENESIS
    for index, rec in enumerate(records):
        if rec.get("seq") != index:
            return ChainResult(False, index, f"seq gap: expected {index}, got {rec.get('seq')}")
        if rec.get("prev_hash") != prev:
            return ChainResult(False, index, f"prev_hash mismatch at seq {index}")
        recomputed = content_hash(rec["seq"], rec["timestamp"], rec["prev_hash"], rec["payload"])
        if recomputed != rec.get("content_hash"):
            return ChainResult(False, index, f"content_hash mismatch (tampered) at seq {index}")
        prev = rec["content_hash"]
    return ChainResult(True)
