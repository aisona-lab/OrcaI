from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any

from orcaverify.checks.base import Check, CheckResult
from orcaverify.context import Context
from orcaverify.policy import OnFail
from orcaverify.trace import Attempt, VerifyResult


class VerificationError(Exception):
    """Raised by @verify when an output fails to pass and raise_on_fail is set."""

    def __init__(self, result: VerifyResult):
        self.result = result
        reasons = "; ".join(f.reason or f.meta.get("name", "?") for f in result.failures)
        super().__init__(f"verification {result.decision}: {reasons}")


class Verifier:
    """Orchestrates a list of checks plus an on_fail policy.

    `check(output)` verifies an existing value. `run(producer)` produces a value,
    verifies it, and applies the on_fail fallback chain (retry/repair/escalate/reject).
    """

    def __init__(
        self, checks: list[Check], on_fail: OnFail | str = "reject", sink=None, judge=None
    ):
        self.checks = checks
        self.on_fail = OnFail.parse(on_fail)
        self.sink = sink
        self.judge = judge

    # -- verification only -------------------------------------------------
    def _run_checks(self, output, context) -> list[CheckResult]:
        results = []
        for c in self.checks:
            try:
                results.append(c.check(output, context))
            except ValueError:
                raise  # misconfiguration (e.g. Grounded without a judge) must surface
            except Exception as e:  # a raising check is a failure, never silent
                results.append(CheckResult(ok=False, reason=f"{c.name} raised: {e}"))
        return results

    def check(self, output: Any, context: Context = None) -> VerifyResult:
        results = self._run_checks(output, context)
        ok = all(r.ok for r in results)
        return self._finish(
            ok,
            output,
            results,
            [Attempt(1, results, "passed" if ok else "checked")],
            "passed" if ok else "rejected",
        )

    # -- produce + verify + policy ----------------------------------------
    def _call(self, producer: Callable, feedback):
        if "feedback" in inspect.signature(producer).parameters:
            return producer(feedback=feedback)
        return producer()

    def run(self, producer: Callable, context: Context = None, escalate=None) -> VerifyResult:
        attempts: list[Attempt] = []

        output = self._call(producer, None)
        results = self._run_checks(output, context)
        if all(r.ok for r in results):
            attempts.append(Attempt(1, results, "passed"))
            return self._finish(True, output, results, attempts, "passed")
        attempts.append(Attempt(1, results, "checked"))

        for name, n in self.on_fail.steps:
            if name == "retry":
                for _ in range(n or 1):
                    feedback = "; ".join(r.reason for r in results if not r.ok and r.reason)
                    output = self._call(producer, feedback)
                    results = self._run_checks(output, context)
                    if all(r.ok for r in results):
                        attempts.append(Attempt(len(attempts) + 1, results, "passed"))
                        return self._finish(True, output, results, attempts, "passed")
                    attempts.append(Attempt(len(attempts) + 1, results, "retry"))

            elif name == "repair":
                if self.judge is None:
                    raise ValueError("on_fail 'repair' requires a judge")
                output = self.judge.rewrite(output, [r.reason for r in results if not r.ok])
                results = self._run_checks(output, context)
                if all(r.ok for r in results):
                    attempts.append(Attempt(len(attempts) + 1, results, "repaired"))
                    return self._finish(True, output, results, attempts, "repaired")
                attempts.append(Attempt(len(attempts) + 1, results, "repair-failed"))

            elif name == "escalate":
                res = self._finish(False, None, results, attempts, "escalated")
                if escalate:
                    escalate(res)
                return res

            elif name == "reject":
                return self._finish(False, None, results, attempts, "rejected")

        return self._finish(False, None, results, attempts, "rejected")

    def _finish(self, ok, output, results, attempts, decision) -> VerifyResult:
        res = VerifyResult(
            ok=ok,
            value=output if ok else None,
            failures=[r for r in results if not r.ok],
            attempts=attempts,
            decision=decision,
        )
        if self.sink:
            self.sink.write(res)
        return res


def verify(
    *checks: Check,
    on_fail: OnFail | str = "reject",
    context=None,
    sink=None,
    judge=None,
    raise_on_fail: bool = True,
    escalate=None,
):
    """Decorator: the wrapped function proposes, Orca verifies, you decide.

    On pass returns the value. On failure raises VerificationError (default) or,
    with raise_on_fail=False, returns the VerifyResult. `context` may be a static
    value or a callable receiving the wrapped function's arguments.
    """
    verifier = Verifier(list(checks), on_fail=on_fail, sink=sink, judge=judge)

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            ctx = context(*args, **kwargs) if callable(context) else context

            def producer(feedback=None):
                return fn(*args, **kwargs)

            res = verifier.run(producer, context=ctx, escalate=escalate)
            if res.ok:
                return res.value
            if raise_on_fail:
                raise VerificationError(res)
            return res

        return wrapper

    return deco
