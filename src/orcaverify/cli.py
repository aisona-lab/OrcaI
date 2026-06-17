from __future__ import annotations

import argparse
import sys

from orcaverify.registry import _accepts, available, get, load_plugins


def cmd_checks(args: argparse.Namespace) -> int:
    load_plugins()
    for name in available():
        marked = " *" if _accepts(get(name), "judge") else ""
        print(f"  {name}{marked}")
    print("\n  * needs a judge (set a provider key)")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="orca", description="Verify LLM/agent outputs.")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("checks", help="list available checks")
    c.set_defaults(func=cmd_checks)
    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
