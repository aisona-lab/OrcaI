from __future__ import annotations

from orcaverify.checks._text import claims, failing, resolve_sources
from orcaverify.checks.base import Check, CheckResult


class Grounded(Check):
    """Every claim in the output must be supported by a retrieved source.

    `sources` may be a list, a zero-arg callable returning a list, or None
    (then sources are read from the verification `context`). Requires a `judge`.
    `extract` pulls the prose to ground from a structured output (e.g. a dict or
    Pydantic model); by default the whole output is grounded as text.
    """

    name = "grounded"

    def __init__(self, sources=None, judge=None, extract=None):
        self.sources = sources
        self.judge = judge
        self.extract = extract

    def check(self, output, context=None) -> CheckResult:
        if self.judge is None:
            raise ValueError("Grounded requires a judge (got None)")
        sources = resolve_sources(self.sources, context)
        text = self.extract(output) if self.extract else output
        unsupported = failing(claims(text), lambda c: not self.judge.entails(c, sources).supported)
        if unsupported:
            return CheckResult(
                ok=False,
                reason="unsupported claims: " + " | ".join(unsupported),
                meta={"unsupported": unsupported},
            )
        return CheckResult(ok=True)
