from __future__ import annotations

from orcaverify.judges.base import PromptJudge


class OpenAIJudge(PromptJudge):
    """Judge backed by OpenAI. Requires `pip install orca-verify[openai]`.

    Pass `client` for dependency injection (tests); otherwise built lazily.
    """

    def __init__(self, model: str = "gpt-4o-mini", client=None):
        self._model = model
        self._client = client

    def _ensure_client(self):
        if self._client is None:
            import openai

            self._client = openai.OpenAI()
        return self._client

    def _complete(self, prompt: str) -> str:
        client = self._ensure_client()
        resp = client.chat.completions.create(
            model=self._model,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content
