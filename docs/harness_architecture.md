# Harness Architecture

## Goal

Generate a polished `.docx` package from:

1. A reusable drafting specification.
2. A user-provided company brief.
3. NVIDIA's OpenAI-compatible chat completion API.
4. Optional retrieved legal-authority context from the local SQLite knowledge base.

## Agent Shape

This harness uses a hybrid pattern:

- ReAct-style orchestration in Python: validate inputs, divide the job into deterministic sections, collect artifacts, and recover from failures.
- Typed tool execution: the LLM only drafts content; Python handles API transport, file IO, markdown-to-DOCX conversion, and artifact logging.

## Action Space

The runtime keeps tools narrow and explicit:

- `load_spec`: read the long legal drafting specification.
- `search_legal_kb`: retrieve exact-citation and FTS5 authority snippets.
- `build_generation_jobs`: turn the full request into bounded generation jobs.
- `complete`: call NVIDIA for one bounded job through a role-specific agent profile.
- `write_docx`: convert completed sections into a Word document.
- `write_artifacts`: save markdown outputs for audit and re-runs.

## Observation Shape

Each step returns a deterministic observation:

```json
{
  "status": "success|warning|error",
  "summary": "one-line result",
  "next_actions": ["actionable follow-up"],
  "artifacts": ["paths or ids"]
}
```

## Recovery

- Missing API key: stop before network calls and explain `NVIDIA_API_KEY`.
- Provider HTTP error: include status code and response body preview.
- Empty model output: stop that job and report which section failed.
- DOCX write error: preserve generated markdown artifacts for manual recovery.

## Context Budget

The source specification is long, so the package is generated in sections:

1. Part A required checklist with the `planner` role.
2. Part B optional/recommended checklist with the `analyst` role.
3. Part C preparation materials with the `reasoner` role.
4. Part D one required document template at a time with the `drafter` role.

This avoids asking the model for the entire legal package in one fragile response.

## Legal Knowledge Base

The first-phase legal KB uses SQLite as the source of truth:

- `sources`: official source registry, including GovInfo, eCFR, Federal Register, and Congress.gov.
- `documents`: versioned legal documents with citation, jurisdiction, URL, effective date, and hash.
- `sections`: canonical legal text sections indexed by SQLite FTS5.
- `chunks`: retrieval chunks ready for a future embedding/vector index.
- `citations` and `updates`: citation graph and change tracking hooks.

The current CLI supports manual `ingest-text` for already retrieved authority text.
Official downloader/updater connectors should write through the same document,
section, and chunk APIs.

Retrieval is intentionally hybrid:

1. Exact citation lookup for authorities such as `15 U.S.C. 77a`.
2. SQLite FTS5 keyword retrieval for terms and definitions.
3. Future vector retrieval via `embedding_id` references in `chunks`.
4. Citation checking before an authority is used as support.

Obsidian export is a workspace view over the SQLite store, not the primary database.

## Model Roles

- `planner`: GPT OSS 120B for structure, coverage, and checklist planning.
- `drafter`: DeepSeek V4 Pro for long-form legal drafting and clause coverage.
- `analyst`: MiniMax M2.7 for risk tradeoffs and optional-document analysis.
- `reasoner`: Nemotron Super for cross-document dependencies and counsel-review risks.
- `coder`: Qwen Coder for future integration, schema, and automation work.
- `reviewer`: Gemma for short, low-cost sanity checks.
