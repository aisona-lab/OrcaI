# Project: Orca (orca-verify)

## What it is

A drop-in, framework-agnostic verification layer for LLM/agent outputs in Python.
The agent proposes, Orca verifies, the developer decides.

## Stack

- Python 3.11+, Pydantic v2 (core depends on Pydantic only)
- Model SDKs are optional extras: `[anthropic]`, `[openai]`, `[local]`
- Tooling: pytest, pytest-cov, ruff

## Structure

```
src/orcaverify/
  core.py        # Verifier (orchestrator), VerifyResult, @verify, VerificationError
  policy.py      # OnFail: parses "retry(2) -> repair -> escalate -> reject"
  trace.py       # VerifyResult/Attempt + FileSink/LoggerSink
  context.py     # Context type alias
  checks/        # Check (ABC) + Schema, Predicate, Grounded, NoPII/NoSecrets
  judges/        # Judge protocol + PromptJudge + Anthropic/OpenAI/Local adapters
tests/           # mirrors src; FakeJudge in tests/judges/conftest.py
examples/        # offline demos (stub judge, no API key)
```

## Conventions

- One responsibility per module; keep files small (< ~200 lines).
- Each `Check` is isolated and unit-tested in its own file.
- `from __future__ import annotations` at the top of modules using `X | Y`.
- Type-annotate public signatures. Conventional-commit messages.

## Commands

- Install: `pip install -e ".[dev,local]"`
- Test: `pytest -q`
- Coverage: `pytest --cov=orcaverify --cov-report=term-missing`
- Lint/format: `ruff check . && ruff format --check .`
- Run demos: `python examples/rag_grounding.py`

## Hard rules (what NOT to do)

- A check that raises is a **failure with a reason**, never a silent pass.
- `Grounded` and `repair` **require a judge**; misconfiguration must raise, not no-op.
- `repair` is **opt-in** (only when the on_fail chain names it) — it can mask real failures.
- Never echo raw PII/secret matches into reasons or traces — name the category only.
- Tests must not hit the network — inject a fake judge/client.
- Don't merge without tests run green (actually executed).

## Definition of done

Types OK · ruff clean · tests written and passing (run, not assumed) · coverage held
on core paths · diff reviewed · README/examples updated if behavior changed.
