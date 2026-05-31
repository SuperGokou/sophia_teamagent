"""Configuration helpers for the NVIDIA provider."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing."""


@dataclass(frozen=True)
class NvidiaConfig:
    """Runtime settings for NVIDIA's OpenAI-compatible API."""

    api_key: str | None
    base_url: str = "https://integrate.api.nvidia.com/v1"
    model: str = "deepseek-ai/deepseek-v4-pro"
    timeout_seconds: float = 120.0
    temperature: float = 1.0
    top_p: float = 0.95
    max_tokens: int = 16384
    thinking: bool = False

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
        top_p: float | None = None,
        thinking: bool | None = None,
    ) -> "NvidiaConfig":
        """Build configuration from explicit values first, then environment."""

        timeout_value = timeout_seconds
        if timeout_value is None:
            timeout_value = float(os.getenv("NVIDIA_TIMEOUT", "120"))

        temperature_value = temperature
        if temperature_value is None:
            temperature_value = float(os.getenv("NVIDIA_TEMPERATURE", "1"))

        top_p_value = top_p
        if top_p_value is None:
            top_p_value = float(os.getenv("NVIDIA_TOP_P", "0.95"))

        max_tokens_value = max_tokens
        if max_tokens_value is None:
            max_tokens_value = int(os.getenv("NVIDIA_MAX_TOKENS", "16384"))

        thinking_value = thinking
        if thinking_value is None:
            thinking_value = _parse_bool(os.getenv("NVIDIA_THINKING"), default=False)

        return cls(
            api_key=api_key or os.getenv("NVIDIA_API_KEY"),
            base_url=(base_url or os.getenv("NVIDIA_BASE_URL") or cls.base_url).rstrip("/"),
            model=model or os.getenv("NVIDIA_MODEL") or cls.model,
            timeout_seconds=timeout_value,
            temperature=temperature_value,
            top_p=top_p_value,
            max_tokens=max_tokens_value,
            thinking=thinking_value,
        )

    def require_api_key(self) -> str:
        """Return the configured API key or raise a clear configuration error."""

        if not self.api_key:
            raise ConfigurationError(
                "NVIDIA_API_KEY is required for real generation. "
                "Set it in the environment or use --dry-run."
            )
        return self.api_key


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None or value == "":
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ConfigurationError(f"Invalid boolean value for NVIDIA_THINKING: {value}")
