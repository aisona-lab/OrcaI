from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from orcaverify.context import Context


@dataclass
class CheckResult:
    """Outcome of one check. `reason` is human-readable and feeds retry feedback."""

    ok: bool
    reason: str | None = None
    meta: dict = field(default_factory=dict)


class Check(ABC):
    """A single, isolated unit of verification. Implement `check`."""

    name: str = "check"

    @abstractmethod
    def check(self, output: Any, context: Context = None) -> CheckResult: ...
