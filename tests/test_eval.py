from eval.run import evaluate, prf

from orcaverify.judges.base import Verdict


def test_prf_basic():
    # tp=3, fp=1, fn=2 -> precision 0.75, recall 0.60, f1 0.67
    m = prf(3, 1, 2)
    assert round(m["precision"], 2) == 0.75
    assert round(m["recall"], 2) == 0.60
    assert round(m["f1"], 2) == 0.67


def test_prf_zero_safe():
    assert prf(0, 0, 0) == {"precision": 0.0, "recall": 0.0, "f1": 0.0}


class _AlwaysSupported:
    """Never flags anything -> every bad row becomes a miss (fn)."""

    def entails(self, claim, sources):
        return Verdict(supported=True)

    def contradicts(self, claim, sources):
        return Verdict(supported=True)


def test_evaluate_counts_confusion():
    rows = [
        {"id": "good", "check": "grounded", "text": "x", "sources": ["x"], "expect_ok": True},
        {"id": "bad", "check": "grounded", "text": "y", "sources": ["z"], "expect_ok": False},
    ]
    buckets, misses, false_alarms = evaluate(rows, _AlwaysSupported())
    assert buckets["grounded"]["tn"] == 1  # good output passed
    assert buckets["grounded"]["fn"] == 1  # bad output slipped through
    assert misses == ["bad"]
    assert false_alarms == []
