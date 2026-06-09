from orcaverify.judges.base import PromptJudge


class Canned(PromptJudge):
    def __init__(self, text):
        self._text = text

    def _complete(self, prompt):
        return self._text


def test_score_parses_float_and_reason():
    s = Canned("0.9 clear and well-sourced").score("out", "be clear")
    assert s.value == 0.9 and "clear" in s.reason


def test_score_parses_bare_one():
    assert Canned("1.0").score("out", "crit").value == 1.0


def test_score_defaults_to_zero_when_unparseable():
    assert Canned("no idea").score("out", "crit").value == 0.0


def test_contradicts_yes_is_unsupported():
    v = Canned("YES: the dates conflict").contradicts("claim", ["src"])
    assert v.supported is False and "dates" in v.reason


def test_contradicts_no_is_supported():
    assert Canned("NO").contradicts("claim", ["src"]).supported is True
