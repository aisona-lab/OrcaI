from __future__ import annotations

from collections.abc import Callable

from orcaverify.checks.base import Check, CheckResult


class Predicate(Check):
    """Universal escape hatch: wrap any function `fn(output, context)`.

    The function returns either a bool, or a (bool, reason) tuple.
    """

    def __init__(self, fn: Callable, name: str = "predicate"):
        self.fn = fn
        self.name = name

    def check(self, output, context=None) -> CheckResult:
        result = self.fn(output, context)
        ok, reason = result if isinstance(result, tuple) else (result, None)
        return CheckResult(ok=bool(ok), reason=reason, meta={"name": self.name})
