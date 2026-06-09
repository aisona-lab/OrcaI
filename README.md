<div align="center">

# 🐋 Orca

**Your agent proposes. Orca verifies. You decide.**

A drop-in, framework-agnostic verification layer for LLM and agent outputs in Python.

[![CI](https://github.com/your-handle/OrcaI/actions/workflows/ci.yml/badge.svg)](https://github.com/your-handle/OrcaI/actions)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

Everyone ships AI agents. Almost everyone ships only the **happy path**: prompt → model → output → use it. Orca is the layer the ecosystem skips — the one that makes an output **trustworthy** before it leaves your system.

You declare *checks*. An output ships only if it passes. Otherwise Orca **retries** with feedback, optionally **repairs**, **escalates** to a human, or **rejects** — and records every decision.

```python
from orcaverify import verify, Schema, Grounded, NoPII

@verify(
    Schema(Report),                       # output matches your shape
    Grounded(sources="kb", judge=judge),  # every claim backed by a source
    NoPII(),                              # no leaked personal data
    on_fail="retry(2) -> escalate",       # what to do when it fails
)
def investigate(alert) -> Report:
    return agent.run(alert)               # your agent, any framework
```

Pass → you get the value. Fail → Orca retries with the failure reasons as feedback, then escalates to a human. You never ship an unverified output by accident.

## Install

```bash
pip install orca-verify
# optional model backends for Grounded / repair:
pip install "orca-verify[anthropic]"   # Claude
pip install "orca-verify[openai]"      # OpenAI
pip install "orca-verify[local]"       # Ollama / vLLM / LM Studio (on-prem, air-gapped)
```

## The two concepts

- **`Check`** — one isolated, testable unit of verification.
- **`Verifier`** — runs a list of checks and applies an `on_fail` policy. `@verify` is sugar over it.

```python
from orcaverify import Verifier, Predicate

gate = Verifier([Predicate(lambda out, ctx: (len(out) > 0, "empty output"))])
result = gate.check(output)          # verify a value you already have
if not result.ok:
    for f in result.failures:
        print(f.reason)
```

## Checks (v1)

| Check | What it enforces |
|---|---|
| `Schema(Model)` | Output validates against a Pydantic model |
| `Predicate(fn)` | Any custom rule — the universal escape hatch |
| `Grounded(sources, judge)` | Every claim is supported by a retrieved source (cite or reject) |
| `Faithful(sources, judge)` | No claim contradicts the sources (consistency, not just support) |
| `Rubric(criteria, judge)` | LLM-as-judge scoring against named criteria, passes above a threshold |
| `NoPII()` / `NoSecrets()` | Output doesn't leak personal data or credentials |

## on_fail policy

A chain, tried left to right: `"retry(2) -> repair -> escalate -> reject"`.

| Step | Behavior |
|---|---|
| `retry(n)` | Re-run the producer with the failure reasons injected as feedback |
| `repair` | A judge rewrites the output to satisfy the failed checks *(opt-in; needs a judge)* |
| `escalate` | Hand off to a human-in-the-loop callback |
| `reject` | Return `ok=False` (or raise `VerificationError`) |

## Judges (for Grounded & repair)

`Grounded` and `repair` use a pluggable `Judge`. Ships with `AnthropicJudge`, `OpenAIJudge`, and `LocalJudge` (any OpenAI-compatible server + Ollama, so it runs fully **on-prem / air-gapped**). Or implement the two-method protocol yourself.

## Trace

Every run returns a JSON-serializable `VerifyResult` — input, which checks passed/failed and why, retries, and the final decision. Point a `FileSink` or `LoggerSink` at it and every verification is recorded.

## Provenance — tamper-evident audit trail

Plug `Provenance` in as the sink and every decision becomes a **hash-chained, append-only** record. Edit, delete, or reorder any record and `verify()` catches it — the audit trail a regulator actually wants to see.

```python
from orcaverify import Verifier, NoPII, Provenance

prov = Verifier([NoPII()], sink=Provenance("audit.jsonl"))
# ... run verifications ...

prov.sink.verify()            # ChainResult(ok=True/False, broken_at=...)
prov.sink.export("audit.json")  # full chain + integrity summary for an auditor
prov.sink.record({"event": "data_access", "user": "mlro", "case": "42"})  # log any event
```

Storage is pluggable (`FileStore`, `InMemoryStore`, or your own `ProvenanceStore`). Integrity is plain SHA-256 hash chaining — no keys to manage.

## Run the demos (offline, no API key)

```bash
python examples/rag_grounding.py      # catches an ungrounded claim
python examples/aml_investigation.py  # schema + grounding + no-PII gate
python examples/audit_trail.py        # tamper-evident provenance log
python examples/quality_checks.py     # rubric scoring + faithfulness
```

## Roadmap

- More checks — toxicity/safety, JSON-repair, custom check registry.
- Provenance backends — Postgres/S3 stores; optional HMAC/Ed25519 signing.
- TypeScript port.
- Gateway mode — language-agnostic HTTP interception.
- TypeScript port.

Contributions welcome — each check and judge is a small, isolated module.

## License

MIT
