from __future__ import annotations

import re

from orcaverify.checks.base import Check, CheckResult


def _claims(text) -> list[str]:
    # v1 claim extraction: one claim per sentence.
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", str(text).strip()) if s.strip()]


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

    def _resolve(self, context) -> list[str]:
        src = self.sources if self.sources is not None else context
        if callable(src):
            src = src()
        return list(src) if src else []

    def check(self, output, context=None) -> CheckResult:
        if self.judge is None:
            raise ValueError("Grounded requires a judge (got None)")
        sources = self._resolve(context)
        text = self.extract(output) if self.extract else output
        unsupported = [
            claim for claim in _claims(text) if not self.judge.entails(claim, sources).supported
        ]
        if unsupported:
            return CheckResult(
                ok=False,
                reason="unsupported claims: " + " | ".join(unsupported),
                meta={"unsupported": unsupported},
            )
        return CheckResult(ok=True)
