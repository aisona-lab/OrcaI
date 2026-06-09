from __future__ import annotations

import re
from dataclasses import dataclass

_STEP = re.compile(r"^(retry|repair|escalate|reject)(?:\((\d+)\))?$")


@dataclass
class OnFail:
    """A chain of fallback steps, e.g. "retry(2) -> repair -> escalate"."""

    steps: list[tuple[str, int | None]]

    @classmethod
    def parse(cls, spec: OnFail | str) -> OnFail:
        if isinstance(spec, OnFail):
            return spec
        steps: list[tuple[str, int | None]] = []
        for raw in str(spec).split("->"):
            m = _STEP.match(raw.strip())
            if not m:
                raise ValueError(f"bad on_fail step: {raw!r}")
            name, n = m.group(1), m.group(2)
            steps.append((name, int(n) if n else None))
        return cls(steps)
