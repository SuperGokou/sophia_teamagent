"""Latency-focused generation path for interactive web requests."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from legal_doc_agent.agents import DRAFTER_ROLE
from legal_doc_agent.docx_writer import DocumentSection, write_docx
from legal_doc_agent.harness import CompletionClient, Observation


LONG_BRIEF_THRESHOLD_CHARS = 3500
MAX_ONLINE_BRIEF_CHARS = 2600


@dataclass(frozen=True)
class WebGenerationResult:
    """Generated web draft plus persisted artifacts."""

    output_path: Path
    artifact_dir: Path
    observations: list[Observation]
    generation_mode: str = "nvidia"


def generate_web_legal_package(
    *,
    client: CompletionClient,
    brief: str,
    output_path: Path,
    artifact_dir: Path,
    knowledge_context: str | None = None,
) -> WebGenerationResult:
    """Generate a compact legal package for browser and Vercel flows."""

    artifact_dir.mkdir(parents=True, exist_ok=True)
    observations: list[Observation] = []
    if knowledge_context:
        observations.append(
            Observation(
                status="success",
                summary="Loaded deployed SQLite FTS5 legal knowledge context",
                next_actions=["Use retrieved citations only as supplemental support"],
                artifacts=[],
            )
        )

    online_brief = _online_safe_brief(brief)
    if online_brief != brief.strip():
        observations.append(
            Observation(
                status="warning",
                summary="Compacted long user prompt for online generation stability",
                next_actions=["Split full template expansion into follow-up runs if needed"],
                artifacts=[],
            )
        )

    generation_mode = "nvidia"
    print("starting web job: compact_package", flush=True)
    try:
        raw_draft = client.complete(
            _compact_package_messages(online_brief, knowledge_context=knowledge_context),
            role=DRAFTER_ROLE,
        )
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
        try:
            raw_draft = client.complete(
                _short_package_retry_messages(
                    online_brief,
                    knowledge_context=knowledge_context,
                ),
                role=DRAFTER_ROLE,
            )
        except Exception as retry_exc:
            print(f"web compact package recovery after retry error: {retry_exc}", flush=True)
            observations.append(
                Observation(
                    status="warning",
                    summary="Provider timed out again; returned backend recovery package",
                    next_actions=["Retry later for provider-generated full drafting"],
                    artifacts=[],
                )
            )
            raw_draft = _provider_timeout_recovery_package(
                online_brief,
                knowledge_context=knowledge_context,
            )
            generation_mode = "timeout_recovery"

    draft = _append_retrieved_authorities_appendix(
        _ensure_complete_web_package(_strip_markdown_fence(raw_draft)),
        knowledge_context=knowledge_context,
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
        generation_mode=generation_mode,
    )


def _online_safe_brief(brief: str) -> str:
    text = brief.strip()
    if len(text) <= LONG_BRIEF_THRESHOLD_CHARS:
        return text

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    keep_patterns = (
        "company",
        "business",
        "jurisdiction",
        "founder",
        "ownership",
        "authorized shares",
        "allocation",
        "vesting",
        "required documents",
        "optional",
        "83(b)",
        "ai",
        "saas",
        "ip assignment",
        "board consent",
        "stockholder consent",
        "bylaws",
    )
    selected: list[str] = []
    for line in lines:
        normalized = line.lower()
        if any(pattern in normalized for pattern in keep_patterns):
            selected.append(line)
        if len("\n".join(selected)) > 1500:
            break

    digest_lines = [
        "ONLINE-SAFE REQUEST DIGEST",
        f"Original prompt length: {len(text)} characters.",
        "The user requested a post-formation Delaware C-Corporation legal package for an AI/SaaS startup.",
        "Do not re-expand the full source prompt. Generate a bounded Word-ready package that can finish inside the online provider timeout.",
        "Preserve key facts, checklist categories, major required documents, AI/SaaS requirements, citation appendix, and counsel-review warnings.",
        "If full law-firm-grade templates exceed the online limit, provide complete first-pass templates plus a clear expansion checklist.",
        "",
        "Key extracted facts and requirements:",
    ]
    digest_lines.extend(f"- {line}" for line in selected[:28])
    digest = "\n".join(digest_lines).strip()
    if len(digest) > MAX_ONLINE_BRIEF_CHARS:
        digest = digest[:MAX_ONLINE_BRIEF_CHARS].rsplit("\n", 1)[0].rstrip()
    return digest


def _compact_package_messages(
    brief: str,
    *,
    knowledge_context: str | None = None,
) -> list[dict[str, str]]:
    supplemental = _supplemental_knowledge_prompt(knowledge_context)
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
                f"{supplemental}"
                f"REQUEST:\n{brief}"
            ),
        },
    ]


def _short_package_retry_messages(
    brief: str,
    *,
    knowledge_context: str | None = None,
) -> list[dict[str, str]]:
    supplemental = _supplemental_knowledge_prompt(knowledge_context)
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
                f"{supplemental}"
                f"REQUEST:\n{brief}"
            ),
        },
    ]


def _supplemental_knowledge_prompt(knowledge_context: str | None) -> str:
    if not knowledge_context:
        return ""
    return (
        "SUPPLEMENTAL LEGAL KNOWLEDGE BASE CONTEXT:\n"
        f"{knowledge_context}\n\n"
        "Use this context only as retrieved authority support. Do not invent citations. "
        "If a cited issue is not supported by this context, mark it for counsel verification.\n\n"
    )


def _append_retrieved_authorities_appendix(
    markdown: str,
    *,
    knowledge_context: str | None,
) -> str:
    if not knowledge_context:
        return markdown
    if "# Retrieved Authority Context" in markdown:
        return markdown
    body = knowledge_context.strip()
    if not body:
        return markdown
    if "END OF PACKAGE" in markdown:
        markdown = markdown.replace("END OF PACKAGE", "").rstrip()
    return (
        f"{markdown}\n\n"
        "# Retrieved Authority Context\n\n"
        f"{body}\n\n"
        "END OF PACKAGE"
    ).strip()


def _provider_timeout_recovery_package(
    brief: str,
    *,
    knowledge_context: str | None,
) -> str:
    authority = (
        "\n\n# Retrieved Authority Context\n\n"
        f"{knowledge_context.strip()}\n"
        if knowledge_context
        else ""
    )
    return (
        "# NVIDIA Provider Timeout Recovery Package\n\n"
        "The online provider did not return a usable completion before the timeout. "
        "This backend recovery package preserves the requested legal-document workflow "
        "so the user can still download a Word file and continue review.\n\n"
        "# Request Digest\n\n"
        f"{brief}\n\n"
        "# Planner Summary\n\n"
        "Matter type: Delaware C-Corporation post-formation legal documentation package "
        "for an AI/SaaS startup with founder equity, governance, IP, tax, and commercial "
        "operations needs.\n\n"
        "# Required Document Checklist\n\n"
        "- Corporate Bylaws: internal governance, meetings, officers, notices, quorum, and board administration.\n"
        "- Initial Board Consent: approve officers, banking authority, stock issuances, agreements, and records.\n"
        "- Founder Stock Purchase Agreements: document founder shares, consideration, vesting, repurchase rights, and restrictions.\n"
        "- Stock Ledger and Cap Table: record authorized shares, issued shares, ownership, consideration, and transfer history.\n"
        "- IP Assignment and CIIAA: assign pre-existing and future company IP, confidentiality obligations, and invention disclosures.\n"
        "- 83(b) Election Instructions: flag deadline-sensitive restricted stock tax-election review.\n"
        "- Banking Authorization and Officer Appointment Resolutions: authorize signatories and corporate authority.\n\n"
        "# Preparation Materials Needed\n\n"
        "- Filed certificate of incorporation, Delaware file number, registered agent, company address, par value, and authorized shares.\n"
        "- Founder legal names, addresses, entity-holder details, share counts, purchase price, vesting schedule, and board roles.\n"
        "- Prior inventions, contractor relationships, customer data flows, SaaS product assumptions, AI agent use cases, and privacy/security posture.\n"
        "- Board composition, officer titles, bank signatories, initial approvals, capitalization records, and counsel/tax-review deadlines.\n\n"
        "# Draft Package\n\n"
        "## Initial Board Consent Template Skeleton\n\n"
        "RESOLVED, that the officers of the Company are authorized and directed to maintain "
        "the Company's books and records, issue founder shares subject to approved purchase "
        "agreements and vesting restrictions, approve the form of IP assignment and CIIAA, "
        "open bank accounts, appoint officers, and take related actions necessary for "
        "post-formation corporate organization, subject to qualified counsel review.\n\n"
        "## Founder Stock Purchase Agreement Template Skeleton\n\n"
        "The founder purchases [SHARES] shares of common stock at $[PRICE] per share, "
        "subject to a four-year vesting schedule with a one-year cliff and monthly vesting "
        "thereafter. Include company repurchase rights, transfer restrictions, tax-election "
        "notices, securities-law representations, IP/confidentiality cross-references, and "
        "signature blocks.\n\n"
        "## IP Assignment / CIIAA Template Skeleton\n\n"
        "Founder assigns to the Company all company-related inventions, works of authorship, "
        "software, models, prompts, workflows, agents, documentation, trade secrets, and "
        "related intellectual property, excluding disclosed prior inventions listed on a "
        "signed schedule.\n\n"
        "## AI and SaaS Operating Clauses\n\n"
        "Include customer-data handling assumptions, AI-output disclaimers, acceptable-use "
        "limits, automated-system limitations, confidentiality, security-policy references, "
        "API restrictions, subscription assumptions, and customer responsibility clauses.\n\n"
        "# Reviewer Quality Gate\n\n"
        "- Replace all bracketed blanks before execution.\n"
        "- Confirm Delaware statutory support, securities compliance, tax election timing, IP chain of title, and investor due-diligence expectations.\n"
        "- Have qualified counsel review enforceability, fiduciary approvals, stock issuance mechanics, and AI/SaaS commercial terms."
        f"{authority}\n\n"
        "END OF PACKAGE"
    )


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
