from __future__ import annotations

from orcaverify.judges.base import PromptJudge

_DEFAULT_URL = "http://localhost:11434/v1"  # Ollama's OpenAI-compatible endpoint


class _HTTPChat:
    """Minimal client for any OpenAI-compatible /chat/completions endpoint.

    Works with Ollama, vLLM, LM Studio, llama.cpp server. No external SDK needed.
    """

    def __init__(self, base_url: str, model: str, api_key: str = "not-needed"):
        import httpx

        self._url = base_url.rstrip("/") + "/chat/completions"
        self._model = model
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._client = httpx.Client(timeout=60)

    def complete(self, prompt: str) -> str:
        resp = self._client.post(
            self._url,
            headers=self._headers,
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


class LocalJudge(PromptJudge):
    """Judge running fully on-prem / air-gapped against a local model server.

    Pass a custom `client` (anything with `.complete(prompt) -> str`) for tests
    or non-OpenAI-shaped servers; otherwise an HTTP client is built lazily.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_URL,
        model: str = "llama3.1",
        api_key: str = "not-needed",
        client=None,
    ):
        self._client = client or _HTTPChat(base_url, model, api_key)

    def _complete(self, prompt: str) -> str:
        return self._client.complete(prompt)
