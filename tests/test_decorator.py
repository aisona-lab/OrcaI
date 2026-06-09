import pytest

from orcaverify.checks.predicate import Predicate
from orcaverify.core import VerificationError, verify


def test_decorator_returns_value_on_pass():
    @verify(Predicate(lambda o, c: o == "ok"))
    def produce():
        return "ok"

    assert produce() == "ok"


def test_decorator_raises_on_reject_by_default():
    @verify(Predicate(lambda o, c: (False, "no")), on_fail="reject")
    def produce():
        return "x"

    with pytest.raises(VerificationError):
        produce()


def test_decorator_return_result_mode():
    @verify(Predicate(lambda o, c: (False, "no")), on_fail="reject", raise_on_fail=False)
    def produce():
        return "x"

    res = produce()
    assert res.ok is False


def test_decorator_passes_context_callable():
    @verify(
        Predicate(lambda o, c: (c == "CTX", "bad ctx")),
        context=lambda *a, **k: "CTX",
    )
    def produce():
        return "anything"

    assert produce() == "anything"
