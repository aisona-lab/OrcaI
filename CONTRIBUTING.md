# Contributing to Orca

Thanks for your interest. Orca is built from small, isolated modules, so most
contributions touch one file.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,local]"
pytest -q
```

## Before opening a PR

```bash
ruff format .
ruff check .
pytest -q
```

All three must be clean. Add tests for any new behavior; tests must run offline
(inject a fake judge or client, never hit the network).

## Adding a check

A check is one class with one responsibility:

```python
from orcaverify import Check, CheckResult, register

@register("my_check")
class MyCheck(Check):
    name = "my_check"

    def check(self, output, context=None) -> CheckResult:
        ok = ...  # your rule
        return CheckResult(ok=ok, reason=None if ok else "why it failed")
```

Put it in `src/orcaverify/checks/`, add a test in `tests/checks/`, and register
it so it works with `from_config`. A check that raises is treated as a failure
with a reason, never a silent pass.

## Distributing checks as plugins

You can also ship checks in your own package and expose them via entry points:

```toml
[project.entry-points."orcaverify.checks"]
my_check = "my_pkg.checks:MyCheck"
```

`load_plugins()` will discover and register them.

## Conventions

- Keep files focused (under ~200 lines).
- Type-annotate public signatures.
- Conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
