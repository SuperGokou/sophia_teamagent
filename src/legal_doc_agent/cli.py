"""Command-line interface for the legal document agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from legal_doc_agent.config import ConfigurationError, DeepSeekConfig
from legal_doc_agent.deepseek import DeepSeekClient, ProviderError
from legal_doc_agent.harness import DryRunClient, LegalDocumentAgent


DEFAULT_SPEC_PATH = Path("prompts/delaware_c_corp_post_formation.txt")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        brief = _load_brief(args)
        client = DryRunClient() if args.dry_run else DeepSeekClient(
            DeepSeekConfig.from_env(
                base_url=args.base_url,
                model=args.model,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )
        )
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
        description="Generate a Word legal-document package with DeepSeek.",
    )
    brief_group = parser.add_mutually_exclusive_group(required=False)
    brief_group.add_argument("--brief-file", type=Path, help="Path to a company brief.")
    brief_group.add_argument("--brief-text", help="Company brief text.")
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    parser.add_argument("--out", type=Path, default=Path("outputs/post_formation_package.docx"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("outputs/artifacts"))
    parser.add_argument("--base-url", help="DeepSeek-compatible base URL.")
    parser.add_argument("--model", help="DeepSeek model name.")
    parser.add_argument("--temperature", type=float, help="Sampling temperature.")
    parser.add_argument("--max-tokens", type=int, help="Max output tokens per section.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Create a placeholder DOCX without calling DeepSeek.",
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


if __name__ == "__main__":
    raise SystemExit(main())
