from __future__ import annotations

import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

# Shared helpers for checks that operate on prose grounded against sources.

_MAX_WORKERS = 8


# ponytail: hand-picked abbreviations, not a real sentence tokenizer. Covers the
# common offenders that make naive splitting produce a bare "Dr." claim. Swap for
# a tokenizer (pysbd/nltk) only if the eval shows it's worth the dependency.
_ABBREV = {
    "dr",
    "mr",
    "mrs",
    "ms",
    "prof",
    "sr",
    "jr",
    "st",
    "vs",
    "etc",
    "e.g",
    "i.e",
    "u.s",
    "u.k",
    "inc",
    "ltd",
}


def _ends_with_abbrev(piece: str) -> bool:
    words = piece.split()
    return bool(words) and words[-1].rstrip(".").lower() in _ABBREV


def claims(text) -> list[str]:
    """Split text into claims, one per sentence (v1 extraction).

    Naive sentence splitting would break "Dr. Smith ..." into a bare "Dr." claim;
    we rejoin a fragment onto the next when it ends in a known abbreviation.
    """
    parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", str(text).strip()) if s.strip()]
    out: list[str] = []
    for part in parts:
        if out and _ends_with_abbrev(out[-1]):
            out[-1] = f"{out[-1]} {part}"
        else:
            out.append(part)
    return out


# ponytail: private on purpose — keeps the pool/signature free to change.
# Export from orcaverify.checks (+ __all__) when a real plugin does per-claim
# judging and needs the fan-out; until then it's speculative API surface.
def failing(items: list[str], is_bad: Callable[[str], bool]) -> list[str]:
    """Return items where `is_bad(item)` holds, in order, evaluating concurrently.

    Each claim is an independent judge round-trip, so we fan them out across a
    thread pool: N claims cost ~1x latency instead of Nx. Order is preserved
    (ThreadPoolExecutor.map yields in input order), so reasons stay deterministic.
    """
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(items))) as ex:
        flags = ex.map(is_bad, items)
    return [item for item, bad in zip(items, flags, strict=True) if bad]


def resolve_sources(sources, context) -> list[str]:
    """Sources may be a list, a zero-arg callable, or None (then read from context)."""
    src = sources if sources is not None else context
    if callable(src):
        src = src()
    return list(src) if src else []
