from orcaverify.judges.base import PromptJudge, Verdict


class CannedJudge(PromptJudge):
    def __init__(self, text):
        self._text = text

    def _complete(self, prompt):
        return self._text


def test_prompt_judge_parses_yes():
    assert CannedJudge("YES").entails("c", ["c"]).supported is True


def test_prompt_judge_parses_no_with_reason():
    v = CannedJudge("NO: not in sources").entails("c", ["other"])
    assert v.supported is False and "not in sources" in v.reason


def test_prompt_judge_rewrite():
    assert CannedJudge("fixed text").rewrite("broken", ["needs fix"]) == "fixed text"


def test_verdict_defaults():
    assert Verdict(supported=True).reason is None
