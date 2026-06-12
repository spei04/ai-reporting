# Vercel Deploy Readiness

## Demo Goal

Deploy a working preview demo where a reporting user can:

- Open the chatbot interface.
- Ask reporting questions.
- Upload session files.
- Upload a support workbook and generate SCF outputs.
- Download the generated workbook and evidence files.
- Inspect SCF evidence in the browser.

## Implemented For Deploy Demo

- Added `api/index.py` as the Vercel Python function entrypoint.
- Added `vercel.json` for routing:
  - `/` to the web app.
  - `/api/*` to the Python backend.
  - `/slack/*` to the Python backend.
- Added `.vercelignore` to exclude local generated files, uploads, sessions, and secrets.
- Added `/api/health` for deploy smoke checks.
- Added runtime path handling:
  - local development writes under the project folder.
  - Vercel writes under `/tmp/ai_reporting`.
- Added runtime copy of the bundled knowledge DB so the deploy demo can query and index without mutating the read-only bundle.
- Added inline generated artifacts to `/api/generate` responses so the browser can download files without relying on durable server-side local paths.
- Updated the web app to use inline artifacts for downloads and evidence inspection when present.

## Required Vercel Environment Variables

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_MODEL_CANDIDATES`
- `AI_REPORTING_PUBLIC_BASE_URL`

Slack preview/prod variables:

- `SLACK_CLIENT_ID`
- `SLACK_CLIENT_SECRET`
- `SLACK_SIGNING_SECRET`
- `SLACK_BOT_TOKEN`
- `SLACK_REDIRECT_URI`
- `SLACK_SCOPES`
- `SLACK_ALLOWED_TEAM_IDS`
- `SLACK_ALLOW_UNSIGNED_DEV=false`

## Preview Smoke Test

After deploy:

1. Open `/api/health`.
2. Confirm:
   - `status` is `ok`.
   - `runtime_writable` is `true`.
   - `template_ready` is `true`.
   - `source_map_ready` is `true`.
   - `parser_profile_ready` is `true`.
3. Open `/web/`.
4. Ask a normal question and confirm no download cards appear.
5. Ask an ASC/SEC question and confirm source citations appear only when retrieved.
6. Upload a support workbook and ask to draft the SCF.
7. Confirm the response includes:
   - generated workbook download
   - evidence links download
   - mapping review download
   - normalized support download
   - clickable SCF evidence preview rows

## Production Gap

The Vercel demo is deployable and end-to-end for a preview, but it is not yet a durable multi-user production system.

Before production:

- Move sessions, messages, artifacts, and user/private knowledge metadata to Postgres.
- Move uploaded and generated files to private Blob storage.
- Add authentication and tenant authorization.
- Add signed artifact download endpoints.
- Add background job processing for large SCF workbooks.
- Add file size limits, malware scanning, retention policy, and audit logs.
