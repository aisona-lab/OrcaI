from __future__ import annotations

from orcaverify.checks.base import Check, CheckResult


class Rubric(Check):
    """Score the output against named criteria via an LLM judge; pass if it clears
    `threshold` (0.0-1.0).

    `criteria` may be a string, a list of strings, or a {name: description} dict.
    Requires a judge that supports `score(output, criteria) -> Score`.
    `extract` pulls the prose to score from a structured output.
    """

    name = "rubric"

    def __init__(self, criteria, judge=None, threshold: float = 0.7, extract=None):
        self.criteria = criteria
        self.judge = judge
        self.threshold = threshold
        self.extract = extract

    def _criteria_text(self) -> str:
        c = self.criteria
        if isinstance(c, dict):
            return "\n".join(f"- {k}: {v}" for k, v in c.items())
        if isinstance(c, (list, tuple)):
            return "\n".join(f"- {x}" for x in c)
        return str(c)

    def check(self, output, context=None) -> CheckResult:
        if self.judge is None:
            raise ValueError("Rubric requires a judge (got None)")
        if not hasattr(self.judge, "score"):
            raise ValueError("Rubric requires a judge that supports score()")
        text = self.extract(output) if self.extract else output
        score = self.judge.score(text, self._criteria_text())
        meta = {"score": score.value, "threshold": self.threshold}
        if score.value >= self.threshold:
            return CheckResult(ok=True, meta=meta)
        reason = f"score {score.value:.2f} < {self.threshold:.2f}"
        if score.reason:
            reason += f": {score.reason}"
        return CheckResult(ok=False, reason=reason, meta=meta)
