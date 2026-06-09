from __future__ import annotations

from typing import Any

# A check's context: a static value (e.g. a list of source documents), or None.
# Grounded reads sources from here when its own `sources` arg is omitted.
Context = Any
