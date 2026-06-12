# Chat And Model Provider

## Purpose

Answer reporting questions with permanent reporting instructions, retrieved rule context, session-specific upload context, and the user question.

The chat context is assembled as a layered cache for a vertical reporting agent:

1. Permanent reporting system prompt.
2. Selected reporting skill and curated L2 skill spec, when routed.
3. Retrieved ASC/SEC rule context, only when the skill needs it.
4. Retrieved session/company upload context.
5. Current user question.

## Current Features

- Backend endpoint: `/api/chat`.
- Uses OpenAI Responses API through `ReportingLlmClient`.
- Reads configuration from `.env`:
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL`
  - `OPENAI_MODEL_CANDIDATES`
- Supports `OPENAI_MODEL=auto`.
- Tries current GPT model candidates in order.
- Returns local preview responses if no OpenAI key is configured.
- Formats model output into:
  - summary
  - key points
  - rule support tags
  - next step
- Retrieves and displays ASC/SEC rule context only for reporting workflows that need it.
- Returns structured source citations with source type, citation label, title, excerpt, path, score, and source number.
- Generic uncategorized questions still call GPT normally without selected skill context or displayed rule-context cards.
- Keeps provider/model metadata in session message history.
- Includes `selected_skill_spec` metadata for categorized reporting workflows so downstream clients can inspect which L2 playbook was used.
- Returns both `answer` for concise UI display and `raw_answer` for full model output, which Slack uses.
- Adds a compact support state to reporting answers:
  - `Source backed`
  - `Partially supported`
  - `No source found`
- Ordinary Q&A responses do not show downloadable outputs.
- Downloadable outputs are reserved for workflows that generate files, such as SCF workbooks and evidence artifacts.

## Fallback Rule

If the backend cannot categorize a query into a reporting skill, it still calls the GPT model normally with no `selected_reporting_skill` context.

Uncategorized responses also avoid showing retrieved rule-context sections unless a reporting workflow explicitly requires them.
