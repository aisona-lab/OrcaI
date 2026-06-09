from __future__ import annotations

import re

from orcaverify.checks.base import Check, CheckResult

PII = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "credit_card": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "iban": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
}
SECRETS = {
    "openai_key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
}


def _scan(text: str, patterns: dict) -> list[str]:
    # Return matched category names only; never echo the raw sensitive match.
    return sorted({name for name, rx in patterns.items() if rx.search(text)})


class NoPII(Check):
    """Fail if the output leaks personal data (email, card, SSN, IBAN)."""

    name = "no_pii"

    def check(self, output, context=None) -> CheckResult:
        found = _scan(str(output), PII)
        return CheckResult(
            ok=not found,
            reason=None if not found else f"PII detected: {', '.join(found)}",
            meta={"categories": found},
        )


class NoSecrets(Check):
    """Fail if the output leaks credentials (API keys, AWS keys)."""

    name = "no_secrets"

    def check(self, output, context=None) -> CheckResult:
        found = _scan(str(output), SECRETS)
        return CheckResult(
            ok=not found,
            reason=None if not found else f"secrets detected: {', '.join(found)}",
            meta={"categories": found},
        )
