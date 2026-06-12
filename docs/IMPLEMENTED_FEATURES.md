# Implemented Features

Status: First build milestone started.

## Implemented

### Project Scaffold

- Added a Python package under `src/ai_reporting`.
- Added CLI entry point: `python -m ai_reporting.cli`.
- Added `pyproject.toml` and `requirements.txt`.
- Added standard-library `unittest` coverage for the first milestone.

### Workbook Ingestion

- Loads the uploaded support workbook in two modes:
  - `data_only=True` for source values.
  - `data_only=False` for formulas.
- Captures workbook-level sheet metadata through `SourceWorkbook.summary()`.
- Provides read-only access to source cell values and formulas.

### Standard Support Normalization

- Added first-pass standard support sections:
  - `balance_sheet`
  - `income_statement`
  - `investments`
  - `fixed_assets`
  - `leases`
  - `sbc_equity`
  - `business_combinations`
  - `repurchases`
  - `reserves`
  - `other_investing`
- Maps expected source tabs into normalized support items.
- Exports `normalized_support.json`.
- Flags missing expected source sheets as missing support items.
- Added workbook profiling to resolve slightly different uploaded sheet names to standard canonical sheet names.
- Exports `workbook_profile.json`.
- Current alias examples:
  - `Balance Sheet` -> `BS`
  - `Income Statement` -> `IS`
  - `Short-term Investments` -> `3. STI`
  - `Property and Equipment` -> `6. Fixed Assets`
  - `Equity Rollforward` -> `8. Equity RF`
- Added a learned source-cell map at `config/source_cell_map_q1.json`.
- The map is derived from the approved support workbook and template, not from `answer.xlsx`.
- Source-cell lookup can now resolve moved rows/columns using exact formula matches, row labels, column labels, and value types.
- Added `config/company_parser_profile.json` for reviewer-approved source-cell overrides.
- Manual parser overrides take priority over learned source-cell matching during generation.
- Generates `mapping_review.json`, a reviewer-facing standard support requirements report with:
  - canonical required support sheet/cell
  - actual uploaded workbook sheet/cell
  - match status
  - confidence
  - row and column labels
  - value and formula context
  - reviewer note
- Mapping Review can now persist an override and rerun generation using the approved parser profile.

### Versioned Cash Flow Template

- Added `config/standard_q1_scf_template.json`.
- The template is seeded from the development answer workbook and contains the formulas/layout for:
  - `1. SCF`
  - `2. 26Q1 QTD`
  - `2a. 2026 YTD`
- Runtime generation consumes this template as configuration.

### Deterministic Formula Evaluation

- Added a small deterministic formula evaluator for the formulas used in the Q1 SCF fixture.
- Supports:
  - same-sheet cell references
  - quoted and unquoted cross-sheet references
  - `SUM(...)`
  - `ROUND(...)`
  - arithmetic expressions
  - recursive dependencies across generated sheets
- Treats non-numeric referenced text as zero for numeric validation.

### Cash Flow Generation

- Generates a workbook at `outputs/first_milestone/generated_scf_q1_2026.xlsx`.
- Generates evaluated output values at `outputs/first_milestone/generated_values.json`.
- Generates mapping review output at `outputs/first_milestone/mapping_review.json`.
- Generates:
  - `2. 26Q1 QTD` detailed bridge
  - `1. SCF` presentation summary
  - fixed `2a. 2026 YTD` formulas
- Preserves formulas in the generated workbook so Excel can recalculate and users can inspect the workpaper.
- Adds an `Evidence Index` sheet to the generated workbook.
- Adds hyperlinks and comments from evidenced generated cells back to the matching `Evidence Index` row.
- Evidence index rows include output sheet/cell, output value, formula, dependencies, source locations, rule reference, and review status.

### Evidence Links

- Captures formula dependencies during evaluation.
- Exports `evidence_links.json`.
- Evidence links connect generated output cells to source/generated dependency cells.
- Source workbook dependency details include both the canonical support reference and the actual uploaded-workbook cell found by the source-cell map.
- Each generated output evidence link is tagged with `ASC 230` as the initial rule reference.

### Golden Validation

- Added validation against the second tab in the development-only `answer.xlsx`.
- Validation compares selected high-value cells from `2. 26Q1 QTD`.
- Validation runs after generation completes.
- Added a no-cheating guard test that fails if generation attempts to read `answer.xlsx`.
- Current status: passing with no differences.

### Web Interface

- Added a static local web interface under `web/`.
- Added a local upload-capable backend at `python -m ai_reporting.server`.
- Replaced the first workbench interface with a chat-first reporting assistant UI.
- The new homepage includes:
  - simple reporting assistant greeting
  - centered message composer
  - file attachment chips
  - suggested reporting prompts
  - light/dark mode toggle
  - subtle marble-inspired visual texture
- Added a left-side vertical icon rail.
- Added a sliding file library panel opened from the folder icon.
- The file library includes tabs for:
  - uploaded files from the current session
  - generated output files from the current session
  - shared ASC and SEC rule PDFs
- The rule library supports ASC/SEC filtering and exposes downloadable links to the source PDFs in `data/raw`.
- Added `/api/session-library` to serve session uploads, generated artifacts, and shared rule documents to the web UI.
- Added conversation rendering for user and assistant messages.
- Added visible assistant work-log/progress steps for generation tasks.
- Added mock assistant responses for SEC filing, contract booking, source trace, CSV, and general reporting prompts while the live model provider is not yet configured.
- Added downloadable artifact cards in assistant responses and in a generated-files drawer.
- Added server-side chat sessions under `data/sessions/{session_id}`.
- Uploaded chat files are saved to the active session and summarized into structured context.
- Chat messages are persisted in the active session.
- Non-SCF chat messages now call the backend `/api/chat` endpoint instead of using only frontend mock responses.
- Backend chat requests assemble four context layers:
  - permanent reporting system prompt
  - retrieved ASC/SEC rule context
  - session-specific uploads, messages, and artifacts
  - user question
- Added OpenAI provider adapter that reads `OPENAI_API_KEY`, `OPENAI_MODEL`, and `OPENAI_MODEL_CANDIDATES` from `.env`.
- If no OpenAI key is configured, the backend returns a local preview response that still exercises session context and rule retrieval.
- Added ASC/SEC retrieval over the local reference folders with lazy PDF chunk extraction into `data/knowledge`.
- Added SQLite knowledge database at `data/reporting_knowledge.db`.
- Ingested the shared static ASC/SEC rule corpus from `data/raw`.
- Current static knowledge database contains 68 global rule documents, 11,225 rule chunks, and 11,234 graph edges.
- Global rules are stored separately from user-private uploads:
  - `global_documents`
  - `global_rule_chunks`
  - `global_rule_edges`
  - `user_documents`
  - `user_document_chunks`
  - `user_document_edges`
- User-uploaded chat files are now ingested into private session-scoped knowledge tables as well as filesystem session storage.
- SCF support workbook uploads are also ingested into private session-scoped knowledge when generation is tied to a session.
- Added deterministic response formatting so model answers are rendered as concise, human-readable summaries with key points, rule support tags, and next-step guidance instead of raw markdown.
- The chat interface can now call the existing deterministic SCF engine when the user attaches an `.xlsx` support workbook and asks for an SCF/cash-flow draft.
- SCF chat generation returns artifact cards for:
  - generated SCF workbook
  - evidence links JSON
  - mapping review JSON
  - normalized support JSON
- The generated response summarizes the parsed file, generated outputs, source evidence count, and mapping review status.
- The generated response now includes a compact source trace preview for representative output cells.
- Previous workbench functionality, preserved in implementation history but no longer exposed as the primary UI, included:
  - period/status dashboard
  - `SCF Summary` table
  - `Detailed Bridge` table
  - `Mapping Review` table
  - `Normalized Support` table
  - evidence side panel
- Users can upload an `.xlsx` support workbook from the browser and regenerate the standardized SCF artifacts.
- Uploaded workbooks are parsed through the workbook profile and learned source-cell map, so the first build can tolerate sheet-name variation and selected row/column movement.
- The underlying mapping review artifact still contains `Matched`, `Moved`, `Missing`, `Review`, and `Unmapped` parser statuses with confidence scores and reviewer notes.
- Parser-profile overrides are still supported by the backend endpoint, but the override review UI needs to be reintroduced in the chat/evidence workflow.
- The previous value-click evidence panel supported:
  - selected sheet/cell
  - generated value
  - formula from the standard cash-flow template
  - linked dependencies from `evidence_links.json`
  - actual located workbook cells when they differ from canonical source references
  - initial `ASC 230` rule support
  - related normalized support items when available
- The new chat UI exposes source linkage through citations and support labels for ordinary Q&A, while generation workflows expose downloadable evidence artifacts. The next evidence milestone should reintroduce clickable value traces inside the chat UI and add workbook-level evidence hyperlinks.

## Verified

Command run:

```bash
PYTHONPATH=src /Users/serenapei/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Result:

```text
Ran 22 tests
OK
```

CLI run:

```bash
PYTHONPATH=src /Users/serenapei/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m ai_reporting.cli \
  --input /Users/serenapei/Downloads/ai_reporting/reference/FS-4\ 26Q1\ SCF\ -\ 3rd\ Consol.xlsx \
  --template config/standard_q1_scf_template.json \
  --source-map config/source_cell_map_q1.json \
  --parser-profile config/company_parser_profile.json \
  --output-dir outputs/first_milestone \
  --answer /Users/serenapei/Downloads/ai_reporting/reference/answer.xlsx
```

Result:

```json
{
  "golden_validation": {
    "status": "passed",
    "answer_workbook_tab": "2. 26Q1 QTD",
    "note": "answer.xlsx is read only after generation completes",
    "differences": []
  }
}
```

Upload API verification:

```bash
curl -s -F 'workbook=@/Users/serenapei/Downloads/ai_reporting/reference/FS-4 26Q1 SCF - 3rd Consol.xlsx' \
  http://127.0.0.1:8001/api/generate
```

Result:

```json
{
  "status": "generated",
  "golden_validation": null
}
```

Web UI verification:

- Started the local upload-capable backend.
- Opened `http://127.0.0.1:8001/web/`.
- Verified the redesigned chat homepage loads with:
  - assistant greeting
  - composer
  - attachment control
  - suggested prompts
  - generated-files drawer
- Sent a mock SEC filing prompt and confirmed the assistant renders user message, progress steps, and a response.
- Toggled from dark mode to light mode and confirmed the theme persisted in page state.
- Checked browser console logs for errors and warnings; none were reported.
- Verified the SCF generation API path with the reference support workbook and confirmed it returned generated workbook, evidence links, mapping review, and normalized support artifacts.
- Verified `/api/sessions` creates a filesystem-backed session.
- Verified `/api/chat` retrieves reporting rule context and sends a live request to OpenAI when `OPENAI_API_KEY` is configured.
- Verified `/api/chat` returns citations from the retrieved ASC/SEC context pack.
- Verified `/api/chat` returns a structured `display` object for clean UI rendering.
- Verified the OpenAI provider returns live GPT answers with `used_live_model: true`.
- Verified `data/reporting_knowledge.db` retrieves ASC 230 chunks for cash-flow presentation queries.
- Verified user-uploaded text is ingested into private `user_document_chunks` using local-preview mode without sending private upload content to the external model.
- Added a sidebar upload panel with a dedicated upload icon, drag-and-drop/select-file support, and immediate session/private-knowledge ingestion through `/api/uploads` without triggering a model response.
- Added first Slack integration endpoints for OAuth install, slash commands, Events API handling, Slack request-signature verification, Slack-file ingestion into private session context, and persistent Slack conversation-to-reporting-session mapping.
- Added `docs/integration-roadmap.md` with the planned sequence for Slack approvals, company file systems, ERP/accounting systems, data warehouses, filing tools, contract systems, ticketing workflows, and MCP-based connectors.
- Switched the live model provider from Claude to OpenAI's Responses API. `OPENAI_MODEL=auto` now tries available/current GPT models, beginning with `gpt-5.4-mini`, and `OPENAI_MODEL_CANDIDATES` can override the ordered list.
- Added a temporary deterministic amortization-schedule smoke test to verify the chat pipeline can ask for missing inputs and return a downloadable Excel artifact. This is not a product feature.
- Added a backend reporting skill router. Categorized reporting queries receive selected-skill context in the model call; uncategorized queries fall back to a normal GPT call without any skill context.
- Added `features/` documentation with separate markdown files for the current web app, chat/model provider, reporting skills, SCF generation, knowledge base, session files/artifacts, and Slack features.
- Added support-state labeling for reporting chat answers:
  - `Source backed`
  - `Partially supported`
  - `No source found`
- Ordinary reporting Q&A responses no longer show downloadable output cards. Downloadable outputs are reserved for generation workflows that produce files, such as SCF workbooks and evidence artifacts.
- ASC/SEC rule-context retrieval and display are now gated to reporting workflows that need rule support, so generic chatbot responses stay clean.
- Added response formatting safeguards so visible summaries and next steps are capitalized, cleaned of leftover markdown/list punctuation, and end as complete sentences.
- Added structured source citations for reporting answers, including source type, citation label, title, excerpt, path, score, and source number.
- Added a source details drawer for citation cards so users can inspect source type, citation, title, excerpt, file name, retrieval score, and answer context without creating downloads.
- Added upload ingestion status metadata for session uploads so users can see whether files were indexed, partially indexed, or failed.
- Added chat-side SCF evidence inspection. Source trace preview rows now open a drawer with output value, formula, source workbook cells, generated dependencies, rule reference, and review status in table form.
- Added Vercel preview deployment readiness:
  - Python function entrypoint at `api/index.py`
  - `vercel.json` routing
  - `.vercelignore`
  - runtime path handling for `/tmp/ai_reporting` on Vercel
  - `/api/health`
  - inline generated artifacts for browser-side downloads
  - frontend support for inline artifacts and evidence inspection without local output URLs

## Current Limitations

- The standard support normalization is still a first-pass mapper. It identifies expected tabs and representative support items, and the engine can resolve selected moved cells, but it does not yet fully parse every support schedule into a row-level canonical schema.
- The formula evaluator intentionally supports the formula subset needed by the Q1 SCF fixture. It is not a full Excel calculation engine.
- The generated workbook stores formulas, but cached Excel formula results are not written into formula cells because `openpyxl` does not calculate formulas.
- Rule support is currently tagged at the initial `ASC 230` level. Paragraph-level ASC citations still need to be curated.
- The web UI now triggers workbook upload/generation, but there is not yet authentication, upload history, or multi-period job tracking.
- The chat UI displays generated artifact links, summary status, a compact source-trace preview, and value-level evidence inspection for generated SCF outputs.
- The downloaded workbook now includes an `Evidence Index` sheet and output-cell hyperlinks/comments. The evidence format still needs paragraph-level rule citations and reviewer approval metadata.
- Live GPT responses are enabled when `OPENAI_API_KEY` is configured. Without an OpenAI key, the frontend falls back to local preview responses unless the SCF engine path is triggered.
- The standard cash-flow template is checked-in config. Runtime generation does not read `answer.xlsx`, but template generalization still needs to evolve from the current Q1 fixture into a broader reusable template authoring workflow.
- The learned source-cell map currently covers source references used by the first Q1 template. Parser-profile overrides are now persisted, but there is not yet a full onboarding workflow for arbitrary support packages.
- The Vercel preview demo can run end to end, but durable production deployment still needs Postgres-backed sessions/knowledge metadata, private Blob storage, authentication, signed downloads, and background processing for large workbooks.

## Next Implementation Step

Add paragraph-level rule citations and reviewer approval metadata to the SCF evidence inspector.
