# Orca v2: the `orca` CLI

**Date:** 2026-06-17
**Status:** Approved design, pending implementation plan
**Target version:** 0.2.0 (package is 0.1.0 today; "v2" is the milestone name, not semver 2.0)

## Goal

Give the community a simple, genuinely useful tool: a command-line wrapper over
Orca's existing verification engine. Same product, same stack, wider reach. No
Python wiring required to verify an output or check a provenance chain.

This is a **new surface, not a new product**. Verification, config-building, and
audit already exist as library functions (`from_config`, `Verifier.check`,
`Provenance.verify/export`). The CLI is dispatch + I/O glue over them.

## Non-goals (YAGNI)

- HTTP / `serve` mode — separate future milestone.
- `init` config scaffolding.
- retry / repair from the CLI — they need a producer to re-run, which a CLI
  verifying a static output does not have. CLI `verify` is check-mode only.
- Colors / TTY theming beyond plain `✓` / `✗` marks.
- New core dependencies. `pip install orca-verify` stays dependency-identical.

## Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| v2 deliverable | `orca` CLI |
| Commands | `verify` + `audit` + `checks` |
| Config format | JSON always (stdlib); YAML via optional `[cli]` extra |
| Judge handling | auto-detect from env; offline checks always run |
| Input model | output from file or stdin; sources via `--source` or config |
| Parser | stdlib `argparse` (no `click`/`typer` dependency) |

## Architecture

One new module: `src/orcaverify/cli.py` (~150 lines). If it ever crosses ~200
lines it splits into a `cli/` package — not before.

```toml
# pyproject.toml additions
[project.scripts]
orca = "orcaverify.cli:main"

[project.optional-dependencies]
cli = ["pyyaml>=6"]   # only for YAML configs; JSON needs nothing
```

`main(argv: list[str] | None = None) -> int` parses args, dispatches to one of
three command functions, and returns an exit code. The console-script entry
calls `sys.exit(main())`.

Command functions:

- `cmd_verify(args) -> int`
- `cmd_audit(args) -> int`
- `cmd_checks(args) -> int`

Helper seams (isolated for testability):

- `judge_from_env(env=os.environ) -> Judge | None`
- `load_config(path) -> dict` — JSON by default, YAML by extension
- `read_output(path_or_dash) -> str` — file or stdin
- `read_sources(paths: list[str]) -> list[str]` — file contents

## Commands

```
orca verify [OUTPUT] -c CONFIG [--source PATH ...] [--json]
orca audit verify  LEDGER
orca audit export  LEDGER [-o OUT]
orca checks
```

### verify

1. `cfg = load_config(args.config)`
2. `judge = judge_from_env()`
3. `verifier = from_config(cfg, judge=judge)` — judge auto-injected into checks
   that accept it (existing behavior)
4. `output = read_output(args.output)` — file path, or `-`/omitted = stdin
5. `sources = read_sources(args.source)` (may be empty)
6. `result = verifier.check(output, context=sources or None)`
7. render: pretty per-check list (default) or `--json` dump of `VerifyResult`
8. exit `0` if `result.ok` else `1`

`--source` feeds grounding through `context`: `resolve_sources(sources, context)`
already falls back to `context` when a check has no `sources` of its own. So
sources work whether declared in the config or passed on the command line.

`on_fail` from the config is parsed by `from_config` but **not exercised** —
`Verifier.check()` is pure verification and does not run the policy chain. This
is intentional (no producer in CLI context) and documented; it is not a silent
drop.

### audit

- `audit verify LEDGER` → `Provenance(LEDGER).verify()` → print `ChainResult`
  (`ok`, `broken_at`); exit `0` if intact, `1` if broken.
- `audit export LEDGER [-o OUT]` → `Provenance(LEDGER).export(OUT)`; if no `-o`,
  print the bundle JSON to stdout.

Pure offline, no judge, no API key.

### checks

Run `load_plugins()` (to include third-party checks), then print `available()`,
one name per line. Judge-requiring checks (`grounded`, `faithful`, `rubric`) are
marked with a trailing `*`. A legend line explains the mark.

## Data flow (verify)

```
config file ──load_config──> dict
env ──────────judge_from_env──> Judge | None
                                   │
dict + judge ──from_config──> Verifier
output (file/stdin) ──read_output──> str
--source files ──read_sources──> list[str]
                                   │
str + sources ──verifier.check(output, context=sources or None)──> VerifyResult
VerifyResult ──render(pretty | --json)──> stdout ; exit 0/1
```

## Judge auto-detection

`judge_from_env()` resolves in order, returning the first match or `None`:

1. `ANTHROPIC_API_KEY` → `AnthropicJudge`
2. `OPENAI_API_KEY` → `OpenAIJudge`
3. `ORCA_JUDGE_BASE_URL` → `LocalJudge` (OpenAI-compatible / Ollama, on-prem)
4. none → `None`

It is the only function that touches real model SDKs, so tests monkeypatch it to
inject a fake judge and keep the network out.

## Error handling & exit codes

| Code | Meaning |
|---|---|
| `0` | all checks passed / chain intact |
| `1` | verification failed / chain broken — the CI gate |
| `2` | usage error |

Code `2` covers: missing or unreadable config/output/ledger file; malformed
config; unknown check name; a configured check that needs a judge when none is
detected; a YAML config when `pyyaml` is not installed.

- **Judge required, none configured:** `from_config` builds the check, and the
  check raises `ValueError` at `check()` time (e.g. "Grounded requires a judge").
  The CLI catches it and exits `2` with a message naming the env vars
  (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `ORCA_JUDGE_BASE_URL`). Never a
  silent pass.
- **YAML without the extra:** if the config path ends `.yaml`/`.yml` and `yaml`
  is not importable, exit `2` with "install orca-verify[cli] for YAML, or use a
  JSON config".
- **No PII/secret leakage:** reasons are printed verbatim from `CheckResult`,
  which already names categories only — the CLI adds no raw matches.

## Packaging

- `pyproject.toml`: add `[project.scripts]` `orca` entry and `[cli]` optional
  dependency (`pyyaml>=6`).
- `load_config` chooses parser by extension: `.json` → `json.loads`;
  `.yaml`/`.yml` → `yaml.safe_load` (guarded import). A file with no/other
  extension is parsed as JSON.

## Testing (no network — hard rule)

`tests/test_cli.py`, calling `main([...])` in-process and asserting exit code +
captured stdout/stderr:

1. offline check passes (`no_pii` on clean text) → exit `0`
2. offline check fails → exit `1`, reason printed
3. `--json` emits a valid, parseable `VerifyResult`
4. output read from stdin via `-`
5. `--source` feeds grounding (monkeypatch `judge_from_env` → `FakeJudge`) → `0`
6. judge-requiring check with no judge configured → exit `2`, message names env vars
7. `audit verify` on an intact chain → `0`; on a tampered chain → `1`
8. `audit export` writes a bundle file (and prints to stdout with no `-o`)
9. `checks` lists registered names, marks judge-requiring ones
10. missing/malformed config → exit `2`
11. YAML config path: guarded by `importorskip("yaml")`

`FakeJudge` reuses the existing test fake (`tests/judges/conftest.py`).

## Docs

- README: new **CLI** section showing the trio plus the `[cli]` extra; move CLI
  from "Roadmap" to shipped.
- Bump `__version__` to `0.2.0`.

## Definition of done

Types OK · ruff clean · `tests/test_cli.py` written and passing (actually run) ·
coverage held on core paths · README updated · `orca` entry point works from a
fresh `pip install -e .`.
