# Orca — caveman notes

How it was built and why. Short. For me.

## big idea
Agent makes output. We do NOT trust it. We check it. If bad → retry, repair, call human, or reject.
Two things only: **Check** (one test) and **Verifier** (runs many checks + decides).

## the files

**checks/base.py** — `Check` = one rule. `CheckResult(ok, reason, meta)`.
Why: small unit. Easy test. Easy add new rule later.

**checks/schema.py** — output must fit a Pydantic shape.
Why: Pydantic already does the hard part. Don't reinvent.

**checks/predicate.py** — wrap any function `fn(output, ctx)`.
Why: escape hatch. User writes own rule in 1 line. Makes Orca work for anything.

**checks/nopii.py** — regex find email/card/SSN/IBAN, and keys.
Why: cheap. No model needed. We name the category, NEVER print the secret itself.

**checks/grounded.py** — split output into sentences = claims. Ask judge "is this in the sources?". No → fail.
Why: this is the special one. Stops made-up facts. `extract` lets us grab one field from a dict.
Needs a judge → if none, raise (loud, not silent).

**judges/base.py** — `Judge` = entails (claim true?) + rewrite (fix it). `PromptJudge` writes the prompt, reads YES / NO: reason.
Why: one brain shared by all backends. Backends only fill in "talk to model".

**judges/local.py / anthropic.py / openai.py** — three brains. Local talks to Ollama/vLLM (no internet → air-gapped).
Why: privacy + cost. All take `client=` so tests inject a fake → no network in tests.

**policy.py** — turns string `"retry(2) -> repair -> escalate"` into a list of steps.
Why: dev writes plan in plain words, not config objects.

**trace.py** — `VerifyResult` = what happened (input, fails, tries, decision). To JSON. Sinks write to file/log.
Why: every decision recorded. Seed of future audit trail.

**core.py** — the engine.
- `check(output)` = just test a value.
- `run(producer)` = make output, test, then walk the on_fail steps.
  - retry: call again, feed it the reasons ("you missed citations").
  - repair: judge rewrites it. Opt-in only. Can hide real bugs → off by default.
  - escalate: call human function.
  - reject: stop, return fail.
- a check that throws → caught → counts as fail with reason. Never silent.
- `@verify(...)` = sugar. Wrap function. Pass → return value. Fail → raise (or return result).

## decisions I made
- Core only needs Pydantic. Model SDKs optional. → light install, no forced deps.
- Output-based, not framework-based. → works with any agent lib.
- Fake judge in tests. → tests fast, offline, free.
- repair behind a flag. → safety over magic.

## run it
```
pip install -e ".[dev,local]"
pytest -q
python examples/rag_grounding.py
```
46 tests. Core 94–100% covered. The 0% files are the real SDK adapters (need network).
