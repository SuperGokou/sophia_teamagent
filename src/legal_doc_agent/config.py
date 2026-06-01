"""Configuration helpers for the NVIDIA provider."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing."""


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOTENV_PATH = PROJECT_ROOT / ".env"
_DOTENV_CACHE: dict[Path, dict[str, str]] = {}


def env_value(name: str, default: str | None = None) -> str | None:
    """Read config from process environment first, then project .env."""

    value = os.getenv(name)
    if value not in {None, ""}:
        return value
    return _load_dotenv_values().get(name, default)


@dataclass(frozen=True)
class NvidiaConfig:
    """Runtime settings for NVIDIA's OpenAI-compatible API."""

    api_key: str | None
    base_url: str = "https://integrate.api.nvidia.com/v1"
    model: str = "minimaxai/minimax-m2.7"
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
        """Build configuration from explicit values, environment, then .env."""

        timeout_value = timeout_seconds
        if timeout_value is None:
            timeout_value = float(env_value("NVIDIA_TIMEOUT", "120") or "120")

        temperature_value = temperature
        if temperature_value is None:
            temperature_value = float(env_value("NVIDIA_TEMPERATURE", "1") or "1")

        top_p_value = top_p
        if top_p_value is None:
            top_p_value = float(env_value("NVIDIA_TOP_P", "1") or "1")

        max_tokens_value = max_tokens
        if max_tokens_value is None:
            max_tokens_value = int(env_value("NVIDIA_MAX_TOKENS", "4096") or "4096")

        thinking_value = thinking
        if thinking_value is None:
            thinking_value = _parse_optional_bool(
                env_value("NVIDIA_THINKING"),
                "NVIDIA_THINKING",
            )

        enable_thinking_value = enable_thinking
        if enable_thinking_value is None:
            enable_thinking_value = _parse_optional_bool(
                env_value("NVIDIA_ENABLE_THINKING"),
                "NVIDIA_ENABLE_THINKING",
            )

        reasoning_budget_value = reasoning_budget
        if reasoning_budget_value is None:
            raw_reasoning_budget = env_value("NVIDIA_REASONING_BUDGET")
            reasoning_budget_value = (
                int(raw_reasoning_budget) if raw_reasoning_budget else None
            )

        stream_value = stream
        if stream_value is None:
            stream_value = (
                _parse_optional_bool(env_value("NVIDIA_STREAM"), "NVIDIA_STREAM")
                or False
            )

        return cls(
            api_key=api_key or env_value("NVIDIA_API_KEY"),
            base_url=(base_url or env_value("NVIDIA_BASE_URL") or cls.base_url).rstrip("/"),
            model=model or env_value("NVIDIA_MODEL") or cls.model,
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


def _load_dotenv_values(path: Path = DEFAULT_DOTENV_PATH) -> dict[str, str]:
    resolved = path.resolve()
    if resolved in _DOTENV_CACHE:
        return _DOTENV_CACHE[resolved]
    try:
        lines = resolved.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        values: dict[str, str] = {}
        _DOTENV_CACHE[resolved] = values
        return values

    values = {}
    for line in lines:
        parsed = _parse_dotenv_line(line)
        if parsed is None:
            continue
        key, value = parsed
        values[key] = value
    _DOTENV_CACHE[resolved] = values
    return values


def _parse_dotenv_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped.removeprefix("export ").strip()
    if "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key:
        return None
    return key, _normalize_dotenv_value(value)


def _normalize_dotenv_value(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"'}:
        return stripped[1:-1]
    if " #" in stripped:
        stripped = stripped.split(" #", 1)[0].rstrip()
    return stripped
