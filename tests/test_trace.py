import json

from orcaverify.checks.base import CheckResult
from orcaverify.trace import Attempt, FileSink, VerifyResult


def test_result_to_dict_is_json_serializable():
    r = VerifyResult(
        ok=True,
        value={"a": 1},
        failures=[],
        attempts=[Attempt(n=1, results=[CheckResult(ok=True)], action="passed")],
        decision="passed",
    )
    dumped = json.dumps(r.to_dict())
    assert json.loads(dumped)["decision"] == "passed"


def test_to_dict_handles_unserializable_value():
    r = VerifyResult(ok=True, value=object(), failures=[], attempts=[], decision="passed")
    # should not raise; falls back to repr
    json.dumps(r.to_dict())


def test_file_sink_writes_jsonl(tmp_path):
    f = tmp_path / "trace.jsonl"
    FileSink(f).write(
        VerifyResult(
            ok=False,
            value=None,
            failures=[CheckResult(ok=False, reason="x")],
            attempts=[],
            decision="rejected",
        )
    )
    line = json.loads(f.read_text().strip())
    assert line["decision"] == "rejected" and line["failures"][0]["reason"] == "x"
