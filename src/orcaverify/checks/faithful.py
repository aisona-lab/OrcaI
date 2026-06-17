from __future__ import annotations

from orcaverify.checks._text import claims, failing, resolve_sources
from orcaverify.checks.base import Check, CheckResult


class Faithful(Check):
    """No claim in the output may contradict the sources.

    Complements Grounded: Grounded requires positive support for every claim,
    Faithful only forbids direct contradiction (a claim unrelated to any source is
    faithful but not grounded). Requires a judge that supports `contradicts`.
    """

    name = "faithful"

    def __init__(self, sources=None, judge=None, extract=None):
        self.sources = sources
        self.judge = judge
        self.extract = extract

    def check(self, output, context=None) -> CheckResult:
        if self.judge is None:
            raise ValueError("Faithful requires a judge (got None)")
        if not hasattr(self.judge, "contradicts"):
            raise ValueError("Faithful requires a judge that supports contradicts()")
        sources = resolve_sources(self.sources, context)
        text = self.extract(output) if self.extract else output
        contradicting = failing(
            claims(text), lambda c: not self.judge.contradicts(c, sources).supported
        )
        if contradicting:
            return CheckResult(
                ok=False,
                reason="contradicting claims: " + " | ".join(contradicting),
                meta={"contradicting": contradicting},
            )
        return CheckResult(ok=True)
