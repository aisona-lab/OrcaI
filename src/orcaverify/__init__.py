"""Orca — Your agent proposes. Orca verifies. You decide.

A drop-in, framework-agnostic verification layer for LLM/agent outputs.
"""

from orcaverify.checks import Check, CheckResult, Grounded, NoPII, NoSecrets, Predicate, Schema
from orcaverify.core import VerificationError, Verifier, verify
from orcaverify.policy import OnFail
from orcaverify.trace import Attempt, FileSink, LoggerSink, VerifyResult

__version__ = "0.1.0"

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
]
