# Deployment

## Purpose

Prepare the demo for Vercel preview deployment while preserving the local development workflow.

## Current Features

- Vercel Python function entrypoint at `api/index.py`.
- Vercel routing config in `vercel.json`.
- Deploy ignore file excludes local runtime state and secrets.
- Runtime storage root switches automatically:
  - project folder locally
  - `/tmp/ai_reporting` on Vercel
- `/api/health` reports deploy readiness checks.
- `/api/generate` returns inline artifacts for browser-side downloads.
- The web app supports inline generated artifacts and still supports local file URLs.

## Notes

This is a deployable preview-demo path. Durable production deployment still needs Postgres for sessions/knowledge metadata and private Blob storage for uploaded/generated files.
