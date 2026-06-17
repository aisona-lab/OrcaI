import io
import json

import pytest

from orcaverify import Provenance
from orcaverify.cli import main
from orcaverify.judges.base import Verdict


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


class _FakeJudge:
    """Offline double: claim supported iff its text appears in a source."""

    def entails(self, claim, sources):
        ok = any(claim.lower().rstrip(".") in s.lower() for s in sources)
        return Verdict(supported=ok, reason=None if ok else f"unsupported: {claim}")


def test_verify_grounded_with_sources(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("orcaverify.cli.judge_from_env", lambda: _FakeJudge())
    cfg = _write(tmp_path, "c.json", json.dumps({"checks": ["grounded"]}))
    out = _write(tmp_path, "o.txt", "The sky is blue")
    src = _write(tmp_path, "s.txt", "The sky is blue and vast")
    assert main(["verify", out, "-c", cfg, "--source", src]) == 0


def test_verify_judge_required_but_missing(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("orcaverify.cli.judge_from_env", lambda: None)
    cfg = _write(tmp_path, "c.json", json.dumps({"checks": ["grounded"]}))
    out = _write(tmp_path, "o.txt", "anything")
    assert main(["verify", out, "-c", cfg, "--source", out]) == 2
    assert "requires a judge" in capsys.readouterr().err


def test_verify_bad_json_config(tmp_path, capsys):
    cfg = _write(tmp_path, "c.json", "{not valid json")
    out = _write(tmp_path, "o.txt", "x")
    assert main(["verify", out, "-c", cfg]) == 2
    assert "invalid JSON config" in capsys.readouterr().err


def test_verify_missing_config_file(tmp_path, capsys):
    out = _write(tmp_path, "o.txt", "x")
    assert main(["verify", out, "-c", str(tmp_path / "nope.json")]) == 2
    assert "file not found" in capsys.readouterr().err


def test_verify_yaml_config(tmp_path, capsys):
    pytest.importorskip("yaml")
    cfg = _write(tmp_path, "c.yaml", "checks:\n  - no_pii\non_fail: reject\n")
    out = _write(tmp_path, "o.txt", "clean")
    assert main(["verify", out, "-c", cfg]) == 0


def _ledger_with_two(tmp_path):
    led = tmp_path / "audit.jsonl"
    prov = Provenance(str(led))
    prov.record({"event": "x"})
    prov.record({"event": "y"})
    return led


def test_audit_verify_intact(tmp_path, capsys):
    led = _ledger_with_two(tmp_path)
    assert main(["audit", "verify", str(led)]) == 0
    assert "intact" in capsys.readouterr().out


def test_audit_verify_tampered(tmp_path, capsys):
    led = _ledger_with_two(tmp_path)
    lines = led.read_text().splitlines()
    rec = json.loads(lines[0])
    rec["payload"] = {"event": "TAMPERED"}
    lines[0] = json.dumps(rec)
    led.write_text("\n".join(lines) + "\n")
    assert main(["audit", "verify", str(led)]) == 1
    assert "broken" in capsys.readouterr().out


def test_audit_export_to_file(tmp_path):
    led = _ledger_with_two(tmp_path)
    out = tmp_path / "bundle.json"
    assert main(["audit", "export", str(led), "-o", str(out)]) == 0
    bundle = json.loads(out.read_text())
    assert bundle["count"] == 2 and bundle["verified"] is True


def test_audit_export_to_stdout(tmp_path, capsys):
    led = _ledger_with_two(tmp_path)
    assert main(["audit", "export", str(led)]) == 0
    bundle = json.loads(capsys.readouterr().out)
    assert bundle["count"] == 2
