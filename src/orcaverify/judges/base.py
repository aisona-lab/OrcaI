from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Verdict:
    supported: bool
    reason: str | None = None


@dataclass
class Score:
    value: float  # 0.0 - 1.0
    reason: str | None = None


class Judge(ABC):
    """Used by Grounded (claim-vs-source entailment) and by repair (rewrite)."""

    @abstractmethod
    def entails(self, claim: str, sources: list[str]) -> Verdict: ...

    @abstractmethod
    def rewrite(self, output: str, failures: list[str]) -> str: ...


_ENTAILS_PROMPT = (
    "You are a strict fact-checker. Decide if the CLAIM is fully supported by the SOURCES.\n"
    "Answer 'YES' if supported, or 'NO: <short reason>' if not.\n\n"
    "SOURCES:\n{sources}\n\nCLAIM:\n{claim}\n\nAnswer:"
)
_REWRITE_PROMPT = (
    "Rewrite the OUTPUT so it fixes every issue listed in FAILURES. "
    "Keep it faithful and concise. Return only the rewritten text.\n\n"
    "FAILURES:\n{failures}\n\nOUTPUT:\n{output}\n\nRewritten:"
)
_SCORE_PROMPT = (
    "Rate from 0.0 to 1.0 how well the OUTPUT satisfies the CRITERIA.\n"
    "Reply with just the number, then optionally a short reason.\n\n"
    "CRITERIA:\n{criteria}\n\nOUTPUT:\n{output}\n\nScore:"
)
_CONTRADICT_PROMPT = (
    "Does the CLAIM contradict the SOURCES? "
    "Answer 'YES: <reason>' if it contradicts them, or 'NO' otherwise.\n\n"
    "SOURCES:\n{sources}\n\nCLAIM:\n{claim}\n\nAnswer:"
)
_FLOAT = re.compile(r"(1(?:\.0+)?|0?\.\d+|0(?:\.0+)?)")


class PromptJudge(Judge):
    """A Judge backed by a text-completion model. Subclasses implement `_complete`."""

    @abstractmethod
    def _complete(self, prompt: str) -> str: ...

    def entails(self, claim: str, sources: list[str]) -> Verdict:
        sources_text = "\n".join(f"- {s}" for s in sources) or "(no sources provided)"
        answer = self._complete(_ENTAILS_PROMPT.format(sources=sources_text, claim=claim)).strip()
        if answer.upper().startswith("YES"):
            return Verdict(supported=True)
        reason = answer.split(":", 1)[1].strip() if ":" in answer else answer
        return Verdict(supported=False, reason=reason or "unsupported")

    def rewrite(self, output: str, failures: list[str]) -> str:
        failures_text = "\n".join(f"- {f}" for f in failures) or "(none)"
        return self._complete(_REWRITE_PROMPT.format(failures=failures_text, output=output)).strip()

    def score(self, output: str, criteria: str) -> Score:
        answer = self._complete(_SCORE_PROMPT.format(criteria=criteria, output=output)).strip()
        m = _FLOAT.match(answer)
        value = float(m.group(1)) if m else 0.0
        reason = answer[m.end() :].strip(" :-.") if m else answer
        return Score(value=value, reason=reason or None)

    def contradicts(self, claim: str, sources: list[str]) -> Verdict:
        """Returns supported=True when the claim is consistent (no contradiction)."""
        sources_text = "\n".join(f"- {s}" for s in sources) or "(no sources provided)"
        answer = self._complete(
            _CONTRADICT_PROMPT.format(sources=sources_text, claim=claim)
        ).strip()
        if answer.upper().startswith("YES"):
            reason = answer.split(":", 1)[1].strip() if ":" in answer else answer
            return Verdict(supported=False, reason=reason or "contradicts sources")
        return Verdict(supported=True)
