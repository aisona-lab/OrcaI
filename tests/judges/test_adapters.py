from orcaverify.judges.local import LocalJudge


class FakeChat:
    def __init__(self, text):
        self._text = text

    def complete(self, prompt):
        return self._text


def test_local_entails_parses_yes():
    assert LocalJudge(client=FakeChat("YES")).entails("claim", ["claim"]).supported is True


def test_local_entails_parses_no():
    v = LocalJudge(client=FakeChat("NO: not in sources")).entails("claim", ["other"])
    assert v.supported is False and "not in sources" in v.reason


def test_local_rewrite():
    assert LocalJudge(client=FakeChat("clean")).rewrite("dirty", ["fix"]) == "clean"
