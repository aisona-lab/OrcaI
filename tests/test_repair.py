import pytest

from orcaverify.checks.predicate import Predicate
from orcaverify.core import Verifier
from tests.judges.conftest import FakeJudge


def test_repair_runs_judge_and_reverifies():
    j = FakeJudge()
    v = Verifier(
        [Predicate(lambda o, c: ("[repaired]" in o, "needs repair"))],
        on_fail="repair",
        judge=j,
    )
    r = v.run(lambda feedback=None: "raw output")
    assert r.ok and r.decision == "repaired" and j.rewrites


def test_repair_without_judge_raises():
    v = Verifier([Predicate(lambda o, c: (False, "x"))], on_fail="repair")
    with pytest.raises(ValueError):
        v.run(lambda feedback=None: "x")
