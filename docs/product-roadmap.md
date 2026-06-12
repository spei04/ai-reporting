# Product Roadmap

## Product Thesis

Financial reporting teams do not need a generic chatbot. They need a trusted reporting intelligence layer that understands company context, cites authoritative sources, reconciles evidence to numbers, preserves audit trails, and turns recurring reporting work into defensible workflows.

## MVP Scope

The MVP should prove:

> A reporting manager can upload support, ask reporting-specific questions, generate a traceable artifact, and trust the answer enough to use it in review.

MVP capabilities:

- Chat-first reporting assistant.
- Shared ASC/SEC knowledge retrieval.
- User-private upload ingestion for Excel, PDF, DOCX, CSV, and text.
- Source-backed answers with citations.
- Session context.
- SCF generation from uploaded support workbook.
- Downloadable evidence package.
- Basic reporting skill router.
- Slack endpoint for simple reporting Q&A.
- File library for uploads, generated artifacts, and shared rules.
- Ingestion/retrieval status visibility.

MVP non-goals:

- Full ERP integration.
- Full Workiva round-trip editing.
- Autonomous filing updates.
- Journal entry posting.
- Replacing human review.
- Training customer-specific models.
- Full close management.
- Complex approval workflows beyond basic controlled review state.

## Core User Journeys

### Ask A Reporting Question

The user asks a reporting question. The assistant searches ASC/SEC guidance, private uploads, prior context, and company knowledge when available. The answer includes citations, assumptions, confidence, and next steps.

Acceptance criteria:

- Every sourced answer includes citations.
- The assistant says when support is insufficient.
- Citations identify source name, source type, and location.
- User can inspect cited support inline.
- Downloadable artifacts appear only when the request generates a file or the user explicitly asks to export support.

### Generate SCF Artifact

The user uploads a support workbook and asks for a cash-flow draft. The assistant parses workbook structure, generates SCF outputs, flags mapping issues, and returns downloadable workbook and evidence artifacts.

Acceptance criteria:

- Generated artifact includes source references for material numbers.
- Ambiguous or unmapped values are flagged.
- Output is reproducible from the same input.
- Development answer workbook is used only for validation, never generation.

### Draft Disclosure From Evidence

The user uploads support and prior filing excerpts. The assistant drafts disclosure language using evidence and prior-period style, highlights changed numbers, missing support, and judgment areas.

Acceptance criteria:

- Draft text is separated from evidence.
- Unsupported claims are marked.
- Sources used and sources not used are visible.

### Review And Tie-Out

The user uploads disclosure draft and support workbook. The assistant extracts numbers, compares them to support, and returns a tie-out table with source, variance, and status.

Acceptance criteria:

- Disclosure number, support number, variance, source, and status are visible.
- Exception statuses include matched, unmatched, variance, ambiguous, and manually accepted.

### Slack Reporting Assistant

The user asks a reporting question in Slack. The assistant replies concisely and links back to full evidence in the web app.

Acceptance criteria:

- Slack requests are authenticated.
- Slack sessions map to the correct reporting session.
- Full traceability remains in the web app.

## Phased Roadmap

### Phase 1: Reporting Copilot

Goal: trusted assistant for reporting Q&A, uploads, and artifact generation.

Priorities:

- Harden upload ingestion.
- Improve citations and confidence UX.
- Add evidence artifact per answer.
- Productize SCF evidence workflow.
- Add upload/session status.
- Keep Slack as lightweight interaction surface.

### Phase 2: Reporting Memory

Goal: make the assistant company-aware across time.

Features:

- Company knowledge graph.
- Persistent reporting memory across sessions.
- Historical package ingestion.
- Prior-period disclosure comparison.
- Company policy retrieval.
- Approved conclusions and reusable assumptions.
- Memory controls: approve, reject, expire, update.

### Phase 3: AI-Native Reporting Workflows

Goal: turn recurring reporting tasks into structured workflows.

Features:

- Workflow templates for SCF, footnotes, MD&A flux, debt, leases, EPS, share-based comp, and audit support.
- Task checklists.
- Review comments and approvals.
- Tie-out engine.
- Variance explanation generator.
- Workflow status dashboard.

### Phase 4: Agentic Reporting

Goal: governed reporting agents across enterprise systems.

Features:

- Reporting agents assigned to recurring processes.
- Connectors for ERP, Workiva, email, Slack, and document systems.
- Autonomous evidence collection.
- Exception detection.
- Human approval gates.
- Agent activity logs and control reports.

## Success Metrics

Activation:

- Percent of users who upload at least one reporting file.
- Percent of users who ask three or more reporting questions in the first week.
- Time from upload to first useful sourced answer.
- Time from upload to first generated artifact.

Trust:

- Percent of answers marked helpful.
- Citation click/download rate.
- Unsupported-answer rate.
- User-reported hallucination rate.
- Percent of artifacts accepted without major rework.

Workflow value:

- Time saved per reporting workflow.
- Reduction in manual tie-out time.
- Number of evidence artifacts generated per reporting cycle.
- Repeat usage during monthly or quarterly close.

Commercial:

- Pilot-to-paid conversion.
- Expansion from one reporting area to multiple areas.
- Sales cycle length.
- ARR per customer.
