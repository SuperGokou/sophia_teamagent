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
    model: str = "openai/gpt-oss-120b"
    timeout_seconds: float = 120.0
    temperature: float = 1.0
    top_p: float = 1.0
    max_tokens: int = 4096
    thinking: bool | None = None
    enable_thinking: bool | None = None
    reasoning_budget: int | None = None
    stream: bool = False

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
        enable_thinking: bool | None = None,
        reasoning_budget: int | None = None,
        stream: bool | None = None,
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
            top_p_value = float(os.getenv("NVIDIA_TOP_P", "1"))

        max_tokens_value = max_tokens
        if max_tokens_value is None:
            max_tokens_value = int(os.getenv("NVIDIA_MAX_TOKENS", "4096"))

        thinking_value = thinking
        if thinking_value is None:
            thinking_value = _parse_optional_bool(
                os.getenv("NVIDIA_THINKING"),
                "NVIDIA_THINKING",
            )

        enable_thinking_value = enable_thinking
        if enable_thinking_value is None:
            enable_thinking_value = _parse_optional_bool(
                os.getenv("NVIDIA_ENABLE_THINKING"),
                "NVIDIA_ENABLE_THINKING",
            )

        reasoning_budget_value = reasoning_budget
        if reasoning_budget_value is None:
            raw_reasoning_budget = os.getenv("NVIDIA_REASONING_BUDGET")
            reasoning_budget_value = (
                int(raw_reasoning_budget) if raw_reasoning_budget else None
            )

        stream_value = stream
        if stream_value is None:
            stream_value = (
                _parse_optional_bool(os.getenv("NVIDIA_STREAM"), "NVIDIA_STREAM")
                or False
            )

        return cls(
            api_key=api_key or os.getenv("NVIDIA_API_KEY"),
            base_url=(base_url or os.getenv("NVIDIA_BASE_URL") or cls.base_url).rstrip("/"),
            model=model or os.getenv("NVIDIA_MODEL") or cls.model,
            timeout_seconds=timeout_value,
            temperature=temperature_value,
            top_p=top_p_value,
            max_tokens=max_tokens_value,
            thinking=thinking_value,
            enable_thinking=enable_thinking_value,
            reasoning_budget=reasoning_budget_value,
            stream=stream_value,
        )

    def require_api_key(self) -> str:
        """Return the configured API key or raise a clear configuration error."""

        if not self.api_key:
            raise ConfigurationError(
                "NVIDIA_API_KEY is required for real generation. "
                "Set it in the environment or use --dry-run."
            )
        return self.api_key

    def with_overrides(
        self,
        *,
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        thinking: bool | None = None,
        enable_thinking: bool | None = None,
        reasoning_budget: int | None = None,
        stream: bool | None = None,
    ) -> "NvidiaConfig":
        """Return a role-specific config while preserving shared auth settings."""

        return NvidiaConfig(
            api_key=self.api_key,
            base_url=self.base_url,
            model=model or self.model,
            timeout_seconds=self.timeout_seconds,
            temperature=self.temperature if temperature is None else temperature,
            top_p=self.top_p if top_p is None else top_p,
            max_tokens=self.max_tokens if max_tokens is None else max_tokens,
            thinking=self.thinking if thinking is None else thinking,
            enable_thinking=(
                self.enable_thinking if enable_thinking is None else enable_thinking
            ),
            reasoning_budget=(
                self.reasoning_budget if reasoning_budget is None else reasoning_budget
            ),
            stream=self.stream if stream is None else stream,
        )


def _parse_optional_bool(value: str | None, name: str) -> bool | None:
    if value is None or value == "":
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ConfigurationError(f"Invalid boolean value for {name}: {value}")
