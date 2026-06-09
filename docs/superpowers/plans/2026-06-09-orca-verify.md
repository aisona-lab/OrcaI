# Orca v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A drop-in, framework-agnostic verification layer for LLM/agent outputs in Python: declare checks, an output ships only if it passes, else retry/repair/escalate/reject.

**Architecture:** Two concepts — `Check` (isolated verification unit) and `Verifier` (orchestrates checks + on_fail policy). `@verify` is sugar over `Verifier`. Core depends on Pydantic only; model SDKs are optional extras. Grounded/repair use a pluggable `Judge` protocol (Anthropic/OpenAI/Local).

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, ruff, GitHub Actions. Optional: anthropic, openai SDKs.

---

## File Structure

```
src/orcaverify/
├── __init__.py          # exports
├── core.py              # Verifier, VerifyResult, Attempt, @verify
├── policy.py            # OnFail parser
├── trace.py             # sinks (file JSONL / logger)
├── context.py           # Context type
├── checks/{base,schema,predicate,grounded,nopii}.py
└── judges/{base,anthropic,openai,local}.py
tests/  mirrors src
examples/{aml_investigation.py, rag_grounding.py}
```

---

### Task 0: Scaffold

**Files:** Create `pyproject.toml`, `README.md`, `LICENSE`, `.github/workflows/ci.yml`, `src/orcaverify/__init__.py`, `tests/__init__.py`.

- [ ] **Step 1:** Write `pyproject.toml` (setuptools, src layout, deps `pydantic>=2`, extras `anthropic`/`openai`/`local`/`dev`; ruff + pytest config).
- [ ] **Step 2:** Write `__init__.py` with `__version__ = "0.1.0"` and a placeholder `__all__`.
- [ ] **Step 3:** Run `pip install -e ".[dev]"`. Expected: success.
- [ ] **Step 4:** Run `pytest`. Expected: "no tests ran" (exit 5 ok).
- [ ] **Step 5:** Commit `chore: scaffold orca-verify package`.

---

### Task 1: Check base + CheckResult + Context

**Files:** Create `src/orcaverify/context.py`, `src/orcaverify/checks/base.py`, `tests/checks/test_base.py`.

- [ ] **Step 1: Failing test** — `tests/checks/test_base.py`:
```python
from orcaverify.checks.base import Check, CheckResult

class AlwaysOk(Check):
    name = "always_ok"
    def check(self, output, context): return CheckResult(ok=True)

def test_check_returns_result():
    assert AlwaysOk().check("x", None).ok is True

def test_checkresult_carries_reason():
    r = CheckResult(ok=False, reason="bad")
    assert r.ok is False and r.reason == "bad"
```
- [ ] **Step 2:** Run `pytest tests/checks/test_base.py -v`. Expected: FAIL (import error).
- [ ] **Step 3: Implement** — `context.py`:
```python
from typing import Any
Context = Any | None  # static value, or read by checks (sources, etc.)
```
`checks/base.py`:
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from orcaverify.context import Context

@dataclass
class CheckResult:
    ok: bool
    reason: str | None = None
    meta: dict = field(default_factory=dict)

class Check(ABC):
    name: str = "check"
    @abstractmethod
    def check(self, output: Any, context: Context) -> CheckResult: ...
```
- [ ] **Step 4:** Run test. Expected: PASS.
- [ ] **Step 5:** Commit `feat: add Check base and CheckResult`.

---

### Task 2: Schema check

**Files:** Create `src/orcaverify/checks/schema.py`, `tests/checks/test_schema.py`.

- [ ] **Step 1: Failing test**:
```python
from pydantic import BaseModel
from orcaverify.checks.schema import Schema

class Report(BaseModel):
    title: str
    score: int

def test_schema_passes_valid():
    assert Schema(Report).check({"title": "a", "score": 1}, None).ok

def test_schema_fails_invalid_and_explains():
    r = Schema(Report).check({"title": "a"}, None)
    assert r.ok is False and "score" in r.reason
```
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement** `schema.py`:
```python
from pydantic import BaseModel, ValidationError
from orcaverify.checks.base import Check, CheckResult

class Schema(Check):
    name = "schema"
    def __init__(self, model: type[BaseModel]):
        self.model = model
    def check(self, output, context):
        try:
            self.model.model_validate(
                output if not isinstance(output, BaseModel) else output.model_dump()
            )
            return CheckResult(ok=True)
        except ValidationError as e:
            return CheckResult(ok=False, reason=str(e))
```
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: add Schema check`.

---

### Task 3: Predicate check

**Files:** Create `src/orcaverify/checks/predicate.py`, `tests/checks/test_predicate.py`.

- [ ] **Step 1: Failing test**:
```python
from orcaverify.checks.predicate import Predicate

def test_predicate_bool():
    assert Predicate(lambda o, c: len(o) > 0).check("hi", None).ok

def test_predicate_tuple_reason():
    r = Predicate(lambda o, c: (False, "empty"), name="nonempty").check("", None)
    assert r.ok is False and r.reason == "empty" and r.meta["name"] == "nonempty"
```
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement** `predicate.py`:
```python
from orcaverify.checks.base import Check, CheckResult

class Predicate(Check):
    name = "predicate"
    def __init__(self, fn, name="predicate"):
        self.fn = fn
        self.name = name
    def check(self, output, context):
        result = self.fn(output, context)
        ok, reason = result if isinstance(result, tuple) else (result, None)
        return CheckResult(ok=bool(ok), reason=reason, meta={"name": self.name})
```
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: add Predicate check`.

---

### Task 4: NoPII / NoSecrets check

**Files:** Create `src/orcaverify/checks/nopii.py`, `tests/checks/test_nopii.py`.

- [ ] **Step 1: Failing test**:
```python
from orcaverify.checks.nopii import NoPII, NoSecrets

def test_nopii_flags_email():
    r = NoPII().check("contact me at john@acme.com", None)
    assert r.ok is False and "email" in r.reason

def test_nopii_clean_passes():
    assert NoPII().check("no personal data here", None).ok

def test_nosecrets_flags_key():
    r = NoSecrets().check("key sk-ABCDEF0123456789ABCDEF0123", None)
    assert r.ok is False
```
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement** `nopii.py` (regex patterns for email, IBAN-ish, credit-card, US SSN; secrets: `sk-...`, AWS `AKIA...`, generic long tokens). Return reason naming categories found, never echo the raw match:
```python
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

def _scan(text, patterns):
    return sorted({name for name, rx in patterns.items() if rx.search(text)})

class NoPII(Check):
    name = "no_pii"
    def check(self, output, context):
        found = _scan(str(output), PII)
        return CheckResult(ok=not found,
                           reason=None if not found else f"PII detected: {', '.join(found)}",
                           meta={"categories": found})

class NoSecrets(Check):
    name = "no_secrets"
    def check(self, output, context):
        found = _scan(str(output), SECRETS)
        return CheckResult(ok=not found,
                           reason=None if not found else f"secrets detected: {', '.join(found)}",
                           meta={"categories": found})
```
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: add NoPII and NoSecrets checks`.

---

### Task 5: Judge protocol + FakeJudge

**Files:** Create `src/orcaverify/judges/base.py`, `tests/judges/conftest.py` (FakeJudge fixture), `tests/judges/test_base.py`.

- [ ] **Step 1: Failing test** — `tests/judges/test_base.py`:
```python
from orcaverify.judges.base import Judge, Verdict

class Yes(Judge):
    def entails(self, claim, sources): return Verdict(supported=True)
    def rewrite(self, output, failures): return output

def test_judge_protocol():
    v = Yes().entails("x", ["x"])
    assert v.supported is True
```
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement** `judges/base.py`:
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class Verdict:
    supported: bool
    reason: str | None = None

class Judge(ABC):
    @abstractmethod
    def entails(self, claim: str, sources: list[str]) -> Verdict: ...
    @abstractmethod
    def rewrite(self, output: str, failures: list[str]) -> str: ...
```
`tests/judges/conftest.py`:
```python
import pytest
from orcaverify.judges.base import Judge, Verdict

class FakeJudge(Judge):
    def __init__(self, supported=True):
        self._supported = supported
        self.rewrites = []
    def entails(self, claim, sources):
        ok = any(claim.lower() in s.lower() for s in sources) if self._supported else False
        return Verdict(supported=ok, reason=None if ok else f"unsupported: {claim}")
    def rewrite(self, output, failures):
        self.rewrites.append(failures)
        return f"{output} [repaired]"

@pytest.fixture
def fake_judge():
    return FakeJudge()
```
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: add Judge protocol and FakeJudge test double`.

---

### Task 6: Grounded check

**Files:** Create `src/orcaverify/checks/grounded.py`, `tests/checks/test_grounded.py`.

Claim extraction v1 = split output into sentences; each sentence is a claim. `sources` may be a list, a callable `() -> list[str]`, or `None` (then read `context`).

- [ ] **Step 1: Failing test**:
```python
from orcaverify.checks.grounded import Grounded
from tests.judges.conftest import FakeJudge

def test_grounded_passes_when_supported():
    j = FakeJudge()
    sources = ["The sky is blue.", "Water is wet."]
    r = Grounded(sources=sources, judge=j).check("The sky is blue", None)
    assert r.ok

def test_grounded_fails_unsupported_and_lists_claim():
    j = FakeJudge()
    r = Grounded(sources=["Water is wet."], judge=j).check("The moon is cheese.", None)
    assert r.ok is False and "moon" in r.reason
```
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement** `grounded.py`:
```python
import re
from orcaverify.checks.base import Check, CheckResult

def _claims(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", str(text).strip()) if s.strip()]

class Grounded(Check):
    name = "grounded"
    def __init__(self, sources=None, judge=None):
        self.sources = sources
        self.judge = judge
    def _resolve(self, context):
        src = self.sources if self.sources is not None else context
        if callable(src): src = src()
        return list(src) if src else []
    def check(self, output, context):
        if self.judge is None:
            raise ValueError("Grounded requires a judge (got None)")
        sources = self._resolve(context)
        unsupported = []
        for claim in _claims(output):
            if not self.judge.entails(claim, sources).supported:
                unsupported.append(claim)
        if unsupported:
            return CheckResult(ok=False,
                               reason="unsupported claims: " + " | ".join(unsupported),
                               meta={"unsupported": unsupported})
        return CheckResult(ok=True)
```
- [ ] **Step 4:** Run `pytest tests/checks/test_grounded.py -v`. Expected: PASS.
- [ ] **Step 5:** Commit `feat: add Grounded check (claim-vs-source via Judge)`.

---

### Task 7: OnFail policy

**Files:** Create `src/orcaverify/policy.py`, `tests/test_policy.py`.

- [ ] **Step 1: Failing test**:
```python
from orcaverify.policy import OnFail

def test_parse_reject():
    p = OnFail.parse("reject")
    assert p.steps == [("reject", None)]

def test_parse_chain():
    p = OnFail.parse("retry(2) -> repair -> escalate")
    assert p.steps == [("retry", 2), ("repair", None), ("escalate", None)]

def test_accepts_onfail_instance():
    p = OnFail.parse(OnFail([("reject", None)]))
    assert p.steps == [("reject", None)]
```
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement** `policy.py`:
```python
import re
from dataclasses import dataclass

_STEP = re.compile(r"^(retry|repair|escalate|reject)(?:\((\d+)\))?$")

@dataclass
class OnFail:
    steps: list[tuple[str, int | None]]

    @classmethod
    def parse(cls, spec):
        if isinstance(spec, OnFail):
            return spec
        steps = []
        for raw in str(spec).split("->"):
            m = _STEP.match(raw.strip())
            if not m:
                raise ValueError(f"bad on_fail step: {raw!r}")
            name, n = m.group(1), m.group(2)
            steps.append((name, int(n) if n else None))
        return cls(steps)
```
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: add OnFail policy parser`.

---

### Task 8: Trace (VerifyResult + Attempt + sinks)

**Files:** Create `src/orcaverify/trace.py`, `tests/test_trace.py`.

- [ ] **Step 1: Failing test**:
```python
import json
from orcaverify.trace import VerifyResult, Attempt, FileSink
from orcaverify.checks.base import CheckResult

def test_result_to_dict_is_json():
    r = VerifyResult(ok=True, value={"a": 1}, failures=[],
                     attempts=[Attempt(n=1, results=[CheckResult(ok=True)], action="passed")],
                     decision="passed")
    assert json.dumps(r.to_dict())["0":] or True  # serializable
    assert r.to_dict()["decision"] == "passed"

def test_file_sink_writes_jsonl(tmp_path):
    f = tmp_path / "trace.jsonl"
    sink = FileSink(f)
    sink.write(VerifyResult(ok=False, value=None, failures=[CheckResult(ok=False, reason="x")],
                            attempts=[], decision="rejected"))
    line = json.loads(f.read_text().strip())
    assert line["decision"] == "rejected"
```
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement** `trace.py`:
```python
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Literal
from orcaverify.checks.base import CheckResult

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
    decision: Literal["passed", "repaired", "escalated", "rejected"]
    def to_dict(self):
        def safe(v):
            try: json.dumps(v); return v
            except TypeError: return repr(v)
        return {
            "ok": self.ok,
            "value": safe(self.value),
            "failures": [asdict(f) for f in self.failures],
            "attempts": [{"n": a.n, "action": a.action,
                          "results": [asdict(r) for r in a.results]} for a in self.attempts],
            "decision": self.decision,
        }

class FileSink:
    def __init__(self, path): self.path = Path(path)
    def write(self, result: VerifyResult):
        with self.path.open("a") as fh:
            fh.write(json.dumps(result.to_dict()) + "\n")

class LoggerSink:
    def __init__(self, logger): self.logger = logger
    def write(self, result: VerifyResult):
        self.logger.info("orca.verify", extra={"orca": result.to_dict()})
```
- [ ] **Step 4:** Run. Expected: PASS (fix the test's serializable assertion to `json.dumps(r.to_dict())`).
- [ ] **Step 5:** Commit `feat: add VerifyResult trace and sinks`.

---

### Task 9: Verifier orchestrator (.check + .run, retry/escalate/reject)

**Files:** Create `src/orcaverify/core.py`, `tests/test_verifier.py`.

`.run(producer, context)` calls producer (a zero-arg callable), runs checks, applies policy. Retry re-invokes producer with `feedback` kwarg if it accepts one. Escalate calls `escalate` callback.

- [ ] **Step 1: Failing test**:
```python
from orcaverify.core import Verifier
from orcaverify.checks.predicate import Predicate

def test_check_only_passes():
    v = Verifier([Predicate(lambda o, c: o == "good")])
    assert v.check("good").ok

def test_run_retry_then_pass():
    attempts = {"n": 0}
    def producer(feedback=None):
        attempts["n"] += 1
        return "bad" if attempts["n"] < 2 else "good"
    v = Verifier([Predicate(lambda o, c: (o == "good", "not good"))], on_fail="retry(2)")
    r = v.run(producer)
    assert r.ok and r.decision == "passed" and attempts["n"] == 2

def test_run_reject_records_failures():
    v = Verifier([Predicate(lambda o, c: (False, "always fails"))], on_fail="reject")
    r = v.run(lambda feedback=None: "x")
    assert r.ok is False and r.decision == "rejected" and r.failures[0].reason == "always fails"

def test_escalate_calls_callback():
    seen = {}
    def esc(result): seen["called"] = True
    v = Verifier([Predicate(lambda o, c: (False, "no"))], on_fail="escalate")
    r = v.run(lambda feedback=None: "x", escalate=esc)
    assert r.decision == "escalated" and seen["called"]
```
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement** `core.py` (Verifier with `_run_checks`, retry loop with feedback, repair hook deferred to Task 10, escalate, reject). Inject feedback only if producer signature accepts `feedback`. Persist to sink if set.
```python
import inspect
from typing import Any, Callable
from orcaverify.checks.base import Check, CheckResult
from orcaverify.context import Context
from orcaverify.policy import OnFail
from orcaverify.trace import VerifyResult, Attempt

class Verifier:
    def __init__(self, checks: list[Check], on_fail="reject", sink=None, judge=None):
        self.checks = checks
        self.on_fail = OnFail.parse(on_fail)
        self.sink = sink
        self.judge = judge

    def _run_checks(self, output, context) -> list[CheckResult]:
        out = []
        for c in self.checks:
            try:
                out.append(c.check(output, context))
            except Exception as e:  # a raising check is a failure, never silent
                out.append(CheckResult(ok=False, reason=f"{c.name} raised: {e}"))
        return out

    def check(self, output: Any, context: Context = None) -> VerifyResult:
        results = self._run_checks(output, context)
        ok = all(r.ok for r in results)
        res = VerifyResult(
            ok=ok, value=output if ok else None,
            failures=[r for r in results if not r.ok],
            attempts=[Attempt(1, results, "passed" if ok else "checked")],
            decision="passed" if ok else "rejected",
        )
        self._emit(res)
        return res

    def _call(self, producer, feedback):
        if "feedback" in inspect.signature(producer).parameters:
            return producer(feedback=feedback)
        return producer()

    def run(self, producer: Callable, context: Context = None, escalate=None) -> VerifyResult:
        attempts: list[Attempt] = []
        feedback = None
        output = None
        results: list[CheckResult] = []
        for name, n in self.on_fail.steps:
            tries = (n or 1) if name == "retry" else 1
            for _ in range(tries):
                output = self._call(producer, feedback)
                results = self._run_checks(output, context)
                if all(r.ok for r in results):
                    attempts.append(Attempt(len(attempts) + 1, results, "passed"))
                    return self._finish(True, output, results, attempts, "passed")
                feedback = "; ".join(r.reason for r in results if not r.ok and r.reason)
                attempts.append(Attempt(len(attempts) + 1, results, name))
            if name == "escalate":
                res = self._finish(False, None, results, attempts, "escalated")
                if escalate: escalate(res)
                return res
            if name == "reject":
                return self._finish(False, None, results, attempts, "rejected")
            # "repair" handled in Task 10
        return self._finish(False, None, results, attempts, "rejected")

    def _finish(self, ok, output, results, attempts, decision) -> VerifyResult:
        res = VerifyResult(ok=ok, value=output if ok else None,
                           failures=[r for r in results if not r.ok],
                           attempts=attempts, decision=decision)
        self._emit(res)
        return res

    def _emit(self, res):
        if self.sink: self.sink.write(res)
```
- [ ] **Step 4:** Run `pytest tests/test_verifier.py -v`. Expected: PASS.
- [ ] **Step 5:** Commit `feat: add Verifier orchestrator (check/run, retry/escalate/reject)`.

---

### Task 10: Repair (opt-in)

**Files:** Modify `src/orcaverify/core.py` (handle `repair` step), `tests/test_repair.py`.

- [ ] **Step 1: Failing test**:
```python
from orcaverify.core import Verifier
from orcaverify.checks.predicate import Predicate
from tests.judges.conftest import FakeJudge

def test_repair_runs_judge_and_reverifies():
    j = FakeJudge()
    # passes only once output contains "[repaired]"
    v = Verifier([Predicate(lambda o, c: ("[repaired]" in o, "needs repair"))],
                 on_fail="repair", judge=j)
    r = v.run(lambda feedback=None: "raw output")
    assert r.ok and r.decision == "repaired" and j.rewrites

def test_repair_without_judge_raises():
    import pytest
    v = Verifier([Predicate(lambda o, c: (False, "x"))], on_fail="repair")
    with pytest.raises(ValueError):
        v.run(lambda feedback=None: "x")
```
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement** — in `run`, add a branch for `name == "repair"` before escalate/reject handling:
```python
            if name == "repair":
                if self.judge is None:
                    raise ValueError("on_fail 'repair' requires a judge")
                output = self.judge.rewrite(output, [r.reason for r in results if not r.ok])
                results = self._run_checks(output, context)
                if all(r.ok for r in results):
                    attempts.append(Attempt(len(attempts) + 1, results, "repaired"))
                    return self._finish(True, output, results, attempts, "repaired")
                attempts.append(Attempt(len(attempts) + 1, results, "repair-failed"))
                continue
```
(Place this branch inside the steps loop, after the retry/try block, guarded by `name == "repair"`. Ensure the `_finish` for repaired sets `decision="repaired"`.)
- [ ] **Step 4:** Run `pytest tests/test_repair.py -v`. Expected: PASS.
- [ ] **Step 5:** Commit `feat: add opt-in repair step to Verifier`.

---

### Task 11: @verify decorator

**Files:** Modify `src/orcaverify/core.py` (add `verify`), `tests/test_decorator.py`.

- [ ] **Step 1: Failing test**:
```python
from orcaverify.core import verify
from orcaverify.checks.predicate import Predicate

def test_decorator_returns_value_on_pass():
    @verify(Predicate(lambda o, c: o == "ok"))
    def produce(): return "ok"
    assert produce() == "ok"

def test_decorator_raises_on_reject_by_default():
    import pytest
    from orcaverify.core import VerificationError
    @verify(Predicate(lambda o, c: (False, "no")), on_fail="reject")
    def produce(): return "x"
    with pytest.raises(VerificationError):
        produce()

def test_decorator_return_result_mode():
    @verify(Predicate(lambda o, c: (False, "no")), on_fail="reject", raise_on_fail=False)
    def produce(): return "x"
    res = produce()
    assert res.ok is False
```
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement** in `core.py`:
```python
import functools

class VerificationError(Exception):
    def __init__(self, result):
        self.result = result
        super().__init__(f"verification {result.decision}: "
                         + "; ".join(f.reason or f.meta.get("name", "?") for f in result.failures))

def verify(*checks, on_fail="reject", context=None, sink=None, judge=None,
           raise_on_fail=True, escalate=None):
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
```
- [ ] **Step 4:** Run `pytest tests/test_decorator.py -v`. Expected: PASS.
- [ ] **Step 5:** Commit `feat: add @verify decorator`.

---

### Task 12: Judge adapters (Anthropic, OpenAI, Local)

**Files:** Create `src/orcaverify/judges/{anthropic,openai,local}.py`, `tests/judges/test_adapters.py`.

Adapters share a prompt-based `entails`/`rewrite`. Tests must NOT hit network — inject a fake client. Each adapter takes an optional `client` param (dependency injection) defaulting to the real SDK constructed lazily.

- [ ] **Step 1: Failing test** (inject fake client returning canned text):
```python
from orcaverify.judges.local import LocalJudge

class FakeChat:
    def __init__(self, text): self._text = text
    def complete(self, prompt): return self._text

def test_local_entails_parses_yes():
    j = LocalJudge(client=FakeChat("YES"))
    assert j.entails("claim", ["claim"]).supported is True

def test_local_entails_parses_no():
    j = LocalJudge(client=FakeChat("NO: not in sources"))
    v = j.entails("claim", ["other"])
    assert v.supported is False and "not in sources" in v.reason
```
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement** — a shared `_PromptJudge` base in `judges/base.py` doing prompt construction + YES/NO parsing, with a `_complete(prompt) -> str` abstract method. `LocalJudge(base_url=..., model=..., client=None)` targets OpenAI-compatible (`/v1/chat/completions`) and Ollama; `AnthropicJudge` and `OpenAIJudge` wrap their SDKs. All accept `client=` for injection. Parsing: response starting with `YES` → supported; `NO: <reason>` → unsupported with reason.
- [ ] **Step 4:** Run `pytest tests/judges/test_adapters.py -v`. Expected: PASS.
- [ ] **Step 5:** Commit `feat: add Anthropic/OpenAI/Local judge adapters`.

---

### Task 13: Public exports

**Files:** Modify `src/orcaverify/__init__.py`, `tests/test_public_api.py`.

- [ ] **Step 1: Failing test**:
```python
def test_top_level_imports():
    from orcaverify import (verify, Verifier, VerifyResult, VerificationError,
                            Schema, Predicate, Grounded, NoPII, NoSecrets, OnFail)
    assert verify and Verifier
```
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement** `__init__.py` re-exporting all public names; set `__all__`.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: expose public API`.

---

### Task 14: Examples + README demo

**Files:** Create `examples/aml_investigation.py`, `examples/rag_grounding.py`, finalize `README.md`.

- [ ] **Step 1:** Write `rag_grounding.py` — a `Grounded` + `Schema` demo using a tiny inline `FakeJudge`-style stub so it runs offline; prints a caught ungrounded claim, then a passing run.
- [ ] **Step 2:** Write `aml_investigation.py` — `Schema(Report) + Grounded(regulatory_sources) + NoPII()` with `on_fail="retry(2) -> escalate"`; offline stub judge.
- [ ] **Step 3:** Run both: `python examples/rag_grounding.py` and `python examples/aml_investigation.py`. Expected: clean output showing fail-then-pass.
- [ ] **Step 4:** Write `README.md`: tagline, 30-second quickstart (the decorator example), checks table, on_fail table, judges (incl. local/air-gapped), roadmap (Provenance, more checks, TS port), MIT.
- [ ] **Step 5:** Commit `docs: add examples and README`.

---

### Task 15: Full suite + lint green

- [ ] **Step 1:** Run `ruff check . && ruff format --check .`. Fix issues.
- [ ] **Step 2:** Run `pytest -q`. Expected: all pass.
- [ ] **Step 3:** Run `pytest --cov=orcaverify` (add `pytest-cov` to dev extra). Expected: ≥80% on core paths.
- [ ] **Step 4:** Commit `chore: lint clean + coverage`.

---

## Self-Review

- **Spec coverage:** §3 file structure → Tasks 0–13. §4 contracts → Tasks 1–11. §4 judges (Anthropic/OpenAI/Local + protocol) → Tasks 5, 12. §5 data flow → Task 9–11. §6 error handling (raising check = failure, repair opt-in + requires judge, judge errors propagate) → Tasks 9, 10, 6. §7 testing (fake judge, RegTech edge cases) → Tasks 5, 6, 14. §8 repo/README/examples/CI → Tasks 0, 14, 15. All covered.
- **Placeholders:** Task 12 step 3 describes adapters in prose but gives exact class names, params, and parsing contract tested in step 1 — acceptable (thin SDK wrappers). All other code steps show full code.
- **Type consistency:** `CheckResult(ok, reason, meta)`, `VerifyResult(ok, value, failures, attempts, decision)`, `Attempt(n, results, action)`, `Verdict(supported, reason)`, `OnFail.steps`, `Verifier(checks, on_fail, sink, judge)`, `verify(*checks, ...)` consistent across tasks.
