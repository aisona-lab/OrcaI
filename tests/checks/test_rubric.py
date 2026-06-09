import pytest

from orcaverify.checks.rubric import Rubric
from orcaverify.judges.base import Score


class FakeScorer:
    def __init__(self, value, reason="because"):
        self._score = Score(value=value, reason=reason)

    def score(self, output, criteria):
        return self._score


def test_rubric_passes_above_threshold():
    assert Rubric("be concise", judge=FakeScorer(0.8), threshold=0.7).check("x").ok


def test_rubric_fails_below_threshold_with_score_in_reason():
    r = Rubric("be concise", judge=FakeScorer(0.4), threshold=0.7).check("x")
    assert r.ok is False and "0.40" in r.reason and r.meta["score"] == 0.4


def test_rubric_accepts_dict_criteria():
    check = Rubric({"clarity": "is it clear?"}, judge=FakeScorer(0.9))
    assert "clarity" in check._criteria_text() and check.check("x").ok


def test_rubric_requires_judge():
    with pytest.raises(ValueError):
        Rubric("crit").check("x")


def test_rubric_requires_scoring_judge():
    class NoScore:
        pass

    with pytest.raises(ValueError):
        Rubric("crit", judge=NoScore()).check("x")
