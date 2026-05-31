"""DeepSeek OpenAI-compatible chat completion client."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from legal_doc_agent.config import DeepSeekConfig


class ProviderError(RuntimeError):
    """Raised when the model provider returns an unusable response."""


Message = dict[str, str]


@dataclass
class DeepSeekClient:
    """Minimal stdlib client for DeepSeek chat completions."""

    config: DeepSeekConfig

    def complete(self, messages: Sequence[Message]) -> str:
        """Return assistant text for the provided chat messages."""

        api_key = self.config.require_api_key()
        payload = {
            "model": self.config.model,
            "messages": list(messages),
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        request = urllib.request.Request(
            f"{self.config.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.config.timeout_seconds,
            ) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")[:2000]
            raise ProviderError(
                f"DeepSeek API returned HTTP {exc.code}: {details}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"DeepSeek API request failed: {exc.reason}") from exc

        try:
            data: dict[str, Any] = json.loads(body)
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError(f"Unexpected DeepSeek response shape: {body[:2000]}") from exc

        if not isinstance(content, str) or not content.strip():
            raise ProviderError("DeepSeek returned an empty assistant message.")
        return content.strip()
