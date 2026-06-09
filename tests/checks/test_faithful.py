import pytest

from orcaverify.checks.faithful import Faithful
from orcaverify.judges.base import Verdict


class FakeContradictJudge:
    """Contradiction iff the claim contains the word 'not'."""

    def contradicts(self, claim, sources):
        if "not" in claim.lower().split():
            return Verdict(supported=False, reason=f"contradiction: {claim}")
        return Verdict(supported=True)


def test_faithful_passes_when_consistent():
    assert Faithful(sources=["sky is blue"], judge=FakeContradictJudge()).check("Sky is blue.").ok


def test_faithful_fails_on_contradiction():
    r = Faithful(sources=["sky is blue"], judge=FakeContradictJudge()).check("Sky is not blue.")
    assert r.ok is False and "not blue" in r.reason


def test_faithful_extracts_field():
    check = Faithful(sources=["s"], judge=FakeContradictJudge(), extract=lambda o: o["finding"])
    assert check.check({"finding": "all consistent here"}).ok


def test_faithful_requires_judge():
    with pytest.raises(ValueError):
        Faithful(sources=["s"]).check("x")


def test_faithful_requires_contradicts_judge():
    class NoMethod:
        pass

    with pytest.raises(ValueError):
        Faithful(sources=["s"], judge=NoMethod()).check("x")
