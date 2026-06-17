from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from orcaverify.registry import _accepts, available, from_config, get, load_plugins


class _Usage(Exception):
    """Bad invocation or config -> exit code 2."""


_JUDGE_HINT = "set ANTHROPIC_API_KEY, OPENAI_API_KEY, or ORCA_JUDGE_BASE_URL"


def judge_from_env(env=None):
    """Build a judge from environment, or None. The only seam touching real SDKs."""
    env = os.environ if env is None else env
    if env.get("ANTHROPIC_API_KEY"):
        from orcaverify.judges import AnthropicJudge

        return AnthropicJudge()
    if env.get("OPENAI_API_KEY"):
        from orcaverify.judges import OpenAIJudge

        return OpenAIJudge()
    if env.get("ORCA_JUDGE_BASE_URL"):
        from orcaverify.judges import LocalJudge

        return LocalJudge(
            base_url=env["ORCA_JUDGE_BASE_URL"], model=env.get("ORCA_JUDGE_MODEL", "llama3.1")
        )
    return None


def cmd_checks(args: argparse.Namespace) -> int:
    load_plugins()
    for name in available():
        marked = " *" if _accepts(get(name), "judge") else ""
        print(f"  {name}{marked}")
    print("\n  * needs a judge (set a provider key)")
    return 0


def load_config(path: str) -> dict:
    text = Path(path).read_text()
    try:
        if path.endswith((".yaml", ".yml")):
            import yaml  # optional [cli] extra

            return yaml.safe_load(text)
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise _Usage(f"invalid JSON config {path}: {e}") from e


def read_output(arg: str | None) -> str:
    if arg in (None, "-"):
        return sys.stdin.read()
    return Path(arg).read_text()


def _print_table(verifier, result) -> None:
    results = result.attempts[0].results
    for check, r in zip(verifier.checks, results, strict=True):
        mark = "✓" if r.ok else "✗"
        line = f"  {mark} {check.name:<12}"
        if not r.ok and r.reason:
            line += f" {r.reason}"
        print(line)
    n_fail = len(result.failures)
    print(f"\n{n_fail} failed" if n_fail else "\nall passed")


def cmd_verify(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    verifier = from_config(cfg, judge=judge_from_env())
    output = read_output(args.output)
    sources = [Path(p).read_text() for p in (args.source or [])]
    result = verifier.check(output, context=sources or None)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_table(verifier, result)
    return 0 if result.ok else 1


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="orca", description="Verify LLM/agent outputs.")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("checks", help="list available checks")
    c.set_defaults(func=cmd_checks)

    v = sub.add_parser("verify", help="run checks against an output")
    v.add_argument("output", nargs="?", help="output file, or - / omitted for stdin")
    v.add_argument("-c", "--config", required=True, help="JSON or YAML check config")
    v.add_argument("--source", nargs="*", help="source files for grounding")
    v.add_argument("--json", action="store_true", help="emit JSON result")
    v.set_defaults(func=cmd_verify)

    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return args.func(args)
    except _Usage as e:
        print(f"orca: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"orca: file not found: {e.filename}", file=sys.stderr)
        return 2
    except ValueError as e:
        msg = str(e)
        if "requires a judge" in msg:
            msg = f"{msg}; {_JUDGE_HINT}"
        print(f"orca: {msg}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
