# AI Reporting

First milestone implementation for deterministic Statement of Cash Flows generation from support data.

## What Exists Now

The current implementation is a local Python package and CLI that:

1. Reads an uploaded Q1 2026 support workbook.
2. Normalizes the uploaded workbook into the first standard support template.
3. Applies a learned source-cell map so expected support values can be found when rows/columns move inside an uploaded workbook.
4. Writes a reviewer-facing mapping review that shows required support items, matched uploaded locations, confidence, and review status.
5. Persists reviewer-approved mapping overrides in a company parser profile and applies them before automated matching.
6. Uses a versioned cash-flow template to generate:
   - `2. 26Q1 QTD`: detailed QTD cash-flow bridge.
   - `1. SCF`: presentation-level SCF summary.
   - `2a. 2026 YTD`: fixed YTD support formulas used by the summary.
7. Exports source evidence links for clickable value drill-downs, including the expected support cell and actual located uploaded-workbook cell.
8. Validates selected generated bridge values against the second tab in the development-only `answer.xlsx` golden workbook.

## Run

```bash
PYTHONPATH=src python -m ai_reporting.cli \
  --input "/Users/serenapei/Downloads/ai_reporting/reference/FS-4 26Q1 SCF - 3rd Consol.xlsx" \
  --template config/standard_q1_scf_template.json \
  --source-map config/source_cell_map_q1.json \
  --parser-profile config/company_parser_profile.json \
  --output-dir outputs/first_milestone \
  --answer "/Users/serenapei/Downloads/ai_reporting/reference/answer.xlsx"
```

Expected validation status:

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

## Test

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v
```

## View the Web Interface

Run the local upload-capable backend:

```bash
PYTHONPATH=src python -m ai_reporting.server
```

Open:

```text
http://127.0.0.1:8001/web/
```

OpenAI API configuration lives in `.env`. Add `OPENAI_API_KEY`, use `OPENAI_MODEL=auto` to let the backend try current available GPT models in order, or set `OPENAI_MODEL_CANDIDATES` to a comma-separated preferred list.

## Vercel Preview Deploy

The repository includes a Vercel preview-demo path:

- `api/index.py` exposes the Python backend as a Vercel function.
- `vercel.json` routes `/api/*` and `/slack/*` to the backend and `/` to the web app.
- `/api/health` reports runtime/config readiness.
- Generated SCF artifacts are returned inline so the browser can download files without relying on a persistent local output folder.

Before deploying, set Vercel environment variables from `.env.example`, especially:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_MODEL_CANDIDATES`
- `AI_REPORTING_PUBLIC_BASE_URL`

Deploy as a preview first:

```bash
vercel deploy . -y
```

After deploy, open:

```text
https://your-preview-url.vercel.app/api/health
```

Then test the full flow in the web app: chat, upload support workbook, generate SCF, download generated files, and click source trace rows.

The preview deployment is not yet a durable multi-user production system. Production still needs Postgres for sessions/metadata, private Blob storage for uploaded/generated files, authentication, signed downloads, and background jobs for large workbooks.

The UI can upload an `.xlsx` support workbook, run generation, and refresh:

- `outputs/first_milestone/generated_values.json`
- `outputs/first_milestone/evidence_links.json`
- `outputs/first_milestone/normalized_support.json`
- `outputs/first_milestone/workbook_profile.json`
- `outputs/first_milestone/mapping_review.json`
- `config/standard_q1_scf_template.json`
- `config/source_cell_map_q1.json`
- `config/company_parser_profile.json`

The workbook profile maps slightly different uploaded tab names to the standard support model. For example, `Balance Sheet` can resolve to canonical `BS`, and `Short-term Investments` can resolve to canonical `3. STI`.

The source-cell map learns formulas, row labels, column labels, and value types from the approved support workbook. During generation, the uploaded workbook is still the only workbook read for source values; the map only helps locate the intended support cell when the workbook layout shifts.

The Mapping Review tab shows the standard support requirements that the engine expects, the uploaded workbook location it matched, match confidence, and whether each item is matched, moved, missing, or needs review.

Reviewers can save a source-cell override from Mapping Review. Overrides are persisted in `config/company_parser_profile.json`, applied before automated matching, and generation reruns using the approved profile.

## Important Design Note

`answer.xlsx` is not a generation input and is not a production dependency. The engine generates output from the FS-4 support workbook plus checked-in template/config. `answer.xlsx` is read only after generation completes, and only by the development validation step that compares generated output to the second tab, `2. 26Q1 QTD`.

There is an automated guard test that fails if `generate()` attempts to open `answer.xlsx`.
