"""Role-based NVIDIA model profiles for the document agent harness."""

from __future__ import annotations

from dataclasses import dataclass

from legal_doc_agent.config import ConfigurationError, NvidiaConfig, env_value
from legal_doc_agent.nvidia import NvidiaClient


PLANNER_ROLE = "planner"
DRAFTER_ROLE = "drafter"
ANALYST_ROLE = "analyst"
REASONER_ROLE = "reasoner"
CODER_ROLE = "coder"
REVIEWER_ROLE = "reviewer"


@dataclass(frozen=True)
class AgentProfile:
    """A model profile optimized for one agent role."""

    role: str
    model: str
    temperature: float
    top_p: float
    max_tokens: int
    thinking: bool | None
    purpose: str
    enable_thinking: bool | None = None
    reasoning_budget: int | None = None
    stream: bool = False


DEFAULT_AGENT_PROFILES: dict[str, AgentProfile] = {
    PLANNER_ROLE: AgentProfile(
        role=PLANNER_ROLE,
        model="google/gemma-3n-e4b-it",
        temperature=0.2,
        top_p=0.7,
        max_tokens=2048,
        thinking=None,
        purpose="Plan sections, synthesize checklists, and keep output structure coherent.",
    ),
    DRAFTER_ROLE: AgentProfile(
        role=DRAFTER_ROLE,
        model="deepseek-ai/deepseek-v4-pro",
        temperature=1.0,
        top_p=0.95,
        max_tokens=16384,
        thinking=False,
        purpose="Draft long-form legal templates that need deeper clause coverage.",
    ),
    ANALYST_ROLE: AgentProfile(
        role=ANALYST_ROLE,
        model="minimaxai/minimax-m2.7",
        temperature=1.0,
        top_p=0.95,
        max_tokens=8192,
        thinking=None,
        purpose="Analyze optional documents, risk tradeoffs, and negotiation benchmarks.",
    ),
    REASONER_ROLE: AgentProfile(
        role=REASONER_ROLE,
        model="nvidia/nemotron-3-super-120b-a12b",
        temperature=1.0,
        top_p=0.95,
        max_tokens=16384,
        thinking=None,
        purpose="Run deep reasoning on cross-document dependencies and counsel-review risks.",
        enable_thinking=True,
        reasoning_budget=16384,
        stream=True,
    ),
    CODER_ROLE: AgentProfile(
        role=CODER_ROLE,
        model="qwen/qwen3-coder-480b-a35b-instruct",
        temperature=0.7,
        top_p=0.8,
        max_tokens=4096,
        thinking=None,
        purpose="Handle future code, automation, schema, and integration tasks.",
    ),
    REVIEWER_ROLE: AgentProfile(
        role=REVIEWER_ROLE,
        model="google/gemma-3n-e4b-it",
        temperature=0.2,
        top_p=0.7,
        max_tokens=2048,
        thinking=None,
        purpose=(
            "Final legal quality gate for completeness, internal consistency, "
            "citation support, formatting readiness, and counsel-review risks."
        ),
    ),
}


def load_agent_profiles_from_env() -> dict[str, AgentProfile]:
    """Load role profiles, allowing per-role environment overrides."""

    return {
        role: _profile_from_env(profile)
        for role, profile in DEFAULT_AGENT_PROFILES.items()
    }


def load_web_agent_profiles_from_env() -> dict[str, AgentProfile]:
    """Load latency-focused profiles for interactive web generation."""

    model = env_value("NVIDIA_WEB_MODEL", "google/gemma-3n-e4b-it") or "google/gemma-3n-e4b-it"
    default_max_tokens = int(env_value("NVIDIA_WEB_MAX_TOKENS", "1536") or "1536")
    drafter_max_tokens = int(
        env_value("NVIDIA_WEB_DRAFTER_MAX_TOKENS", "3072") or "3072"
    )
    profiles: dict[str, AgentProfile] = {}
    for role, profile in DEFAULT_AGENT_PROFILES.items():
        max_tokens = drafter_max_tokens if role == DRAFTER_ROLE else default_max_tokens
        profiles[role] = AgentProfile(
            role=role,
            model=model,
            temperature=min(profile.temperature, 0.7),
            top_p=min(profile.top_p, 0.8),
            max_tokens=max_tokens,
            thinking=None,
            purpose=profile.purpose,
            enable_thinking=None,
            reasoning_budget=None,
            stream=False,
        )
    return profiles


class NvidiaAgentRouter:
    """Route completion calls to the NVIDIA model configured for each role."""

    def __init__(
        self,
        *,
        base_config: NvidiaConfig,
        profiles: dict[str, AgentProfile] | None = None,
    ) -> None:
        self._base_config = base_config
        self._profiles = profiles or load_agent_profiles_from_env()

    @property
    def profiles(self) -> dict[str, AgentProfile]:
        """Return configured profiles by role."""

        return dict(self._profiles)

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        role: str | None = None,
    ) -> str:
        """Complete messages with the model assigned to the requested role."""

        selected_role = role or PLANNER_ROLE
        try:
            profile = self._profiles[selected_role]
        except KeyError as exc:
            known = ", ".join(sorted(self._profiles))
            raise ConfigurationError(
                f"Unknown agent role {selected_role!r}. Known roles: {known}"
            ) from exc

        client = NvidiaClient(
            self._base_config.with_overrides(
                model=profile.model,
                temperature=profile.temperature,
                top_p=profile.top_p,
                max_tokens=profile.max_tokens,
                thinking=profile.thinking,
                enable_thinking=profile.enable_thinking,
                reasoning_budget=profile.reasoning_budget,
                stream=profile.stream,
            )
        )
        return client.complete(messages)


def _profile_from_env(default: AgentProfile) -> AgentProfile:
    prefix = f"NVIDIA_{default.role.upper()}_"
    return AgentProfile(
        role=default.role,
        model=env_value(f"{prefix}MODEL", default.model) or default.model,
        temperature=float(
            env_value(f"{prefix}TEMPERATURE", str(default.temperature))
            or default.temperature
        ),
        top_p=float(env_value(f"{prefix}TOP_P", str(default.top_p)) or default.top_p),
        max_tokens=int(
            env_value(f"{prefix}MAX_TOKENS", str(default.max_tokens))
            or default.max_tokens
        ),
        thinking=_parse_role_thinking(env_value(f"{prefix}THINKING"), default.thinking),
        purpose=env_value(f"{prefix}PURPOSE", default.purpose) or default.purpose,
        enable_thinking=_parse_role_thinking(
            env_value(f"{prefix}ENABLE_THINKING"),
            default.enable_thinking,
        ),
        reasoning_budget=_parse_optional_int(
            env_value(f"{prefix}REASONING_BUDGET"),
            default.reasoning_budget,
        ),
        stream=_parse_role_stream(env_value(f"{prefix}STREAM"), default.stream),
    )


def _parse_role_thinking(value: str | None, default: bool | None) -> bool | None:
    if value is None or value == "":
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ConfigurationError(f"Invalid NVIDIA role thinking value: {value}")


def _parse_optional_int(value: str | None, default: int | None) -> int | None:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigurationError(f"Invalid NVIDIA role integer value: {value}") from exc


def _parse_role_stream(value: str | None, default: bool) -> bool:
    parsed = _parse_role_thinking(value, default)
    return bool(parsed)
