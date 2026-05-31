"""Configuration helpers for the DeepSeek provider."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing."""


@dataclass(frozen=True)
class DeepSeekConfig:
    """Runtime settings for DeepSeek's OpenAI-compatible API."""

    api_key: str | None
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-pro"
    timeout_seconds: float = 120.0
    temperature: float = 0.2
    max_tokens: int = 12000

    @classmethod
    def from_env(
        cls,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> "DeepSeekConfig":
        """Build configuration from explicit values first, then environment."""

        timeout_value = timeout_seconds
        if timeout_value is None:
            timeout_value = float(os.getenv("DEEPSEEK_TIMEOUT", "120"))

        temperature_value = temperature
        if temperature_value is None:
            temperature_value = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.2"))

        max_tokens_value = max_tokens
        if max_tokens_value is None:
            max_tokens_value = int(os.getenv("DEEPSEEK_MAX_TOKENS", "12000"))

        return cls(
            api_key=api_key or os.getenv("DEEPSEEK_API_KEY"),
            base_url=(base_url or os.getenv("DEEPSEEK_BASE_URL") or cls.base_url).rstrip("/"),
            model=model or os.getenv("DEEPSEEK_MODEL") or cls.model,
            timeout_seconds=timeout_value,
            temperature=temperature_value,
            max_tokens=max_tokens_value,
        )

    def require_api_key(self) -> str:
        """Return the configured API key or raise a clear configuration error."""

        if not self.api_key:
            raise ConfigurationError(
                "DEEPSEEK_API_KEY is required for real generation. "
                "Set it in the environment or use --dry-run."
            )
        return self.api_key
