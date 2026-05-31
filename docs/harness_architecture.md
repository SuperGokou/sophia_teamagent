# Harness Architecture

## Goal

Generate a polished `.docx` package from:

1. A reusable drafting specification.
2. A user-provided company brief.
3. NVIDIA's OpenAI-compatible chat completion API.

## Agent Shape

This harness uses a hybrid pattern:

- ReAct-style orchestration in Python: validate inputs, divide the job into deterministic sections, collect artifacts, and recover from failures.
- Typed tool execution: the LLM only drafts content; Python handles API transport, file IO, markdown-to-DOCX conversion, and artifact logging.

## Action Space

The runtime keeps tools narrow and explicit:

- `load_spec`: read the long legal drafting specification.
- `build_generation_jobs`: turn the full request into bounded generation jobs.
- `complete`: call NVIDIA for one bounded job.
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

1. Part A required checklist.
2. Part B optional/recommended checklist.
3. Part C preparation materials.
4. Part D one required document template at a time.

This avoids asking the model for the entire legal package in one fragile response.
