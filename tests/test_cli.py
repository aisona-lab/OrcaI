import io
import json

from orcaverify.cli import main


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content)
    return str(p)


def test_checks_lists_names(capsys):
    assert main(["checks"]) == 0
    out = capsys.readouterr().out
    assert "no_pii" in out  # offline check, unmarked
    assert "grounded *" in out  # judge-requiring check, marked


def test_verify_offline_passes(tmp_path, capsys):
    cfg = _write(tmp_path, "c.json", json.dumps({"checks": ["no_pii"]}))
    out = _write(tmp_path, "o.txt", "the sky is blue")
    assert main(["verify", out, "-c", cfg]) == 0
    assert "✓ no_pii" in capsys.readouterr().out


def test_verify_offline_fails(tmp_path, capsys):
    cfg = _write(tmp_path, "c.json", json.dumps({"checks": ["no_pii"]}))
    out = _write(tmp_path, "o.txt", "email me at john@example.com")
    assert main(["verify", out, "-c", cfg]) == 1
    captured = capsys.readouterr().out
    assert "✗ no_pii" in captured
    assert "PII detected" in captured


def test_verify_reads_stdin(tmp_path, capsys, monkeypatch):
    cfg = _write(tmp_path, "c.json", json.dumps({"checks": ["no_pii"]}))
    monkeypatch.setattr("sys.stdin", io.StringIO("clean text"))
    assert main(["verify", "-", "-c", cfg]) == 0


def test_verify_json_output(tmp_path, capsys):
    cfg = _write(tmp_path, "c.json", json.dumps({"checks": ["no_pii"]}))
    out = _write(tmp_path, "o.txt", "clean text")
    assert main(["verify", out, "-c", cfg, "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
    assert data["decision"] == "passed"
