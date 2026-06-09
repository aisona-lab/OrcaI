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

## provenance (module 2 — the audit trail)
Plugs in as a `sink`. Every decision becomes a record in a chain.

**chain.py** — `content_hash` = SHA-256 of (seq + time + prev_hash + payload). `verify_records` re-walks the whole chain.
Why: each record locks the one before it. Change one → its hash changes → chain breaks → we see it.

**record.py** — one record: seq, time, prev_hash, content_hash, payload.
Why: prev_hash = the hash of the record before. First record points to GENESIS (all zeros).

**store.py** — where records live. `FileStore` (1 JSON per line), `InMemoryStore` (tests). ABC so Postgres/S3 later.
Why: don't tie the logic to the disk.

**ledger.py** — `Provenance`. `.write(result)` (sink), `.record(event)` (any event), `.verify()` (cheating?), `.export()` (give to auditor).
Why: one object does logging + integrity check + export.

How tamper is caught: edit a payload → content_hash no longer matches. Delete a record → seq jumps + prev_hash points to nothing. Both → `.verify().ok == False` with `broken_at`.

Decision: hash chain only, no secret key. Tamper-EVIDENT (you see it changed), not tamper-PROOF. Simple, no key to lose. HMAC/Ed25519 = later if needed.

## more checks (module 3 — rubric + faithful)
Both reuse the Judge. Added 2 methods to PromptJudge so all real backends get them free.

**checks/_text.py** — pulled `claims()` and `resolve_sources()` out of grounded.
Why: grounded + faithful both need them. DRY. One place to improve sentence splitting later.

**checks/rubric.py** — `Rubric(criteria, judge, threshold)`. Judge scores 0–1, pass if >= threshold.
Why: this is "LLM as judge". criteria = string / list / dict. Duck-types `judge.score`; no score method → loud error.

**checks/faithful.py** — `Faithful(sources, judge)`. Fails if a claim CONTRADICTS a source.
Why: different from Grounded. Grounded = "is it backed?". Faithful = "does it clash?". A claim with no related source passes Faithful but fails Grounded.

**judges/base.py** — added `score()` (parse leading float) and `contradicts()` (YES/NO).
Why: keep one brain. Judge ABC stays minimal (entails+rewrite); these are concrete on PromptJudge so old/custom judges don't break.

## run it
```
pip install -e ".[dev,local]"
pytest -q
python examples/rag_grounding.py
```
74 tests. Core 94–100% covered. The 0% files are the real SDK adapters (need network).
