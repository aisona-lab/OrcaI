from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from orcaverify.checks.base import CheckResult

Decision = Literal["passed", "repaired", "escalated", "rejected"]


@dataclass
class Attempt:
    n: int
    results: list[CheckResult]
    action: str


@dataclass
class VerifyResult:
    ok: bool
    value: Any
    failures: list[CheckResult]
    attempts: list[Attempt]
    decision: Decision

    def to_dict(self) -> dict:
        def safe(v):
            try:
                json.dumps(v)
                return v
            except TypeError:
                return repr(v)

        return {
            "ok": self.ok,
            "value": safe(self.value),
            "failures": [asdict(f) for f in self.failures],
            "attempts": [
                {"n": a.n, "action": a.action, "results": [asdict(r) for r in a.results]}
                for a in self.attempts
            ],
            "decision": self.decision,
        }


class FileSink:
    """Append each VerifyResult as one JSON line."""

    def __init__(self, path):
        self.path = Path(path)

    def write(self, result: VerifyResult) -> None:
        with self.path.open("a") as fh:
            fh.write(json.dumps(result.to_dict()) + "\n")


class LoggerSink:
    """Emit each VerifyResult through a stdlib logger."""

    def __init__(self, logger):
        self.logger = logger

    def write(self, result: VerifyResult) -> None:
        self.logger.info("orca.verify", extra={"orca": result.to_dict()})
