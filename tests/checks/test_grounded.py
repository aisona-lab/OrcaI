import pytest

from orcaverify.checks.grounded import Grounded
from tests.judges.conftest import FakeJudge


def test_grounded_passes_when_supported():
    r = Grounded(sources=["The sky is blue.", "Water is wet."], judge=FakeJudge()).check(
        "The sky is blue."
    )
    assert r.ok


def test_grounded_fails_unsupported_and_lists_claim():
    r = Grounded(sources=["Water is wet."], judge=FakeJudge()).check("The moon is cheese.")
    assert r.ok is False and "moon" in r.reason


def test_grounded_reads_sources_from_context():
    r = Grounded(judge=FakeJudge()).check("Water is wet.", context=["Water is wet."])
    assert r.ok


def test_grounded_extracts_field_from_structured_output():
    check = Grounded(
        sources=["The sky is blue."], judge=FakeJudge(), extract=lambda o: o["finding"]
    )
    assert check.check({"title": "t", "finding": "The sky is blue."}).ok


def test_grounded_requires_judge():
    with pytest.raises(ValueError):
        Grounded(sources=["x"]).check("x")
