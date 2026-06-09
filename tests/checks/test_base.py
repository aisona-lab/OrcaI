from orcaverify.checks.base import Check, CheckResult


class AlwaysOk(Check):
    name = "always_ok"

    def check(self, output, context=None):
        return CheckResult(ok=True)


def test_check_returns_result():
    assert AlwaysOk().check("x").ok is True


def test_checkresult_carries_reason():
    r = CheckResult(ok=False, reason="bad")
    assert r.ok is False and r.reason == "bad"
