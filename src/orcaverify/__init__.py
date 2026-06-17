"""Orca — Your agent proposes. Orca verifies. You decide.

A drop-in, framework-agnostic verification layer for LLM/agent outputs.
"""

from orcaverify.checks import (
    Check,
    CheckResult,
    Faithful,
    Grounded,
    NoPII,
    NoSecrets,
    Predicate,
    Rubric,
    Schema,
)
from orcaverify.core import VerificationError, Verifier, verify
from orcaverify.policy import OnFail
from orcaverify.provenance import FileStore, InMemoryStore, Provenance
from orcaverify.registry import available, build_check, from_config, load_plugins, register
from orcaverify.trace import Attempt, FileSink, LoggerSink, VerifyResult

__version__ = "0.2.0"

__all__ = [
    "verify",
    "Verifier",
    "VerifyResult",
    "VerificationError",
    "OnFail",
    "Attempt",
    "FileSink",
    "LoggerSink",
    "Check",
    "CheckResult",
    "Schema",
    "Predicate",
    "Grounded",
    "NoPII",
    "NoSecrets",
    "Rubric",
    "Faithful",
    "Provenance",
    "FileStore",
    "InMemoryStore",
    "register",
    "build_check",
    "from_config",
    "available",
    "load_plugins",
]
