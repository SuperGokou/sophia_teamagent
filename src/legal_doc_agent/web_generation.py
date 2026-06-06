"""Latency-focused generation path for interactive web requests."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from legal_doc_agent.agents import DRAFTER_ROLE
from legal_doc_agent.docx_writer import DocumentSection, write_docx
from legal_doc_agent.harness import CompletionClient, Observation


@dataclass(frozen=True)
class WebGenerationResult:
    """Generated web draft plus persisted artifacts."""

    output_path: Path
    artifact_dir: Path
    observations: list[Observation]


def generate_web_legal_package(
    *,
    client: CompletionClient,
    brief: str,
    output_path: Path,
    artifact_dir: Path,
) -> WebGenerationResult:
    """Generate a compact legal package for browser and Vercel flows."""

    artifact_dir.mkdir(parents=True, exist_ok=True)
    observations: list[Observation] = []

    print("starting web job: compact_package", flush=True)
    try:
        raw_draft = client.complete(_compact_package_messages(brief), role=DRAFTER_ROLE)
    except Exception as exc:
        print(f"web compact package retry after provider error: {exc}", flush=True)
        observations.append(
            Observation(
                status="warning",
                summary="Provider timed out during full web package generation",
                next_actions=["Retry with a shorter package prompt"],
                artifacts=[],
            )
        )
        raw_draft = client.complete(
            _short_package_retry_messages(brief),
            role=DRAFTER_ROLE,
        )

    draft = _ensure_complete_web_package(_strip_markdown_fence(raw_draft))
    draft_path = artifact_dir / "web_drafter_package.md"
    draft_path.write_text(draft, encoding="utf-8")
    print("finished web job: compact_package", flush=True)
    observations.append(
        Observation(
            status="success",
            summary="Generated compact web legal document package",
            next_actions=["Write Word document"],
            artifacts=[str(draft_path)],
        )
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_docx(
        title="Web Legal Document Package",
        subtitle="NVIDIA-assisted draft for qualified counsel review",
        sections=[
            DocumentSection(title="NVIDIA Web Legal Package", markdown=draft),
        ],
        output_path=output_path,
    )
    observations.append(
        Observation(
            status="success",
            summary=f"Wrote Word document to {output_path}",
            next_actions=["Review generated document with qualified counsel"],
            artifacts=[str(output_path)],
        )
    )

    return WebGenerationResult(
        output_path=output_path,
        artifact_dir=artifact_dir,
        observations=observations,
    )


def _compact_package_messages(brief: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are a concise legal-document drafting assistant. Drafting "
                "support only; do not provide final legal advice. Keep responses "
                "short enough for an interactive web app."
            ),
        },
        {
            "role": "user",
            "content": (
                "Generate one compact Markdown legal package for the request below. "
                "Do not wrap the response in a Markdown code fence. "
                "Use exactly these sections:\n"
                "# Planner Summary\n"
                "Matter type, missing facts, required documents, delivery order.\n"
                "# Draft Package\n"
                "Complete practical clauses/templates/checklists with bracketed placeholders. "
                "Do not stop mid-item; close every list item and section.\n"
                "# Reviewer Quality Gate\n"
                "Blocking issues, required fixes, formatting checks, and counsel review notes.\n"
                "Target 1,600-2,400 words. Finish with the exact line: END OF PACKAGE.\n\n"
                f"REQUEST:\n{brief}"
            ),
        },
    ]


def _short_package_retry_messages(brief: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are a concise legal-document drafting assistant. Drafting "
                "support only; do not provide final legal advice. Prioritize "
                "returning a complete Word-ready package quickly."
            ),
        },
        {
            "role": "user",
            "content": (
                "The previous provider request timed out. Generate a shorter, complete "
                "Markdown legal package for the request below. Do not wrap the response "
                "in a Markdown code fence. Use exactly these sections:\n"
                "# Planner Summary\n"
                "Matter type, missing facts, required documents, delivery order.\n"
                "# Draft Package\n"
                "Practical clauses/templates/checklists with bracketed placeholders. "
                "Use concise clauses and close every section.\n"
                "# Reviewer Quality Gate\n"
                "Blocking issues, required fixes, formatting checks, and counsel review notes.\n"
                "Target 700-1,100 words. Finish with the exact line: END OF PACKAGE.\n\n"
                f"REQUEST:\n{brief}"
            ),
        },
    ]


def _strip_markdown_fence(markdown: str) -> str:
    text = markdown.strip()
    if not text.startswith("```"):
        return markdown.strip()
    lines = text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _ensure_complete_web_package(markdown: str) -> str:
    text = _drop_likely_truncated_tail(markdown.strip())
    if "# Reviewer Quality Gate" in text and "END OF PACKAGE" in text:
        return text

    completion_sections: list[str] = []
    if "# Reviewer Quality Gate" not in text:
        completion_sections.append(
            "\n\n# Reviewer Quality Gate\n\n"
            "## Completion Safeguard\n"
            "The online generator detected that the provider response may have ended before "
            "the final review package was complete. Treat this package as a drafting aid, "
            "not final legal advice.\n\n"
            "## Blocking Issues\n"
            "- Confirm the entity name, jurisdiction, file number, founders, equity split, "
            "vesting schedule, IP ownership, and signature authority.\n"
            "- Replace all bracketed placeholders before signature, filing, investor review, "
            "or Google Doc delivery.\n"
            "- Have qualified counsel review enforceability, tax timing, securities law, "
            "employment/IP assignment, and Delaware corporate requirements.\n\n"
            "## Required Fixes\n"
            "- Complete missing schedules, exhibits, signature blocks, dates, addresses, "
            "share counts, consideration, and board approvals.\n"
            "- Check all cross-references, numbering, defined terms, and attachment labels.\n"
            "- Confirm that the Word document uses legal-document formatting before delivery.\n\n"
            "## Formatting Checks\n"
            "- Use consistent headings, numbered clauses, page breaks, signature blocks, and "
            "Times New Roman legal-document styling.\n"
            "- Keep checklists separate from operative clauses so counsel can review quickly.\n\n"
            "## Counsel Review Notes\n"
            "Counsel should review the package against the company's charter, cap table, "
            "board approvals, tax deadlines, IP chain of title, and investor diligence needs."
        )
    if "END OF PACKAGE" not in text:
        completion_sections.append("\n\nEND OF PACKAGE")
    return f"{text}{''.join(completion_sections)}".strip()


def _drop_likely_truncated_tail(markdown: str) -> str:
    lines = markdown.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""

    tail = lines[-1].strip()
    if _looks_like_truncated_tail(tail):
        lines.pop()
    return "\n".join(lines).strip()


def _looks_like_truncated_tail(line: str) -> bool:
    if re_match := re.search(r"(Scope of|Prep:|Purpose:|Risk if missing:|Who signs:)$", line):
        return bool(re_match)
    return len(line) > 40 and line[-1] not in ".。;；:：)]}"
