from orcaverify.checks.predicate import Predicate
from orcaverify.core import Verifier


def test_check_only_passes():
    assert Verifier([Predicate(lambda o, c: o == "good")]).check("good").ok


def test_check_only_rejects():
    r = Verifier([Predicate(lambda o, c: (o == "good", "not good"))]).check("bad")
    assert r.ok is False and r.decision == "rejected"


def test_run_retry_then_pass():
    calls = {"n": 0}

    def producer(feedback=None):
        calls["n"] += 1
        return "bad" if calls["n"] < 2 else "good"

    v = Verifier([Predicate(lambda o, c: (o == "good", "not good"))], on_fail="retry(2)")
    r = v.run(producer)
    assert r.ok and r.decision == "passed" and calls["n"] == 2


def test_run_reject_records_failures():
    v = Verifier([Predicate(lambda o, c: (False, "always fails"))], on_fail="reject")
    r = v.run(lambda feedback=None: "x")
    assert r.ok is False and r.decision == "rejected" and r.failures[0].reason == "always fails"


def test_escalate_calls_callback():
    seen = {}

    def esc(result):
        seen["called"] = True

    v = Verifier([Predicate(lambda o, c: (False, "no"))], on_fail="escalate")
    r = v.run(lambda feedback=None: "x", escalate=esc)
    assert r.decision == "escalated" and seen["called"]


def test_raising_check_is_failure_not_silent():
    def boom(o, c):
        raise RuntimeError("kaboom")

    r = Verifier([Predicate(boom)], on_fail="reject").run(lambda feedback=None: "x")
    assert r.ok is False and "kaboom" in r.failures[0].reason


def test_passes_first_try_with_reject_policy():
    r = Verifier([Predicate(lambda o, c: True)], on_fail="reject").run(lambda feedback=None: "ok")
    assert r.ok and r.decision == "passed" and r.value == "ok"
