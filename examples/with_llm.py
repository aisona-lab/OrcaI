"""Real-LLM integration — Orca wrapping an actual model call.

A model drafts an answer; Orca enforces that every claim is grounded in the
provided sources, with one retry on failure. Uses whichever provider key is set
(ANTHROPIC_API_KEY or OPENAI_API_KEY). No key set: prints how to run and exits.

Run: ANTHROPIC_API_KEY=... python examples/with_llm.py
"""

import os

from orcaverify import Grounded, VerificationError, verify

SOURCES = [
    "Orca verifies LLM outputs before they ship.",
    "Orca runs fully on-prem via the LocalJudge.",
]


def _pick_judge():
    if os.getenv("ANTHROPIC_API_KEY"):
        from orcaverify.judges import AnthropicJudge

        return AnthropicJudge(), _anthropic_completer()
    if os.getenv("OPENAI_API_KEY"):
        from orcaverify.judges import OpenAIJudge

        return OpenAIJudge(), _openai_completer()
    return None, None


def _anthropic_completer():
    import anthropic

    client = anthropic.Anthropic()

    def complete(prompt: str) -> str:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    return complete


def _openai_completer():
    import openai

    client = openai.OpenAI()

    def complete(prompt: str) -> str:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content

    return complete


def main():
    judge, complete = _pick_judge()
    if judge is None:
        print("Set ANTHROPIC_API_KEY or OPENAI_API_KEY to run this example.")
        return

    @verify(Grounded(sources=SOURCES, judge=judge), on_fail="retry(1) -> reject")
    def answer(question: str) -> str:
        prompt = (
            "Answer in one or two sentences using ONLY these facts:\n"
            + "\n".join(f"- {s}" for s in SOURCES)
            + f"\n\nQuestion: {question}"
        )
        return complete(prompt)

    try:
        print("Answer:", answer("What does Orca do and can it run on-prem?"))
    except VerificationError as e:
        print("Blocked ungrounded answer:", e)


if __name__ == "__main__":
    main()
