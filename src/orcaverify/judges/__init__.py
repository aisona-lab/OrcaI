from orcaverify.judges.base import Judge, PromptJudge, Score, Verdict

__all__ = [
    "Judge",
    "PromptJudge",
    "Verdict",
    "Score",
    "AnthropicJudge",
    "OpenAIJudge",
    "LocalJudge",
]


def __getattr__(name):
    # Lazy import so optional SDK deps aren't required unless the judge is used.
    if name == "AnthropicJudge":
        from orcaverify.judges.anthropic import AnthropicJudge

        return AnthropicJudge
    if name == "OpenAIJudge":
        from orcaverify.judges.openai import OpenAIJudge

        return OpenAIJudge
    if name == "LocalJudge":
        from orcaverify.judges.local import LocalJudge

        return LocalJudge
    raise AttributeError(name)
