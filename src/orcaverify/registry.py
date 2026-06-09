from __future__ import annotations

import inspect

from orcaverify.checks import (
    Check,
    Faithful,
    Grounded,
    NoPII,
    NoSecrets,
    Predicate,
    Rubric,
    Schema,
)
from orcaverify.core import Verifier

_REGISTRY: dict[str, type[Check]] = {}


def register(name: str, cls: type[Check] | None = None):
    """Register a Check class under `name`. Usable as a decorator or directly."""
    if cls is None:

        def deco(c: type[Check]) -> type[Check]:
            _REGISTRY[name] = c
            return c

        return deco
    _REGISTRY[name] = cls
    return cls


def get(name: str) -> type[Check]:
    if name not in _REGISTRY:
        raise KeyError(f"no check registered as {name!r}. Available: {available()}")
    return _REGISTRY[name]


def available() -> list[str]:
    return sorted(_REGISTRY)


def _parse_spec(spec) -> tuple[str, dict]:
    if isinstance(spec, str):
        return spec, {}
    if isinstance(spec, dict):
        if "name" in spec:
            return spec["name"], dict(spec.get("args", {}))
        if len(spec) == 1:
            name, args = next(iter(spec.items()))
            if not isinstance(args, dict):
                raise ValueError(f"args for {name!r} must be a dict, got {type(args).__name__}")
            return name, dict(args)
    raise ValueError(f"bad check spec: {spec!r}")


def _accepts(cls: type, param: str) -> bool:
    try:
        return param in inspect.signature(cls.__init__).parameters
    except (ValueError, TypeError):
        return False


def build_check(spec, judge=None) -> Check:
    """Instantiate a check from a name or a {name: args} / {name, args} spec.

    Injects `judge` into checks that accept it, unless the spec already set one.
    """
    name, kwargs = _parse_spec(spec)
    cls = get(name)
    if judge is not None and "judge" not in kwargs and _accepts(cls, "judge"):
        kwargs["judge"] = judge
    return cls(**kwargs)


def from_config(config, judge=None, sink=None) -> Verifier:
    """Build a Verifier from config: a list of check specs, or
    {"checks": [...], "on_fail": "..."}.
    """
    if isinstance(config, dict):
        specs = config["checks"]
        on_fail = config.get("on_fail", "reject")
    else:
        specs, on_fail = config, "reject"
    checks = [build_check(s, judge=judge) for s in specs]
    return Verifier(checks, on_fail=on_fail, sink=sink, judge=judge)


def _default_entry_points(group: str):
    from importlib.metadata import entry_points

    return entry_points(group=group)


def load_plugins(group: str = "orcaverify.checks", *, _entry_points=None) -> list[str]:
    """Discover and register third-party checks exposed via entry points.

    A package declares them under [project.entry-points."orcaverify.checks"].
    Returns the names available after loading.
    """
    eps = (_entry_points or _default_entry_points)(group)
    for ep in eps:
        register(ep.name, ep.load())
    return available()


_BUILTINS: dict[str, type[Check]] = {
    "schema": Schema,
    "predicate": Predicate,
    "grounded": Grounded,
    "faithful": Faithful,
    "rubric": Rubric,
    "no_pii": NoPII,
    "no_secrets": NoSecrets,
}
for _name, _cls in _BUILTINS.items():
    register(_name, _cls)
