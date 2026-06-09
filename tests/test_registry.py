import pytest

from orcaverify.checks.base import Check, CheckResult
from orcaverify.checks.nopii import NoPII
from orcaverify.registry import (
    available,
    build_check,
    from_config,
    get,
    load_plugins,
    register,
)


def test_builtins_are_registered():
    names = available()
    for n in ["schema", "grounded", "faithful", "rubric", "no_pii", "no_secrets"]:
        assert n in names


def test_get_unknown_raises_helpful():
    with pytest.raises(KeyError) as e:
        get("does_not_exist")
    assert "Available" in str(e.value)


def test_register_via_decorator():
    @register("ok_check")
    class OkCheck(Check):
        name = "ok_check"

        def check(self, output, context=None):
            return CheckResult(ok=True)

    assert get("ok_check") is OkCheck


def test_build_check_from_string():
    assert isinstance(build_check("no_pii"), NoPII)


def test_build_check_from_dict_shorthand_with_args():
    class FakeScorer:
        def score(self, output, criteria):
            from orcaverify.judges.base import Score

            return Score(value=1.0)

    check = build_check({"rubric": {"criteria": "be clear", "threshold": 0.5}}, judge=FakeScorer())
    assert check.threshold == 0.5 and check.check("x").ok


def test_build_check_name_args_form():
    check = build_check({"name": "no_secrets", "args": {}})
    assert check.name == "no_secrets"


def test_bad_spec_raises():
    with pytest.raises(ValueError):
        build_check({"rubric": "not-a-dict"})


def test_from_config_builds_running_verifier():
    cfg = {"checks": ["no_pii", "no_secrets"], "on_fail": "reject"}
    verifier = from_config(cfg)
    assert verifier.run(lambda feedback=None: "clean text").ok


def test_from_config_injects_judge():
    class FakeJudge:
        def entails(self, claim, sources):
            from orcaverify.judges.base import Verdict

            return Verdict(supported=True)

    verifier = from_config({"checks": ["grounded"]}, judge=FakeJudge())
    # grounded received the judge -> no ValueError, passes a supported claim
    assert verifier.check("anything", context=["anything"]).ok


def test_load_plugins_registers_entry_points():
    class ToxCheck(Check):
        name = "toxicity"

        def check(self, output, context=None):
            return CheckResult(ok="bad" not in str(output))

    class FakeEP:
        name = "toxicity"

        def load(self):
            return ToxCheck

    names = load_plugins(_entry_points=lambda group: [FakeEP()])
    assert "toxicity" in names and get("toxicity") is ToxCheck
