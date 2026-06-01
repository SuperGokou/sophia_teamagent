"""NVIDIA OpenAI-compatible chat completion client."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from legal_doc_agent.config import NvidiaConfig


class ProviderError(RuntimeError):
    """Raised when the model provider returns an unusable response."""


Message = dict[str, str]


@dataclass
class NvidiaClient:
    """Minimal stdlib client for NVIDIA chat completions."""

    config: NvidiaConfig

    def complete(
        self,
        messages: Sequence[Message],
        *,
        role: str | None = None,
    ) -> str:
        """Return assistant text for the provided chat messages."""

        api_key = self.config.require_api_key()
        payload = {
            "model": self.config.model,
            "messages": list(messages),
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "max_tokens": self.config.max_tokens,
            "stream": self.config.stream,
        }
        chat_template_kwargs: dict[str, bool] = {}
        if self.config.thinking is not None:
            chat_template_kwargs["thinking"] = self.config.thinking
        if self.config.enable_thinking is not None:
            chat_template_kwargs["enable_thinking"] = self.config.enable_thinking
        if chat_template_kwargs:
            payload["chat_template_kwargs"] = chat_template_kwargs
        if self.config.reasoning_budget is not None:
            payload["reasoning_budget"] = self.config.reasoning_budget
        request = urllib.request.Request(
            f"{self.config.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream" if self.config.stream else "application/json",
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
                f"NVIDIA API returned HTTP {exc.code}: {details}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"NVIDIA API request failed: {exc.reason}") from exc

        try:
            content = (
                _parse_streaming_content(body)
                if self.config.stream
                else _parse_json_content(body)
            )
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError(f"Unexpected NVIDIA response shape: {body[:2000]}") from exc

        if not isinstance(content, str) or not content.strip():
            raise ProviderError("NVIDIA returned an empty assistant message.")
        return content.strip()


def _parse_json_content(body: str) -> str:
    data: dict[str, Any] = json.loads(body)
    choice = data["choices"][0]
    message = choice["message"]
    content = message.get("content") or ""
    if not content and choice.get("finish_reason") == "length":
        raise ProviderError(
            "NVIDIA response was truncated before assistant content. "
            "Increase max_tokens for this model."
        )
    return content


def _parse_streaming_content(body: str) -> str:
    parts: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or not stripped.startswith("data:"):
            continue
        payload = stripped.removeprefix("data:").strip()
        if payload == "[DONE]":
            break
        chunk: dict[str, Any] = json.loads(payload)
        choices = chunk.get("choices") or []
        if not choices:
            continue
        content = choices[0].get("delta", {}).get("content")
        if content is not None:
            parts.append(content)
    return "".join(parts)
