import pytest

from orcaverify.judges.base import Judge, Verdict


class FakeJudge(Judge):
    """Offline test double: a claim is supported if it appears in any source."""

    def __init__(self, supported=True):
        self._supported = supported
        self.rewrites = []

    def entails(self, claim, sources):
        ok = (
            any(claim.lower().rstrip(".") in s.lower() for s in sources)
            if self._supported
            else False
        )
        return Verdict(supported=ok, reason=None if ok else f"unsupported: {claim}")

    def rewrite(self, output, failures):
        self.rewrites.append(failures)
        return f"{output} [repaired]"


@pytest.fixture
def fake_judge():
    return FakeJudge()
