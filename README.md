# Legal Doc Agent

A small Python harness for generating Word document packages from a user brief and a reusable drafting specification, using the DeepSeek OpenAI-compatible API.

The included default prompt is tuned for a Delaware C-Corp post-formation legal documentation package for an AI/SaaS startup. Generated output is drafting assistance only and should be reviewed by qualified counsel before use.

## Setup

```powershell
python -m pip install -e .
$env:DEEPSEEK_API_KEY = "your_deepseek_api_key"
```

DeepSeek's official docs list the OpenAI-compatible base URL as `https://api.deepseek.com`. The default model here is `deepseek-v4-pro`; override it with `DEEPSEEK_MODEL` or `--model`.

## Generate a Word Document

Create or edit `input/company_brief.md`, then run:

```powershell
python -m legal_doc_agent --brief-file input/company_brief.md --out outputs/post_formation_package.docx
```

You can also pass short input directly:

```powershell
python -m legal_doc_agent --brief-text "Company name: Example AI, Inc.; founders: Alice and Bob; 50/50 ownership." --out outputs/example.docx
```

For an offline smoke test without calling DeepSeek:

```powershell
python -m legal_doc_agent --dry-run --brief-file input/company_brief.md --out outputs/dry_run.docx
```

## Configuration

Environment variables:

- `DEEPSEEK_API_KEY`: required for real generation.
- `DEEPSEEK_BASE_URL`: defaults to `https://api.deepseek.com`.
- `DEEPSEEK_MODEL`: defaults to `deepseek-v4-pro`.
- `DEEPSEEK_TIMEOUT`: defaults to `120`.

CLI options override environment values.

## Test

```powershell
python -m unittest discover -s tests
```
