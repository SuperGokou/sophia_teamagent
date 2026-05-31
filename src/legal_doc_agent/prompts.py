"""Prompt construction for bounded document generation jobs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from legal_doc_agent.agents import (
    ANALYST_ROLE,
    DRAFTER_ROLE,
    PLANNER_ROLE,
    REASONER_ROLE,
    REVIEWER_ROLE,
)


SYSTEM_PROMPT = """You are a careful legal-document drafting assistant.
Draft detailed professional text, but do not claim that the output is final legal advice.
Generated documents must be reviewed by qualified counsel before use.
Follow the user's source specification exactly unless it conflicts with this review notice.
Use clear Markdown headings, numbered clauses, and bullet lists. Avoid markdown tables unless
row/column comparison is materially clearer than prose.
"""


REQUIRED_TEMPLATE_DOCUMENTS = [
    "Corporate Bylaws",
    "Initial Board Consent",
    "Founder Stock Purchase Agreement",
    "Stock Ledger",
    "Initial Capitalization Table",
    "Intellectual Property Assignment Agreement",
    "Confidential Information and Invention Assignment Agreement",
    "Section 83(b) Election Instructions and Cover Package",
    "Banking Authorization",
    "Officer Appointment Resolutions",
    "Founder Vesting and Company Repurchase Rights Schedule",
]

FINAL_REVIEW_MAX_CHARS = 24000


class GeneratedSection(Protocol):
    """Generated text contract used by the final reviewer prompt."""

    title: str
    markdown: str


@dataclass(frozen=True)
class GenerationJob:
    """A bounded model generation task."""

    job_id: str
    title: str
    prompt: str
    agent_role: str


def build_generation_jobs(
    specification: str,
    brief: str,
    knowledge_context: str | None = None,
) -> list[GenerationJob]:
    """Split the package into bounded generation jobs."""

    supplemental = ""
    if knowledge_context:
        supplemental = f"""
SUPPLEMENTAL LEGAL KNOWLEDGE BASE CONTEXT:
{knowledge_context}

Use this context only as retrieved authority support. Do not invent citations.
If the context is incomplete or does not support a claim, say that qualified counsel
should verify the issue instead of overstating the legal conclusion.
"""

    base_context = f"""SOURCE SPECIFICATION:
{specification}

USER COMPANY BRIEF:
{brief}
{supplemental}
"""

    jobs = [
        GenerationJob(
            job_id="part_a_required_checklist",
            title="PART A - Required Document Checklist",
            agent_role=PLANNER_ROLE,
            prompt=f"""{base_context}

Generate only PART A from the source specification.
Include every required-document checklist field requested by the source.
Do not generate PART B, C, or D in this response.
""",
        ),
        GenerationJob(
            job_id="part_b_optional_recommended_checklist",
            title="PART B - Optional / Recommended Document Checklist",
            agent_role=ANALYST_ROLE,
            prompt=f"""{base_context}

Generate only PART B from the source specification.
Include every optional/recommended-document checklist field requested by the source.
Do not generate PART A, C, or D in this response.
""",
        ),
        GenerationJob(
            job_id="part_c_preparation_materials",
            title="PART C - Preparation Materials Needed For Each Document",
            agent_role=REASONER_ROLE,
            prompt=f"""{base_context}

Generate only PART C from the source specification.
Organize preparation materials by document and include required plus optional/recommended documents.
Do not generate PART A, B, or D in this response.
""",
        ),
    ]

    for index, document_name in enumerate(REQUIRED_TEMPLATE_DOCUMENTS, start=1):
        slug = (
            document_name.lower()
            .replace("section ", "")
            .replace("(", "")
            .replace(")", "")
            .replace("/", " ")
            .replace("-", " ")
            .replace("&", "and")
        )
        slug = "_".join(part for part in slug.split() if part)
        jobs.append(
            GenerationJob(
                job_id=f"part_d_{index:02d}_{slug}",
                title=f"PART D - Complete Template: {document_name}",
                agent_role=DRAFTER_ROLE,
                prompt=f"""{base_context}

Generate only the PART D complete template for this required document:
{document_name}

For this required document template, include:
1. Purpose brief
2. Key legal risks brief
3. Drafting notes brief
4. Complete professional template

Keep the template internally consistent with the company profile and user company brief.
Do not generate templates for other documents in this response.
""",
            )
        )

    return jobs


def build_final_review_job(
    specification: str,
    brief: str,
    generated_sections: list[GeneratedSection],
    knowledge_context: str | None = None,
) -> GenerationJob:
    """Build the mandatory final legal quality review job."""

    section_blocks: list[str] = []
    remaining_chars = FINAL_REVIEW_MAX_CHARS
    for section in generated_sections:
        header = f"\n\n## Generated Section: {section.title}\n"
        body = section.markdown.strip()
        available = remaining_chars - len(header)
        if available <= 0:
            break
        if len(body) > available:
            body = body[: max(0, available - 160)].rstrip()
            body += "\n\n[Truncated for final review prompt budget.]"
        section_blocks.append(header + body)
        remaining_chars -= len(header) + len(body)

    supplemental = ""
    if knowledge_context:
        supplemental = f"""
SUPPLEMENTAL LEGAL KNOWLEDGE BASE CONTEXT:
{knowledge_context}

Use this context only to verify whether generated legal statements are supported.
Flag unsupported citations or unsupported claims instead of filling gaps by assumption.
"""

    return GenerationJob(
        job_id="final_reviewer_quality_gate",
        title="FINAL REVIEW - Legal Document Quality Gate",
        agent_role=REVIEWER_ROLE,
        prompt=f"""SOURCE SPECIFICATION:
{specification}

USER COMPANY BRIEF:
{brief}
{supplemental}

GENERATED PACKAGE FOR FINAL REVIEW:
{''.join(section_blocks)}

You are the final reviewer agent. Audit the complete package before Word / Google Doc delivery.
Your job is quality control, not new drafting. Check:
1. Whether every required document and preparation item requested by the source specification appears.
2. Internal consistency of entity names, founders, ownership, dates, signature blocks, defined terms, and cross-references.
3. Whether legal statements and citations are supported by the provided knowledge context.
4. Whether placeholders are obvious, necessary, and labeled for user/counsel completion.
5. Whether the output is ready for professional legal-document layout.
6. Issues that qualified counsel must verify before use.

Return only this Markdown structure:
# Final Reviewer Quality Gate
## Approval Status
Use PASS if the package is ready for counsel review and document export, or NEEDS REVISION if blockers remain.
## Blocking Issues
List missing or contradictory items. Write "None found" if none are found.
## Required Fixes Before Use
List concrete fixes the drafting agents must make before the package is used.
## Formatting/Layout Checks
List Word and Google Doc layout requirements: margins, font, headings, numbering, signature pages, page breaks.
## Counsel Review Notes
List legal questions that must be reviewed by qualified counsel. Do not claim the document is final legal advice.
""",
    )


def messages_for_job(job: GenerationJob) -> list[dict[str, str]]:
    """Convert a generation job into chat messages."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": job.prompt},
    ]
