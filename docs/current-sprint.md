# Current Sprint

## Sprint Goal

Prepare the AI Reporting demo for Vercel preview deployment while keeping the local end-to-end workflow working.

The demo must support chat, uploads, SCF generation, generated downloads, and SCF evidence inspection without depending on local-only output paths.

## Sprint Backlog

### P0: Vercel API Entrypoint

Status: implemented.

Implemented:

- Added `api/index.py` as the Python serverless function entrypoint.
- Added `vercel.json` routes for `/`, `/api/*`, `/slack/*`, and `/data/*`.
- Added `.vercelignore` to exclude secrets and local runtime state.

### P0: Deploy Runtime Paths

Status: implemented.

Implemented:

- Added runtime path helpers.
- Local development continues to use the project directory.
- Vercel uses `/tmp/ai_reporting` for ephemeral processing.
- The bundled knowledge DB is copied to the runtime folder before mutation.

### P0: End-To-End Artifact Downloads

Status: implemented.

Implemented:

- `/api/generate` returns inline generated artifacts.
- The web app turns inline artifacts into browser download links.
- Evidence and mapping JSON can be read directly from the generation response.
- The SCF evidence inspector continues to work without fetching generated JSON from a local server path.

### P0: Deploy Health Check

Status: implemented.

Implemented:

- Added `/api/health`.
- Reports runtime write access, config readiness, knowledge DB availability, and model env status.

### P1: Production Durable Storage

Status: documented, not implemented.

Remaining:

- Move sessions and metadata to Postgres.
- Move uploads and generated files to private Blob storage.
- Add signed download URLs.
- Add authentication and tenant authorization.

## Definition Of Done

- Local tests pass.
- Local browser app still loads.
- `/api/health` works.
- `/api/generate` can return downloadable inline artifacts.
- Vercel config and docs exist.
- Production storage/auth gaps are clearly documented.
