"""A tiny offline Judge for the examples — no API key, no network.

In real use, swap this for AnthropicJudge, OpenAIJudge, or LocalJudge.
A claim is "supported" only if most of its content words appear in one source.
"""

from orcaverify.judges.base import Judge, Score, Verdict

_STOPWORDS = {"the", "a", "an", "is", "was", "of", "in", "to", "by", "and", "for", "on", "at"}


def _content_words(text: str) -> set[str]:
    return {w for w in text.lower().rstrip(".").split() if w not in _STOPWORDS}


class StubJudge(Judge):
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold

    def entails(self, claim, sources):
        claim_words = _content_words(claim)
        if not claim_words:
            return Verdict(supported=True)
        for s in sources:
            overlap = len(claim_words & _content_words(s)) / len(claim_words)
            if overlap >= self.threshold:
                return Verdict(supported=True)
        return Verdict(supported=False, reason=f"no source supports: {claim}")

    def rewrite(self, output, failures):
        return output

    def score(self, output, criteria):
        crit, out = _content_words(criteria), _content_words(output)
        value = round(len(crit & out) / len(crit), 2) if crit else 1.0
        return Score(value=value, reason="word-overlap heuristic (stub)")

    def contradicts(self, claim, sources):
        if "not" in claim.lower().split():
            return Verdict(supported=False, reason=f"negation detected (stub): {claim}")
        return Verdict(supported=True)
