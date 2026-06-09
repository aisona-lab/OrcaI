# Orca — Design Spec (v1)

**Date:** 2026-06-09
**Status:** Approved for implementation planning
**Tagline:** *Your agent proposes. Orca verifies. You decide.*

---

## 1. Problem & Positioning

Everyone is shipping AI agents, and almost everyone builds only the **happy path**: prompt → model → output → use it. The hard, ignored layers — the ones that make an agent *trustworthy and auditable* — are evaluation, guardrails, grounding, human-in-the-loop, and the discipline of *"the agent proposes, the system verifies, you decide."*

**Orca** is a drop-in, framework-agnostic **verification layer** for LLM/agent outputs in Python. It does not produce outputs; it gates them. You declare *verifiers*, and an output only ships if it passes — otherwise Orca retries with feedback, optionally repairs, escalates to a human, or rejects.

- **Audience:** Python developers building agents/LLM apps with any framework (OpenAI SDK, Anthropic SDK, LangGraph, CrewAI, LlamaIndex, custom).
- **Differentiation:** Not "another agent framework." It is the *output-control layer* the ecosystem skips. Born from RegTech/AML production experience where ungrounded or leaky outputs are catastrophic.
- **Goals:** Useful open-source tool (GitHub stars), portfolio centerpiece, proof of senior agentic-engineering judgement.

### Non-goals (v1)

- Not an orchestration framework. Orca wraps *your* producer function; it does not run agents for you.
- Not an observability dashboard. It emits structured traces; visualization is out of scope.
- Cryptographic / immutable regulator-grade audit is **v2** (`Provenance` module).
- No automatic prompt management or model routing.

---

## 2. Decisions (locked)

| Decision | Choice |
|---|---|
| Concept | "Verify" — the proposes→verifies→decides layer |
| Positioning | Horizontal, open source, production-grade niche |
| Ecosystem | Python first (TypeScript port is future) |
| Brand / package | Brand **Orca**; pip package **`orca-verify`**; import **`orcaverify`**; API **`@verify`** |
| API shape | Pipeline (`Verifier`) + decorator (`@verify`) sugar |
| v1 verifiers | Schema, Predicate (custom), Grounded, NoPII/NoSecrets |
| on_fail strategies | reject, retry-with-feedback, escalate-to-human, repair (opt-in, flagged) |
| Default on_fail order | `retry → repair? → escalate → reject` |
| Trace/audit | Lightweight JSON-serializable result + sinks (file/logger). Crypto/immutable = v2 |
| Judge adapters | Anthropic (default), OpenAI, Local (OpenAI-compatible + Ollama), open protocol |

**PyPI verified:** `orca` is taken (plotly); `orca-verify` and `orcaverify` are free.

---

## 3. Architecture

Two concepts only: a **`Check`** (an isolated, independently testable unit of verification) and a **`Verifier`** (orchestrates a list of checks + an on_fail policy). `@verify` is sugar over `Verifier`.

```
src/orcaverify/
├── __init__.py          # exports: verify, Verifier, VerifyResult, checks, judges
├── core.py              # Verifier (orchestrator), VerifyResult, @verify decorator
├── policy.py            # OnFail: parse/represent "retry(2) -> repair -> escalate"
├── trace.py             # VerifyResult serialization + sinks (file JSONL / logger)
├── checks/
│   ├── base.py          # Check (ABC): .check(output, context) -> CheckResult
│   ├── schema.py        # Schema(PydanticModel)
│   ├── predicate.py     # Predicate(fn)            — universal escape hatch
│   ├── grounded.py      # Grounded(sources, judge) — the differentiator
│   └── nopii.py         # NoPII() / NoSecrets()
└── judges/
    ├── base.py          # Judge / LLM protocol (no hard dependency)
    ├── anthropic.py     # Claude adapter (default)
    ├── openai.py        # OpenAI adapter
    └── local.py         # OpenAI-compatible (vLLM, LM Studio, llama.cpp) + Ollama native
```

**Dependency discipline:** core depends on **Pydantic only**. Model SDKs are optional extras:
`orca-verify[anthropic]`, `[openai]`, `[local]`, `[pii]`. Each module stays small and focused (target < 200–300 lines).

---

## 4. Components & Contracts

### `Check` (ABC) — `checks/base.py`
```python
class Check(ABC):
    name: str
    @abstractmethod
    def check(self, output: Any, context: Context) -> CheckResult: ...

@dataclass
class CheckResult:
    ok: bool
    reason: str | None = None      # human-readable failure reason (feeds retry feedback)
    meta: dict = field(default_factory=dict)
```

### Built-in checks
- **`Schema(model)`** — validates `output` against a Pydantic model; failure reason = validation errors.
- **`Predicate(fn, name=...)`** — `fn(output, context) -> bool | (bool, reason)`. Universal escape hatch; makes Orca use-case agnostic.
- **`Grounded(sources, judge=None, min_support=...)`** — extracts claims from `output`, checks each against `sources` via a `Judge`; unsupported claims are listed as failure reasons. Sources may be a list, a callable, or read from `context`.
- **`NoPII()` / `NoSecrets()`** — regex + optional detector; failure reason names the leaked category/span (span redacted in the reason itself).

### `Verifier` — `core.py`
```python
class Verifier:
    def __init__(self, checks: list[Check], on_fail: OnFail | str = "reject", sink: Sink | None = None): ...
    def check(self, output, context=None) -> VerifyResult: ...        # verify only
    def run(self, producer: Callable[..., Any], context=None, **kw) -> VerifyResult: ...  # produce + verify + policy
```

### `@verify` decorator — `core.py`
```python
@verify(Schema(Report), Grounded(sources="kb"), NoPII(), on_fail="retry(2) -> escalate", context=...)
def investigate(alert) -> Report:
    return agent.run(alert)
```
`context` may be static or a callable receiving the same args as the decorated function.

### `VerifyResult` — `trace.py`
```python
@dataclass
class VerifyResult:
    ok: bool
    value: Any | None
    failures: list[CheckResult]          # checks that failed on the final attempt
    attempts: list[Attempt]              # full trace: each attempt's check results + action taken
    decision: Literal["passed", "repaired", "escalated", "rejected"]
    def to_dict(self) -> dict: ...        # JSON-serializable
```

### `Judge` / `LLM` protocol — `judges/base.py`
A minimal protocol used by `Grounded` (claim-vs-source entailment) and `repair` (rewrite to satisfy failed checks). Adapters: Anthropic (default), OpenAI, Local. `local.py` targets OpenAI-compatible servers via configurable `base_url` (vLLM, LM Studio, llama.cpp) and Ollama's native API — enabling fully on-prem / air-gapped operation.

---

## 5. Data Flow — the propose → verify → decide loop

1. Decorated function (the **producer**) is called → yields `output`.
2. `Verifier.run` executes every `Check` → collects `CheckResult`s → records an `Attempt` in the trace.
3. All pass → return `value`, persist trace to sink, done (`decision="passed"`).
4. On failure, apply `OnFail` policy (default `retry → repair? → escalate → reject`):
   - **retry(n):** re-invoke producer with failure reasons injected as feedback (backoff between attempts).
   - **repair (opt-in):** a `Judge` rewrites the output to satisfy failed checks; re-verified before acceptance.
   - **escalate:** invoke a human-in-the-loop callback / queue handler (`decision="escalated"`).
   - **reject:** return `VerifyResult(ok=False, ...)` or raise, per config (`decision="rejected"`).
5. Final `VerifyResult` written to `sink` (JSONL file or logger).

---

## 6. Error Handling (nothing fails silently)

- A `Check` that raises → treated as a failure with an explicit reason; never swallowed.
- A producer exception → counts as a failed attempt (configurable: propagate vs. retry), recorded in the trace.
- Judge/model errors → propagated with clear context (no silent fallback to "ok").
- `repair` is **opt-in and explicitly flagged** — off by default, because an LLM rewriting output can mask real failures.

---

## 7. Testing (target 80%+ on critical paths, TDD)

- Each `Check` unit-tested in isolation (red → green → refactor).
- `Verifier` orchestration tested with fake checks/producers: retry-with-feedback, escalate, reject paths.
- `Grounded` and `repair` tested with a **fake Judge** — zero network in tests.
- RegTech-flavored edge cases: claim without a source → blocked; output containing PII → blocked; clean control case → passes.
- CI runs the real suite (`pytest`) — no self-reported "green" without execution.

---

## 8. Repo, Packaging & Community

- `pyproject.toml`, `src/` layout, MIT license.
- CI (GitHub Actions): `ruff` + `pytest` + build.
- **README** with a 30-second demo: Orca catching an ungrounded output, then the same call passing after grounding.
- `examples/`: (a) AML investigation with mandatory citation, (b) generic RAG grounding.
- `CLAUDE.md` per the playbook: hard rules, commands, definition of done.
- Visible roadmap inviting contributions: **②Provenance** (immutable/crypto audit), **③more checks** (toxicity, faithfulness, rubric/LLM-judge), TypeScript port.

---

## 9. Out of Scope for v1 (future modules)

- `Provenance`: append-only, cryptographically verifiable, regulator-exportable audit trail.
- Additional checks: Toxicity/Safety, Faithfulness/Consistency, Rubric (LLM-judge scoring).
- Gateway/proxy deployment mode (language-agnostic HTTP interception).
- TypeScript port.
