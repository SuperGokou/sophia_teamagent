"""Command-line interface for the legal document agent."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from legal_doc_agent.agents import NvidiaAgentRouter, load_agent_profiles_from_env
from legal_doc_agent.config import ConfigurationError, NvidiaConfig
from legal_doc_agent.nvidia import NvidiaClient, ProviderError
from legal_doc_agent.harness import DryRunClient, LegalDocumentAgent
from legal_doc_agent.google_docs import (
    GoogleDocPermissionError,
    build_google_docs_formatter,
    extract_google_doc_id,
)
from legal_doc_agent.legal_kb import FIRST_PHASE_CONNECTORS, LegalKnowledgeBase, SearchHit


DEFAULT_SPEC_PATH = Path("prompts/delaware_c_corp_post_formation.txt")


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "kb":
        return _kb_main(argv[1:])
    if argv and argv[0] == "google-doc":
        return _google_doc_main(argv[1:])

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
        knowledge_context = _load_knowledge_context(args)
        agent = LegalDocumentAgent(client)
        result = agent.generate(
            specification_path=args.spec,
            brief=brief,
            output_path=args.out,
            artifact_dir=args.artifact_dir,
            knowledge_context=knowledge_context,
        )
    except (ConfigurationError, FileNotFoundError, ProviderError, ValueError, sqlite3.Error) as exc:
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
    parser.add_argument("--kb-db", type=Path, help="SQLite legal knowledge base path.")
    parser.add_argument("--kb-query", help="Search query for supplemental legal authority context.")
    parser.add_argument("--kb-citation", help="Exact citation to retrieve from the legal KB.")
    parser.add_argument(
        "--kb-limit",
        type=int,
        default=6,
        help="Maximum legal KB search hits to inject into generation prompts.",
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


def _load_knowledge_context(args: argparse.Namespace) -> str | None:
    if not args.kb_db:
        if args.kb_query or args.kb_citation:
            raise ValueError("Provide --kb-db when using --kb-query or --kb-citation.")
        return None
    if not args.kb_query and not args.kb_citation:
        return None

    kb = LegalKnowledgeBase(args.kb_db)
    query = args.kb_query or args.kb_citation or ""
    hits = kb.search(query, citation=args.kb_citation, limit=args.kb_limit)
    if not hits:
        return "No local legal authority hits were found. Do not cite the local KB."
    return _format_kb_hits(hits)


def _format_kb_hits(hits: list[SearchHit]) -> str:
    blocks: list[str] = []
    for index, hit in enumerate(hits, start=1):
        excerpt = " ".join(hit.text.split())
        if len(excerpt) > 900:
            excerpt = excerpt[:897].rstrip() + "..."
        blocks.append(
            "\n".join(
                [
                    f"[{index}] {hit.citation} - {hit.heading}",
                    f"source: {hit.source_key}",
                    f"retrieval_mode: {hit.retrieval_mode}",
                    f"version_date: {hit.version_date or 'unknown'}",
                    f"effective_date: {hit.effective_date or 'unknown'}",
                    f"url: {hit.url}",
                    f"excerpt: {excerpt}",
                ]
            )
        )
    return "\n\n".join(blocks)


def _kb_main(argv: list[str]) -> int:
    parser = _build_kb_parser()
    args = parser.parse_args(argv)
    try:
        kb = LegalKnowledgeBase(args.db)
        if args.command == "init":
            kb.initialize()
            print(f"Initialized {args.db}")
            if args.seed_sources:
                sources = kb.seed_connector_sources()
                print(f"Seeded {len(sources)} official source definitions")
            return 0
        if args.command == "seed-sources":
            kb.initialize()
            sources = kb.seed_connector_sources()
            for source in sources:
                print(f"{source.key}\t{source.name}\t{source.official_level}")
            return 0
        if args.command == "sources":
            return _kb_print_sources(kb)
        if args.command == "ingest-text":
            kb.initialize()
            kb.seed_connector_sources()
            text = args.text_file.read_text(encoding="utf-8").strip()
            if not text:
                raise ValueError(f"Text file is empty: {args.text_file}")
            document = kb.upsert_document(
                source_key=args.source_key,
                citation=args.citation,
                title=args.title,
                jurisdiction=args.jurisdiction,
                doc_type=args.doc_type,
                effective_date=args.effective_date,
                version_date=args.version_date,
                url=args.url,
            )
            section = kb.upsert_section(
                document_id=document.id,
                citation=args.citation,
                heading=args.heading,
                text=text,
                path=args.section_path or args.citation,
                order_index=args.order_index,
            )
            chunk_id = kb.add_chunk(
                section_id=section.id,
                chunk_text=text,
                token_count=args.token_count or len(text.split()),
            )
            print(
                f"Ingested {args.citation} as document {document.id}, "
                f"section {section.id}, chunk {chunk_id}"
            )
            return 0
        if args.command == "search":
            hits = kb.search(args.query, citation=args.citation, limit=args.limit)
            print(_format_kb_hits(hits) if hits else "No hits")
            return 0
        if args.command == "check-citation":
            check = kb.check_citation(args.citation, required_terms=args.term, limit=args.limit)
            print(f"citation: {check.citation}")
            print(f"supported: {str(check.supported).lower()}")
            if check.missing_terms:
                print("missing_terms: " + ", ".join(check.missing_terms))
            if check.hits:
                print(_format_kb_hits(list(check.hits)))
            return 0 if check.supported else 2
        if args.command == "export-obsidian":
            base = kb.export_obsidian(args.out, matter_name=args.matter_name)
            print(f"Wrote Obsidian vault notes under {base}")
            return 0
        parser.error("unknown kb command")
    except (sqlite3.Error, ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1


def _google_doc_main(argv: list[str]) -> int:
    parser = _build_google_doc_parser()
    args = parser.parse_args(argv)
    try:
        extract_google_doc_id(args.url)
        formatter = build_google_docs_formatter(
            credentials_path=args.credentials,
            token_path=args.token,
        )
        if args.command == "check":
            check = formatter.check_editor_access(args.url)
            print(f"document_id: {check.document_id}")
            if check.title:
                print(f"title: {check.title}")
            print(f"can_edit: {str(check.can_edit).lower()}")
            print(f"message: {check.message}")
            if check.next_actions:
                print("next_actions:")
                for action in check.next_actions:
                    print(f"- {action}")
            return 0 if check.can_edit else 2
        if args.command == "format":
            result = formatter.apply_legal_layout(args.url)
            print(f"document_id: {result.document_id}")
            if result.title:
                print(f"title: {result.title}")
            print(f"requests_sent: {result.requests_sent}")
            print(result.summary)
            return 0
        parser.error("unknown google-doc command")
    except (RuntimeError, FileNotFoundError, ValueError, GoogleDocPermissionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1


def _build_kb_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the local legal knowledge base.")
    parser.add_argument("--db", type=Path, default=Path("data/legal_kb.sqlite"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create the SQLite schema.")
    _add_kb_db_override(init)
    init.add_argument("--seed-sources", action="store_true")

    seed_sources = subparsers.add_parser(
        "seed-sources", help="Insert first-phase official source definitions."
    )
    _add_kb_db_override(seed_sources)

    sources = subparsers.add_parser("sources", help="List configured sources.")
    _add_kb_db_override(sources)

    ingest = subparsers.add_parser("ingest-text", help="Ingest one text file as authority.")
    _add_kb_db_override(ingest)
    ingest.add_argument("--source-key", required=True)
    ingest.add_argument("--citation", required=True)
    ingest.add_argument("--title", required=True)
    ingest.add_argument("--jurisdiction", default="US-Federal")
    ingest.add_argument("--doc-type", default="authority")
    ingest.add_argument("--url", required=True)
    ingest.add_argument("--text-file", type=Path, required=True)
    ingest.add_argument("--heading", default="Text")
    ingest.add_argument("--section-path")
    ingest.add_argument("--order-index", type=int, default=1)
    ingest.add_argument("--version-date")
    ingest.add_argument("--effective-date")
    ingest.add_argument("--token-count", type=int)

    search = subparsers.add_parser("search", help="Search sections with FTS5 and citation matching.")
    _add_kb_db_override(search)
    search.add_argument("query")
    search.add_argument("--citation")
    search.add_argument("--limit", type=int, default=8)

    check = subparsers.add_parser("check-citation", help="Verify a citation exists and has terms.")
    _add_kb_db_override(check)
    check.add_argument("citation")
    check.add_argument("--term", action="append", default=[])
    check.add_argument("--limit", type=int, default=5)

    export = subparsers.add_parser("export-obsidian", help="Export Markdown notes.")
    _add_kb_db_override(export)
    export.add_argument("--out", type=Path, default=Path("outputs/obsidian"))
    export.add_argument("--matter-name", default="Example Matter")

    return parser


def _build_google_doc_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check or format an editable Google Doc.")
    parser.add_argument(
        "--credentials",
        type=Path,
        default=Path("credentials/google_oauth_client.json"),
        help="Google OAuth desktop-client credentials JSON.",
    )
    parser.add_argument(
        "--token",
        type=Path,
        default=Path("credentials/google_token.json"),
        help="Local OAuth token cache path. Keep this file out of git.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="Verify Editor permission.")
    check.add_argument("url")
    format_doc = subparsers.add_parser(
        "format",
        help="Apply standard legal-document layout.",
    )
    format_doc.add_argument("url")
    return parser


def _add_kb_db_override(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--db",
        type=Path,
        dest="db",
        default=argparse.SUPPRESS,
        help="SQLite legal knowledge base path.",
    )


def _kb_print_sources(kb: LegalKnowledgeBase) -> int:
    kb.initialize()
    kb.seed_connector_sources()
    for connector in FIRST_PHASE_CONNECTORS:
        print(
            f"{connector.key}\t{connector.name}\t{connector.jurisdiction}\t"
            f"{connector.official_level}\t{connector.source_url}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
