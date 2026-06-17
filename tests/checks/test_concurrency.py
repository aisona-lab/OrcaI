import time

from orcaverify.checks.faithful import Faithful
from orcaverify.checks.grounded import Grounded
from orcaverify.judges.base import Verdict


class SlowJudge:
    """Each round-trip costs 50ms — serial would be N*50ms, parallel ~50ms."""

    def entails(self, claim, sources):
        time.sleep(0.05)
        return Verdict(supported=True)

    def contradicts(self, claim, sources):
        time.sleep(0.05)
        return Verdict(supported=True)


def test_grounded_checks_claims_concurrently():
    text = " ".join(f"Claim number {i} stands." for i in range(8))  # 8 claims
    start = time.perf_counter()
    assert Grounded(sources=["x"], judge=SlowJudge()).check(text).ok
    elapsed = time.perf_counter() - start
    # Serial would be ~0.40s; concurrent stays well under half that.
    assert elapsed < 0.2, f"claims ran serially ({elapsed:.2f}s)"


def test_faithful_checks_claims_concurrently():
    text = " ".join(f"Claim number {i} stands." for i in range(8))  # 8 claims
    start = time.perf_counter()
    assert Faithful(sources=["x"], judge=SlowJudge()).check(text).ok
    elapsed = time.perf_counter() - start
    # Serial would be ~0.40s; concurrent stays well under half that.
    assert elapsed < 0.2, f"claims ran serially ({elapsed:.2f}s)"
