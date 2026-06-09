import pytest

from orcaverify.policy import OnFail


def test_parse_reject():
    assert OnFail.parse("reject").steps == [("reject", None)]


def test_parse_chain():
    p = OnFail.parse("retry(2) -> repair -> escalate")
    assert p.steps == [("retry", 2), ("repair", None), ("escalate", None)]


def test_accepts_onfail_instance():
    assert OnFail.parse(OnFail([("reject", None)])).steps == [("reject", None)]


def test_bad_step_raises():
    with pytest.raises(ValueError):
        OnFail.parse("explode")
