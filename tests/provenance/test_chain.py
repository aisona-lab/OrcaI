from orcaverify.provenance.chain import GENESIS, content_hash, verify_records
from orcaverify.provenance.record import ProvenanceRecord


def _build(payloads):
    records, prev = [], GENESIS
    for i, p in enumerate(payloads):
        rec = ProvenanceRecord.create(i, prev, p, timestamp=f"2026-01-01T00:00:0{i}+00:00")
        records.append(rec.to_dict())
        prev = rec.content_hash
    return records


def test_content_hash_deterministic():
    a = content_hash(0, "t", GENESIS, {"x": 1})
    b = content_hash(0, "t", GENESIS, {"x": 1})
    assert a == b


def test_content_hash_changes_with_payload():
    a = content_hash(0, "t", GENESIS, {"x": 1})
    b = content_hash(0, "t", GENESIS, {"x": 2})
    assert a != b


def test_valid_chain_verifies():
    assert verify_records(_build([{"a": 1}, {"b": 2}, {"c": 3}])).ok


def test_tampered_payload_breaks_chain():
    records = _build([{"a": 1}, {"b": 2}, {"c": 3}])
    records[1]["payload"] = {"b": 999}  # edit after the fact
    result = verify_records(records)
    assert result.ok is False and result.broken_at == 1 and "tampered" in result.reason


def test_deleted_record_breaks_chain():
    records = _build([{"a": 1}, {"b": 2}, {"c": 3}])
    del records[1]  # remove the middle record
    result = verify_records(records)
    assert result.ok is False and result.broken_at == 1
