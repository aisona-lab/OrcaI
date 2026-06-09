from __future__ import annotations

from orcaverify.judges.base import PromptJudge


class AnthropicJudge(PromptJudge):
    """Judge backed by Claude. Requires `pip install orca-verify[anthropic]`.

    Pass `client` for dependency injection (tests); otherwise built lazily.
    """

    def __init__(self, model: str = "claude-haiku-4-5-20251001", client=None):
        self._model = model
        self._client = client

    def _ensure_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def _complete(self, prompt: str) -> str:
        client = self._ensure_client()
        msg = client.messages.create(
            model=self._model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
