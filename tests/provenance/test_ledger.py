import json

from orcaverify.checks.predicate import Predicate
from orcaverify.core import Verifier
from orcaverify.provenance import Provenance
from orcaverify.provenance.store import FileStore, InMemoryStore


def test_record_and_verify_ok():
    prov = Provenance(InMemoryStore())
    prov.record({"event": "login", "user": "a"})
    prov.record({"event": "access", "resource": "case-1"})
    assert prov.verify().ok and len(prov.records()) == 2


def test_records_are_chained():
    prov = Provenance(InMemoryStore())
    r0 = prov.record({"a": 1})
    r1 = prov.record({"b": 2})
    assert r1.prev_hash == r0.content_hash and r1.seq == 1


def test_write_accepts_verifyresult_via_sink():
    store = InMemoryStore()
    prov = Provenance(store)
    v = Verifier([Predicate(lambda o, c: True)], sink=prov)
    v.run(lambda feedback=None: "good")
    records = prov.records()
    assert len(records) == 1 and records[0]["payload"]["decision"] == "passed"
    assert prov.verify().ok


def test_tampering_file_is_detected(tmp_path):
    path = tmp_path / "audit.jsonl"
    prov = Provenance(FileStore(path))
    prov.record({"amount": 100})
    prov.record({"amount": 200})

    lines = path.read_text().splitlines()
    rec = json.loads(lines[0])
    rec["payload"]["amount"] = 1  # tamper with the persisted file
    lines[0] = json.dumps(rec)
    path.write_text("\n".join(lines) + "\n")

    assert prov.verify().ok is False


def test_export_writes_verified_bundle(tmp_path):
    prov = Provenance(InMemoryStore())
    prov.record({"a": 1})
    bundle = prov.export(tmp_path / "export.json")
    assert bundle["verified"] is True and bundle["count"] == 1
    on_disk = json.loads((tmp_path / "export.json").read_text())
    assert on_disk["verified"] is True
