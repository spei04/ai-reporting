# Session Files And Artifacts

## Purpose

Let users upload supporting files, preserve session context, and download generated outputs.

## Current Features

- Files can be attached to chat messages.
- Files can be uploaded directly from the sidebar upload panel.
- Supported file types:
  - `.xlsx`
  - `.csv`
  - `.docx`
  - `.pdf`
  - `.txt`
- Uploaded files are stored under `data/sessions/{session_id}`.
- Uploaded files are summarized and indexed into private knowledge context.
- Uploaded files are L3 context: they are retrieved for the active session when relevant, not loaded into the permanent prompt or global skill specs.
- Uploaded files return ingestion status: `indexed`, `partial`, or `failed`.
- Generated artifacts are stored under the same session.
- Disclosure completeness reviews are stored as generated JSON artifacts when the user asks whether uploaded disclosures are complete.
- The file library exposes:
  - uploaded files
  - generated outputs
  - shared ASC/SEC rules
- Artifact cards can be rendered directly in assistant responses.

## Current Output Types

- SCF workbook.
- SCF evidence JSON.
- Mapping review JSON.
- Normalized support JSON.
- Disclosure completeness review JSON.
