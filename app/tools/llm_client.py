"""OpenAI-compatible chat client using only the Python standard library."""

from __future__ import annotations

import json
import urllib.error
import urllib.request


class LLMClientError(RuntimeError):
    pass


class OpenAICompatibleClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: int = 30,
    ) -> None:
        if not api_key:
            raise LLMClientError("未配置 OPENAI_API_KEY。")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def chat_json(self, system: str, user: str, max_tokens: int = 2500) -> dict:
        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
        except (urllib.error.URLError, KeyError, IndexError, TimeoutError, json.JSONDecodeError) as exc:
            raise LLMClientError(f"LLM API 调用失败：{exc}") from exc
