from __future__ import annotations

import json
from pathlib import Path

from orcaverify.provenance.chain import GENESIS, ChainResult, verify_records
from orcaverify.provenance.record import ProvenanceRecord
from orcaverify.provenance.store import FileStore, ProvenanceStore


class Provenance:
    """Tamper-evident, append-only audit trail. Drops into a Verifier as its `sink`.

    Each VerifyResult (or any payload) becomes a hash-chained record. `verify()`
    re-walks the chain to prove nothing was edited, deleted, or reordered.
    """

    def __init__(self, store: ProvenanceStore | str):
        self.store = FileStore(store) if isinstance(store, (str, Path)) else store

    def _tip(self) -> tuple[str, int]:
        records = self.store.read()
        if not records:
            return GENESIS, -1
        last = records[-1]
        return last["content_hash"], last["seq"]

    def record(self, payload: dict) -> ProvenanceRecord:
        """Log any auditable event (data access, login, decision...)."""
        prev_hash, last_seq = self._tip()
        rec = ProvenanceRecord.create(last_seq + 1, prev_hash, payload)
        self.store.append(rec.to_dict())
        return rec

    def write(self, result) -> ProvenanceRecord:
        """Sink interface: accepts a VerifyResult (or any dict-able)."""
        payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
        return self.record(payload)

    def records(self) -> list[dict]:
        return self.store.read()

    def verify(self) -> ChainResult:
        return verify_records(self.store.read())

    def export(self, path) -> dict:
        """Write the full chain plus an integrity summary for an auditor."""
        records = self.store.read()
        result = self.verify()
        bundle = {
            "verified": result.ok,
            "count": len(records),
            "broken_at": result.broken_at,
            "records": records,
        }
        Path(path).write_text(json.dumps(bundle, indent=2))
        return bundle
