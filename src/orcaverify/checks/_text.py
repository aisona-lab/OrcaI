from __future__ import annotations

import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

# Shared helpers for checks that operate on prose grounded against sources.

_MAX_WORKERS = 8


def claims(text) -> list[str]:
    """Split text into claims, one per sentence (v1 extraction)."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", str(text).strip()) if s.strip()]


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
