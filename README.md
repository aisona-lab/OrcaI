<div align="center">

# OrcaI 🫍

**Your agent proposes. Orca verifies. You decide.**

A drop-in, framework-agnostic verification layer for LLM and agent outputs in Python.

[![CI](https://github.com/aisona-lab/OrcaI/actions/workflows/ci.yml/badge.svg)](https://github.com/aisona-lab/OrcaI/actions)
[![PyPI](https://img.shields.io/pypi/v/orca-verify)](https://pypi.org/project/orca-verify/)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

## Why Orca

Everyone ships AI agents. Almost everyone ships only the happy path: prompt, model, output, use it. Orca is the layer most projects skip, the one that makes an output trustworthy before it leaves your system.

You declare *checks*. An output ships only if it passes. Otherwise Orca retries with feedback, optionally repairs, escalates to a human, or rejects, and it records every decision along the way.

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

On pass you get the value back. On failure Orca retries with the failure reasons as feedback, then escalates to a human. You never ship an unverified output by accident.

## Install

```bash
pip install orca-verify
```

Optional model backends, used by `Grounded`, `Faithful`, `Rubric`, and repair:

```bash
pip install "orca-verify[anthropic]"   # Claude
pip install "orca-verify[openai]"      # OpenAI
pip install "orca-verify[local]"       # Ollama, vLLM, LM Studio (on-prem, air-gapped)
```

## Two concepts

A `Check` is one isolated, testable unit of verification. A `Verifier` runs a list of checks and applies an `on_fail` policy. The `@verify` decorator is sugar over `Verifier`.

```python
from orcaverify import Verifier, Predicate

gate = Verifier([Predicate(lambda out, ctx: (len(out) > 0, "empty output"))])
result = gate.check(output)          # verify a value you already have
if not result.ok:
    for f in result.failures:
        print(f.reason)
```

## Checks

| Check | What it enforces |
|---|---|
| `Schema(Model)` | Output validates against a Pydantic model |
| `Predicate(fn)` | Any custom rule, the universal escape hatch |
| `Grounded(sources, judge)` | Every claim is supported by a retrieved source, cite or reject |
| `Faithful(sources, judge)` | No claim contradicts the sources, consistency rather than support |
| `Rubric(criteria, judge)` | LLM-as-judge scoring against named criteria, passes above a threshold |
| `NoPII()` / `NoSecrets()` | Output does not leak personal data or credentials |

## on_fail policy

A chain, tried left to right, for example `"retry(2) -> repair -> escalate -> reject"`.

| Step | Behavior |
|---|---|
| `retry(n)` | Re-run the producer with the failure reasons injected as feedback |
| `repair` | A judge rewrites the output to satisfy the failed checks (opt-in, needs a judge) |
| `escalate` | Hand off to a human-in-the-loop callback |
| `reject` | Return `ok=False`, or raise `VerificationError` |

## Judges

`Grounded`, `Faithful`, `Rubric`, and repair use a pluggable `Judge`. Orca ships with `AnthropicJudge`, `OpenAIJudge`, and `LocalJudge`. `LocalJudge` targets any OpenAI-compatible server plus Ollama, so it runs fully on-prem or air-gapped. You can also implement the protocol yourself.

## Trace

Every run returns a JSON-serializable `VerifyResult`: the input, which checks passed or failed and why, the retries, and the final decision. Point a `FileSink` or `LoggerSink` at it and every verification is recorded.

## Tamper-evident audit trail

Plug `Provenance` in as the sink and every decision becomes a hash-chained, append-only record. Edit, delete, or reorder any record and `verify()` catches it. This is the audit trail a regulator actually wants to see.

```python
from orcaverify import Verifier, NoPII, Provenance

prov = Verifier([NoPII()], sink=Provenance("audit.jsonl"))
# ... run verifications ...

prov.sink.verify()                            # ChainResult(ok=True/False, broken_at=...)
prov.sink.export("audit.json")                # full chain plus integrity summary
prov.sink.record({"event": "data_access"})    # log any auditable event
```

Storage is pluggable (`FileStore`, `InMemoryStore`, or your own `ProvenanceStore`). Integrity is plain SHA-256 hash chaining, with no keys to manage.

## Extend it: registry and plugins

Register your own check, then compose verifiers from config. Built-in checks are registered under `schema`, `predicate`, `grounded`, `faithful`, `rubric`, `no_pii`, and `no_secrets`.

```python
from orcaverify import Check, CheckResult, register, from_config

@register("max_length")
class MaxLength(Check):
    def __init__(self, limit=280):
        self.limit = limit

    def check(self, output, context=None):
        n = len(str(output))
        return CheckResult(ok=n <= self.limit, reason=None if n <= self.limit else f"too long: {n}")

gate = from_config({
    "checks": ["no_pii", {"max_length": {"limit": 280}}, "grounded"],
    "on_fail": "retry(2) -> reject",
}, judge=judge)   # the judge is auto-injected into checks that need it
```

Ship checks in your own package and expose them through entry points. `load_plugins()` discovers and registers them automatically:

```toml
[project.entry-points."orcaverify.checks"]
toxicity = "my_pkg.checks:Toxicity"
```

## CLI

Verify outputs and audit trails from the terminal, no Python required.

```bash
orca verify out.txt -c orca.json         # run a config of checks (exit 1 on failure)
cat out.txt | orca verify - -c orca.json  # read the output from stdin
orca verify out.txt -c rag.json --source kb/*.md   # grounding sources
orca audit verify audit.jsonl            # prove a provenance chain is intact
orca audit export audit.jsonl -o bundle.json
orca checks                              # list available checks (* needs a judge)
```

Config is JSON out of the box; YAML works with the `[cli]` extra:

```bash
pip install "orca-verify[cli]"
```

```yaml
# orca.yaml
checks:
  - no_pii
  - grounded
on_fail: reject
```

Checks that need a judge (`grounded`, `faithful`, `rubric`) pick up a provider
automatically from `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `ORCA_JUDGE_BASE_URL`.
Offline checks run with zero setup. Exit codes: `0` pass, `1` verification failed,
`2` usage error.

## Run the demos

All demos run offline, with no API key.

```bash
python examples/rag_grounding.py      # catches an ungrounded claim
python examples/aml_investigation.py  # schema, grounding, and no-PII gate
python examples/audit_trail.py        # tamper-evident provenance log
python examples/quality_checks.py     # rubric scoring and faithfulness
python examples/custom_check.py       # register a check and build from config
```

To see Orca wrap a real model call (grounding a live answer against sources), set a provider key:

```bash
ANTHROPIC_API_KEY=... python examples/with_llm.py   # or OPENAI_API_KEY
```

## Evaluation

The judge-backed checks are only as trustworthy as their precision and recall.
`eval/` holds a small hand-labeled dataset and a runner that measures both,
treating "the check flags a problem" as the positive class, so **recall is the
fraction of bad outputs caught** and **precision is the false-alarm rate**.

```bash
ANTHROPIC_API_KEY=... python eval/run.py   # or OPENAI_API_KEY / ORCA_JUDGE_BASE_URL
python eval/run.py --fake                   # offline smoke test (not a real verdict)
```

It prints per-check precision/recall/F1 plus the exact misses and false alarms,
so changes to claim extraction or judge prompts can be judged by the numbers,
not by feel. Add cases to `eval/dataset.jsonl` as new failure modes show up.

## Roadmap

- More checks: toxicity and safety, JSON repair.
- Provenance backends: Postgres and S3 stores, optional HMAC or Ed25519 signing.
- Gateway mode: language-agnostic HTTP interception.
- TypeScript port.

Contributions are welcome. Each check and judge is a small, isolated module.

## License

MIT
