"""Rubric + Faithful demo — runs offline with a stub judge (no API key).

Rubric:   scores the output against criteria, passes above a threshold.
Faithful: fails if any claim contradicts the sources.

In real use, swap StubJudge for AnthropicJudge / OpenAIJudge / LocalJudge.
Run: python examples/quality_checks.py
"""

from _stub_judge import StubJudge

from orcaverify import Faithful, Rubric, Verifier

SOURCES = ["CASPs must register with a national competent authority under MiCA."]


def main():
    judge = StubJudge()
    gate = Verifier(
        [
            Rubric("mentions MiCA and CASP registration", judge=judge, threshold=0.5),
            Faithful(sources=SOURCES, judge=judge),
        ]
    )

    good = "Under MiCA, CASP registration is required."
    print("Good output ->", gate.check(good).decision)

    bad = "Under MiCA, CASPs are not required to register."
    result = gate.check(bad)
    print("Bad output  ->", result.decision)
    for f in result.failures:
        print("   reason:", f.reason)


if __name__ == "__main__":
    main()
