"""Latency-focused generation path for interactive web requests."""

from __future__ import annotations

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
    draft = _strip_markdown_fence(
        client.complete(_compact_package_messages(brief), role=DRAFTER_ROLE)
    )
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
                "Practical clauses/templates/checklists with bracketed placeholders.\n"
                "# Reviewer Quality Gate\n"
                "Blocking issues, required fixes, formatting checks, and counsel review notes.\n"
                "Keep the whole response under 900 words.\n\n"
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
