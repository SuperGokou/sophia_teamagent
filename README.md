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

The role-based flow always runs a final `reviewer` quality gate after planning,
analysis, reasoning, and drafting. The reviewer writes
`final_reviewer_quality_gate.md` and the same report is appended to the final
Word document so the user can see blocking issues, required fixes, layout checks,
and counsel-review notes before using the package.

## Google Docs Editor Workflow

Google Doc editing requires Google Docs and Drive credentials with access to the
target document:

```powershell
python -m pip install -e ".[google]"
```

One-time Google setup:

1. In Google Cloud Console, create or select a project.
2. Enable both Google Docs API and Google Drive API.
3. Configure the OAuth consent screen for your own Google account.
4. Create an OAuth Client ID with application type `Desktop app`.
5. Download the client JSON to `credentials/google_oauth_client.json`.

The formatter checks the Drive `canEdit` capability before making changes. If the
link is not editable by the active credentials, the app must stop and ask the
user to open Google Doc sharing and grant Editor permission. The app never tries
to bypass sharing permissions.

Check access:

```powershell
python -m legal_doc_agent google-doc check "https://docs.google.com/document/d/.../edit"
```

Apply the standard legal layout:

```powershell
python -m legal_doc_agent google-doc format "https://docs.google.com/document/d/.../edit"
```

Replace the document body with generated draft text and apply legal layout:

```powershell
python -m legal_doc_agent google-doc write "https://docs.google.com/document/d/.../edit" --text-file outputs/draft.txt
```

Run the local OAuth service that the web UI can call:

```powershell
python -m legal_doc_agent google-doc serve --port 8765
```

On first run, Google opens a browser consent page. Sign in with the same account
that has Editor access to the target document. The local token is saved under
`credentials/google_token.json`, which is ignored by git.

When this service is running, the UI's `Multi Agent` flow will attempt to call:

```text
POST http://127.0.0.1:8765/google-doc/write
```

If the service is not running, the UI still exposes `Copy draft` and local
`.docx` download as fallbacks.

When editor access is confirmed, the formatter can apply a standard legal layout:
1 inch margins, Times New Roman 11 pt body text, 115% line spacing, and consistent
paragraph spacing for legal-document readability.

## Legal Knowledge Base MVP

The local legal knowledge base is a SQLite + FTS5 foundation for retrieval-augmented drafting. It is intentionally scoped as a first phase, not a claim that the app has already mirrored all U.S. law.

Initialize the database and seed first-phase official source definitions:

```powershell
python -m legal_doc_agent kb init --db data/legal_kb.sqlite --seed-sources
python -m legal_doc_agent kb sources --db data/legal_kb.sqlite
```

The seeded source registry covers the recommended MVP connectors:

- GovInfo U.S. Code and public-law material
- eCFR current federal regulations
- Federal Register recent rules and notices
- Congress.gov public/private law metadata

Search and citation-check local authority:

```powershell
python -m legal_doc_agent kb ingest-text --db data/legal_kb.sqlite --source-key govinfo-uscode --citation "15 U.S.C. 77a" --title "Definitions" --url "https://www.govinfo.gov/" --text-file input/authority.txt --heading "Definitions"
python -m legal_doc_agent kb search "Delaware stockholder consent" --db data/legal_kb.sqlite
python -m legal_doc_agent kb check-citation "15 U.S.C. 77a" --term issuer --db data/legal_kb.sqlite
```

Inject retrieved authority context into Word generation:

```powershell
python -m legal_doc_agent --brief-file input/company_brief.md --kb-db data/legal_kb.sqlite --kb-query "post formation founder equity" --out outputs/post_formation_package.docx
```

Export a human-readable Obsidian-style workspace from the SQLite source of truth:

```powershell
python -m legal_doc_agent kb export-obsidian --db data/legal_kb.sqlite --out outputs/obsidian --matter-name "Example AI Inc"
```

## UI Preview

The local UI lives in `ui/` and can be opened directly:

```powershell
start ui\index.html
```

For a local preview server:

```powershell
cd ui
python -m http.server 5173 --bind 127.0.0.1
```

The UI console includes three delivery paths:

- Open a Google Doc edit link directly in a new browser tab.
- Create a Chrome handoff request for a Google Docs editor/formatter bridge.
- Generate a local `.docx` draft in the browser when cloud editing is not ready.

When a Google Doc edit link is present, the `Multi Agent` button also creates
the Chrome handoff request immediately. The document will only be modified when
a Chrome bridge/plugin or the Google Docs OAuth formatter service is running;
the static UI cannot bypass Google sharing permissions by itself.

## Configuration

Environment variables:

- `NVIDIA_API_KEY`: required for real generation.
- `NVIDIA_BASE_URL`: defaults to `https://integrate.api.nvidia.com/v1`.
- `NVIDIA_MODEL`: defaults to `openai/gpt-oss-120b`.
- `NVIDIA_TEMPERATURE`: defaults to `1`.
- `NVIDIA_TOP_P`: defaults to `1`.
- `NVIDIA_MAX_TOKENS`: defaults to `4096`.
- `NVIDIA_THINKING`: optional. When unset, no `chat_template_kwargs` is sent. Set `false` for models that support `chat_template_kwargs.thinking=false`.
- `NVIDIA_ENABLE_THINKING`: optional. Sends `chat_template_kwargs.enable_thinking` for models such as Nemotron.
- `NVIDIA_REASONING_BUDGET`: optional provider reasoning budget.
- `NVIDIA_STREAM`: optional. Set `true` to request streaming completions and collect streamed content.
- `NVIDIA_TIMEOUT`: defaults to `120`.

Single-agent CLI options override the single-agent values above.

## Multi-Agent Profiles

Default role routing:

- `planner`: `openai/gpt-oss-120b`, for checklists, structure, and package planning.
- `drafter`: `deepseek-ai/deepseek-v4-pro`, for long legal templates and clause-heavy drafting.
- `analyst`: `minimaxai/minimax-m2.7`, for optional-document analysis, risk tradeoffs, and benchmark-style synthesis.
- `reasoner`: `nvidia/nemotron-3-super-120b-a12b`, for deep thinking on preparation materials, cross-document dependencies, and counsel-review risks.
- `coder`: `qwen/qwen3-coder-480b-a35b-instruct`, reserved for future code/schema/automation tasks.
- `reviewer`: `openai/gpt-oss-120b`, for the final legal quality gate, consistency checks, citation-support review, layout readiness, and counsel-review risk notes.

Override any role with environment variables like:

```powershell
$env:NVIDIA_PLANNER_MODEL = "openai/gpt-oss-120b"
$env:NVIDIA_DRAFTER_MODEL = "deepseek-ai/deepseek-v4-pro"
$env:NVIDIA_ANALYST_MODEL = "minimaxai/minimax-m2.7"
$env:NVIDIA_REASONER_MODEL = "nvidia/nemotron-3-super-120b-a12b"
$env:NVIDIA_REASONER_ENABLE_THINKING = "true"
$env:NVIDIA_REASONER_REASONING_BUDGET = "16384"
$env:NVIDIA_REASONER_STREAM = "true"
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
