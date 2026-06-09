"""Grounding demo — runs offline with a tiny stub judge (no API key needed).

Shows Orca catching an ungrounded claim, then passing a grounded one.
Run: python examples/rag_grounding.py
"""

from _stub_judge import StubJudge

from orcaverify import Grounded, Verifier

KNOWLEDGE_BASE = [
    "MiCA is the EU Markets in Crypto-Assets regulation.",
    "CASPs must register with a national competent authority.",
]


def main():
    gate = Verifier([Grounded(sources=KNOWLEDGE_BASE, judge=StubJudge())])

    bad = "MiCA was written by the Bank of Japan in 1990."
    print("Ungrounded output ->", gate.check(bad).decision)
    for f in gate.check(bad).failures:
        print("   reason:", f.reason)

    good = "MiCA is the EU Markets in Crypto-Assets regulation."
    print("Grounded output   ->", gate.check(good).decision)


if __name__ == "__main__":
    main()
