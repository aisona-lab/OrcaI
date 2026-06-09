from orcaverify.provenance.store import FileStore, InMemoryStore


def test_file_store_roundtrip(tmp_path):
    store = FileStore(tmp_path / "audit.jsonl")
    store.append({"seq": 0, "x": 1})
    store.append({"seq": 1, "x": 2})
    records = store.read()
    assert [r["seq"] for r in records] == [0, 1]


def test_file_store_read_empty_when_missing(tmp_path):
    assert FileStore(tmp_path / "nope.jsonl").read() == []


def test_in_memory_store():
    store = InMemoryStore()
    store.append({"seq": 0})
    assert store.read() == [{"seq": 0}]
