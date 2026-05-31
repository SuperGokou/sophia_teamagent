"""Command-line interface for the legal document agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from legal_doc_agent.agents import NvidiaAgentRouter, load_agent_profiles_from_env
from legal_doc_agent.config import ConfigurationError, NvidiaConfig
from legal_doc_agent.nvidia import NvidiaClient, ProviderError
from legal_doc_agent.harness import DryRunClient, LegalDocumentAgent


DEFAULT_SPEC_PATH = Path("prompts/delaware_c_corp_post_formation.txt")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.list_agents:
            _print_agent_profiles()
            return 0

        brief = _load_brief(args)
        if args.dry_run:
            client = DryRunClient()
        elif args.single_agent:
            client = NvidiaClient(
                NvidiaConfig.from_env(
                    base_url=args.base_url,
                    model=args.model,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    max_tokens=args.max_tokens,
                    thinking=args.thinking,
                    enable_thinking=args.enable_thinking,
                    reasoning_budget=args.reasoning_budget,
                    stream=args.stream,
                )
            )
        else:
            base_config = NvidiaConfig.from_env(base_url=args.base_url)
            client = NvidiaAgentRouter(base_config=base_config)
        agent = LegalDocumentAgent(client)
        result = agent.generate(
            specification_path=args.spec,
            brief=brief,
            output_path=args.out,
            artifact_dir=args.artifact_dir,
        )
    except (ConfigurationError, FileNotFoundError, ProviderError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {result.output_path}")
    print(f"Markdown artifacts: {result.artifact_dir}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a Word legal-document package with NVIDIA.",
    )
    brief_group = parser.add_mutually_exclusive_group(required=False)
    brief_group.add_argument("--brief-file", type=Path, help="Path to a company brief.")
    brief_group.add_argument("--brief-text", help="Company brief text.")
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    parser.add_argument("--out", type=Path, default=Path("outputs/post_formation_package.docx"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("outputs/artifacts"))
    parser.add_argument("--base-url", help="NVIDIA-compatible base URL.")
    parser.add_argument("--model", help="Single-agent NVIDIA model name.")
    parser.add_argument("--temperature", type=float, help="Single-agent sampling temperature.")
    parser.add_argument("--top-p", type=float, help="Single-agent nucleus sampling top_p.")
    parser.add_argument("--max-tokens", type=int, help="Single-agent max output tokens per section.")
    parser.add_argument(
        "--thinking",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable or disable NVIDIA chat_template_kwargs.thinking.",
    )
    parser.add_argument(
        "--enable-thinking",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable or disable NVIDIA chat_template_kwargs.enable_thinking.",
    )
    parser.add_argument(
        "--reasoning-budget",
        type=int,
        help="Single-agent NVIDIA reasoning_budget value.",
    )
    parser.add_argument(
        "--stream",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Request streaming completions and collect streamed content.",
    )
    parser.add_argument(
        "--single-agent",
        action="store_true",
        help="Use one NVIDIA model for every job instead of role-based routing.",
    )
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="Print configured role-based model profiles and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Create a placeholder DOCX without calling NVIDIA.",
    )
    return parser


def _load_brief(args: argparse.Namespace) -> str:
    if args.brief_file:
        brief = args.brief_file.read_text(encoding="utf-8")
    elif args.brief_text:
        brief = args.brief_text
    elif not sys.stdin.isatty():
        brief = sys.stdin.read()
    else:
        raise ValueError("Provide --brief-file, --brief-text, or pipe brief text on stdin.")

    if not brief.strip():
        raise ValueError("Company brief is empty.")
    return brief.strip()


def _print_agent_profiles() -> None:
    for role, profile in load_agent_profiles_from_env().items():
        thinking = "unset" if profile.thinking is None else str(profile.thinking).lower()
        enable_thinking = (
            "unset"
            if profile.enable_thinking is None
            else str(profile.enable_thinking).lower()
        )
        reasoning_budget = (
            "unset" if profile.reasoning_budget is None else str(profile.reasoning_budget)
        )
        print(
            f"{role}: model={profile.model}, temperature={profile.temperature}, "
            f"top_p={profile.top_p}, max_tokens={profile.max_tokens}, "
            f"thinking={thinking}, enable_thinking={enable_thinking}, "
            f"reasoning_budget={reasoning_budget}, stream={str(profile.stream).lower()}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
