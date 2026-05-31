"""Prompt construction for bounded document generation jobs."""

from __future__ import annotations

from dataclasses import dataclass

from legal_doc_agent.agents import DRAFTER_ROLE, PLANNER_ROLE


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


@dataclass(frozen=True)
class GenerationJob:
    """A bounded model generation task."""

    job_id: str
    title: str
    prompt: str
    agent_role: str


def build_generation_jobs(specification: str, brief: str) -> list[GenerationJob]:
    """Split the package into bounded generation jobs."""

    base_context = f"""SOURCE SPECIFICATION:
{specification}

USER COMPANY BRIEF:
{brief}
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
            agent_role=PLANNER_ROLE,
            prompt=f"""{base_context}

Generate only PART B from the source specification.
Include every optional/recommended-document checklist field requested by the source.
Do not generate PART A, C, or D in this response.
""",
        ),
        GenerationJob(
            job_id="part_c_preparation_materials",
            title="PART C - Preparation Materials Needed For Each Document",
            agent_role=PLANNER_ROLE,
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


def messages_for_job(job: GenerationJob) -> list[dict[str, str]]:
    """Convert a generation job into chat messages."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": job.prompt},
    ]
