"""Agent harness orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from legal_doc_agent.docx_writer import DocumentSection, write_docx
from legal_doc_agent.prompts import build_generation_jobs, messages_for_job


class CompletionClient(Protocol):
    """Provider protocol used by the harness and tests."""

    def complete(self, messages: list[dict[str, str]]) -> str:
        """Generate assistant text from messages."""


@dataclass(frozen=True)
class Observation:
    """Deterministic step result for auditability."""

    status: str
    summary: str
    next_actions: list[str]
    artifacts: list[str]


@dataclass(frozen=True)
class AgentResult:
    """Final harness result."""

    output_path: Path
    artifact_dir: Path
    observations: list[Observation]


class LegalDocumentAgent:
    """Generate legal-document packages through bounded model calls."""

    def __init__(self, client: CompletionClient) -> None:
        self._client = client

    def generate(
        self,
        *,
        specification_path: Path,
        brief: str,
        output_path: Path,
        artifact_dir: Path,
    ) -> AgentResult:
        """Generate section markdown artifacts and a final Word document."""

        observations: list[Observation] = []
        specification = specification_path.read_text(encoding="utf-8")
        observations.append(
            Observation(
                status="success",
                summary=f"Loaded drafting specification from {specification_path}",
                next_actions=["Build bounded generation jobs"],
                artifacts=[str(specification_path)],
            )
        )

        jobs = build_generation_jobs(specification, brief)
        observations.append(
            Observation(
                status="success",
                summary=f"Built {len(jobs)} generation jobs",
                next_actions=["Call provider for each job"],
                artifacts=[],
            )
        )

        artifact_dir.mkdir(parents=True, exist_ok=True)
        sections: list[DocumentSection] = []
        for job in jobs:
            content = self._client.complete(messages_for_job(job))
            artifact_path = artifact_dir / f"{job.job_id}.md"
            artifact_path.write_text(content, encoding="utf-8")
            sections.append(DocumentSection(title=job.title, markdown=content))
            observations.append(
                Observation(
                    status="success",
                    summary=f"Generated {job.title}",
                    next_actions=["Continue to next section"],
                    artifacts=[str(artifact_path)],
                )
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_docx(
            title="Delaware C-Corp Post-Formation Legal Documentation Package",
            subtitle="AI software company and AI agent staffing platform",
            sections=sections,
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

        return AgentResult(
            output_path=output_path,
            artifact_dir=artifact_dir,
            observations=observations,
        )


class DryRunClient:
    """Offline client used for smoke tests and formatting checks."""

    def complete(self, messages: list[dict[str, str]]) -> str:
        user_prompt = messages[-1]["content"]
        title = "Generated Section"
        for line in user_prompt.splitlines():
            if line.startswith("Generate only PART"):
                title = line.rstrip(".")
                break
        return (
            f"# {title}\n\n"
            "This is dry-run placeholder content. It confirms that the harness, "
            "artifact writer, and DOCX renderer path are wired correctly.\n\n"
            "## Review Notice\n\n"
            "- Replace dry-run output with a real NVIDIA generation before use.\n"
            "- Have qualified counsel review all legal drafts.\n"
        )
