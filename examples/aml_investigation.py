"""AML investigation demo — the RegTech flavor that inspired Orca.

A compliance "agent" drafts an investigation report. Orca enforces three things
before the report can ship:
  1. Schema      — the report has the required fields.
  2. Grounded    — every statement is backed by a regulatory source.
  3. NoPII       — the report never leaks personal data.

Runs offline with a stub judge. Run: python examples/aml_investigation.py
"""

from _stub_judge import StubJudge
from pydantic import BaseModel

from orcaverify import Grounded, NoPII, Schema, verify

REGULATION = [
    "Structuring is splitting deposits to stay under the reporting threshold.",
    "Suspicious activity must be reported to the competent authority.",
]


class Report(BaseModel):
    title: str
    finding: str


@verify(
    Schema(Report),
    Grounded(sources=REGULATION, judge=StubJudge(), extract=lambda o: o["finding"]),
    NoPII(),
)
def draft_report() -> dict:
    return {
        "title": "Alert 42",
        "finding": "Structuring is splitting deposits to stay under the reporting threshold.",
    }


if __name__ == "__main__":
    report = draft_report()  # raises VerificationError if any check fails
    print("Report shipped:", report)
