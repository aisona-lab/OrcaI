from __future__ import annotations

import re

# Shared helpers for checks that operate on prose grounded against sources.


def claims(text) -> list[str]:
    """Split text into claims, one per sentence (v1 extraction)."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", str(text).strip()) if s.strip()]


def resolve_sources(sources, context) -> list[str]:
    """Sources may be a list, a zero-arg callable, or None (then read from context)."""
    src = sources if sources is not None else context
    if callable(src):
        src = src()
    return list(src) if src else []
