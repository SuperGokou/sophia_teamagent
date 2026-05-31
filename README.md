# Legal Doc Agent

A small Python harness for generating Word document packages from a user brief and a reusable drafting specification, using NVIDIA's OpenAI-compatible API.

The included default prompt is tuned for a Delaware C-Corp post-formation legal documentation package for an AI/SaaS startup. Generated output is drafting assistance only and should be reviewed by qualified counsel before use.

## Setup

```powershell
python -m pip install -e .
$env:NVIDIA_API_KEY = "your_nvidia_api_key"
```

The default NVIDIA OpenAI-compatible base URL is `https://integrate.api.nvidia.com/v1`. By default the harness uses a role-based multi-agent router; use `--single-agent` if you want one model for every job.

Do not hardcode API keys in source files. Put them in your environment or a local `.env` file that remains ignored by git.

## Generate a Word Document

Create or edit `input/company_brief.md`, then run:

```powershell
python -m legal_doc_agent --brief-file input/company_brief.md --out outputs/post_formation_package.docx
```

You can also pass short input directly:

```powershell
python -m legal_doc_agent --brief-text "Company name: Example AI, Inc.; founders: Alice and Bob; 50/50 ownership." --out outputs/example.docx
```

For an offline smoke test without calling NVIDIA:

```powershell
python -m legal_doc_agent --dry-run --brief-file input/company_brief.md --out outputs/dry_run.docx
```

## Configuration

Environment variables:

- `NVIDIA_API_KEY`: required for real generation.
- `NVIDIA_BASE_URL`: defaults to `https://integrate.api.nvidia.com/v1`.
- `NVIDIA_MODEL`: defaults to `openai/gpt-oss-120b`.
- `NVIDIA_TEMPERATURE`: defaults to `1`.
- `NVIDIA_TOP_P`: defaults to `1`.
- `NVIDIA_MAX_TOKENS`: defaults to `4096`.
- `NVIDIA_THINKING`: optional. When unset, no `chat_template_kwargs` is sent. Set `false` for models that support `chat_template_kwargs.thinking=false`.
- `NVIDIA_TIMEOUT`: defaults to `120`.

Single-agent CLI options override the single-agent values above.

## Multi-Agent Profiles

Default role routing:

- `planner`: `openai/gpt-oss-120b`, for checklists, structure, and package planning.
- `drafter`: `deepseek-ai/deepseek-v4-pro`, for long legal templates and clause-heavy drafting.
- `coder`: `qwen/qwen3-coder-480b-a35b-instruct`, reserved for future code/schema/automation tasks.
- `reviewer`: `google/gemma-3n-e2b-it`, reserved for short sanity checks and lightweight review.

Override any role with environment variables like:

```powershell
$env:NVIDIA_PLANNER_MODEL = "openai/gpt-oss-120b"
$env:NVIDIA_DRAFTER_MODEL = "deepseek-ai/deepseek-v4-pro"
$env:NVIDIA_DRAFTER_THINKING = "false"
```

Inspect the active profile map without making an API call:

```powershell
python -m legal_doc_agent --list-agents
```

## Test

```powershell
python -m unittest discover -s tests
```
