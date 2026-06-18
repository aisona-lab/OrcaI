"""Minimal evaluation harness: do the grounding/faithfulness checks actually work?

Runs each labeled example through the real `Grounded`/`Faithful` checks and a
judge, then reports precision/recall/F1 per check. The positive class is "the
check flags a problem", so:

  recall    = fraction of bad outputs the check caught   (misses are dangerous)
  precision = fraction of flags that were real problems  (false-alarm rate)

Use a real judge (auto-detected from env) for meaningful numbers:

  ANTHROPIC_API_KEY=... python eval/run.py
  OPENAI_API_KEY=...    python eval/run.py
  ORCA_JUDGE_BASE_URL=... python eval/run.py        # local / on-prem

`--fake` swaps in an offline keyword judge so the harness itself can be smoke
-tested without an API key. The fake is NOT a real verifier; ignore its scores.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from orcaverify.checks import Faithful, Grounded
from orcaverify.cli import judge_from_env
from orcaverify.judges.base import Verdict

_DATASET = Path(__file__).parent / "dataset.jsonl"
_CHECKS = {"grounded": Grounded, "faithful": Faithful}


class _KeywordJudge:
    """Offline stand-in: 'supported' iff most of the claim's words appear in a
    source. Only for smoke-testing the harness wiring, never a real verdict."""

    def entails(self, claim, sources):
        return self._verdict(claim, sources)

    def contradicts(self, claim, sources):
        return self._verdict(claim, sources)

    def _verdict(self, claim, sources) -> Verdict:
        blob = " ".join(sources).lower()
        words = [w.strip(".,") for w in claim.lower().split() if len(w) > 3]
        hit = sum(w in blob for w in words)
        ok = bool(words) and hit / len(words) >= 0.6
        return Verdict(supported=ok, reason=None if ok else "low keyword overlap")


def load_dataset(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def prf(tp: int, fp: int, fn: int) -> dict:
    """Precision/recall/F1, zero-safe."""
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": p, "recall": r, "f1": f1}


def evaluate(rows: list[dict], judge) -> tuple[dict, list[str], list[str]]:
    """Run every example. Positive class = the check flagged a problem."""
    buckets: dict[str, dict] = {}
    misses, false_alarms = [], []
    for row in rows:
        check = _CHECKS[row["check"]](sources=row["sources"], judge=judge)
        predicted_bad = not check.check(row["text"]).ok
        actual_bad = not row["expect_ok"]
        b = buckets.setdefault(row["check"], {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
        if actual_bad and predicted_bad:
            b["tp"] += 1
        elif actual_bad and not predicted_bad:
            b["fn"] += 1
            misses.append(row["id"])
        elif not actual_bad and predicted_bad:
            b["fp"] += 1
            false_alarms.append(row["id"])
        else:
            b["tn"] += 1
    return buckets, misses, false_alarms


def _report(buckets: dict, misses: list[str], false_alarms: list[str]) -> None:
    print(f"{'check':<10} {'P':>5} {'R':>5} {'F1':>5}    tp fp fn tn    n")
    for name, b in sorted(buckets.items()):
        m = prf(b["tp"], b["fp"], b["fn"])
        n = sum(b.values())
        print(
            f"{name:<10} {m['precision']:>5.2f} {m['recall']:>5.2f} {m['f1']:>5.2f}   "
            f"{b['tp']:>3}{b['fp']:>3}{b['fn']:>3}{b['tn']:>3}  {n:>3}"
        )
    if misses:
        print(f"\nMISSED (bad output passed — dangerous): {', '.join(misses)}")
    if false_alarms:
        print(f"FALSE ALARMS (good output flagged): {', '.join(false_alarms)}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Evaluate Orca checks against a labeled dataset.")
    ap.add_argument("--fake", action="store_true", help="offline keyword judge (smoke test only)")
    ap.add_argument("--dataset", default=str(_DATASET), help="path to dataset.jsonl")
    args = ap.parse_args(argv)

    judge = _KeywordJudge() if args.fake else judge_from_env()
    if judge is None:
        print(
            "no judge: set ANTHROPIC_API_KEY / OPENAI_API_KEY / ORCA_JUDGE_BASE_URL, "
            "or pass --fake",
            file=sys.stderr,
        )
        return 2

    rows = load_dataset(Path(args.dataset))
    _report(*evaluate(rows, judge))
    return 0


if __name__ == "__main__":
    sys.exit(main())
