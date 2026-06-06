"""Online legal knowledge-base retrieval for Vercel generation."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from legal_doc_agent.legal_kb import LegalKnowledgeBase, SearchHit


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEB_KB_PATH = PROJECT_ROOT / "api" / "legal_kb.sqlite"
DEFAULT_WEB_KB_QUERY_PREFIX = (
    "83 election restricted stock tax filing Delaware board consent stockholder "
    "consent founder corporation certificate incorporation bylaws vesting "
    "intellectual property assignment"
)


def web_kb_path() -> Path:
    """Return the configured online legal KB path."""

    configured = os.getenv("LEGAL_KB_DB", "").strip()
    return Path(configured) if configured else DEFAULT_WEB_KB_PATH


def build_web_knowledge_context(
    brief: str,
    *,
    db_path: Path | None = None,
    limit: int = 6,
) -> str | None:
    """Retrieve citation support for a browser/Vercel generation request."""

    path = db_path or web_kb_path()
    if not path.exists():
        return None

    query = f"{DEFAULT_WEB_KB_QUERY_PREFIX} {brief.strip()}".strip()
    if not query:
        return None

    try:
        hits = LegalKnowledgeBase(path).search(query, limit=limit)
    except (sqlite3.Error, ValueError) as exc:
        print(f"web legal kb unavailable: {exc}", flush=True)
        return None
    if not hits:
        return None
    return _format_web_hits(hits)


def _format_web_hits(hits: list[SearchHit]) -> str:
    blocks = [
        "Retrieved legal authority support from the deployed SQLite FTS5 KB.",
        "Use these excerpts only as citation support. Do not cite authority that is not listed here.",
        "Flag any issue that still requires qualified counsel review.",
    ]
    for index, hit in enumerate(hits, start=1):
        excerpt = " ".join(hit.text.split())
        if len(excerpt) > 850:
            excerpt = excerpt[:847].rstrip() + "..."
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
