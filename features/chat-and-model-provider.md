# Chat And Model Provider

## Purpose

Answer reporting questions with permanent reporting instructions, retrieved rule context, session-specific upload context, and the user question.

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
- Adds a compact support state to reporting answers:
  - `Source backed`
  - `Partially supported`
  - `No source found`
- Ordinary Q&A responses do not show downloadable outputs.
- Downloadable outputs are reserved for workflows that generate files, such as SCF workbooks and evidence artifacts.

## Fallback Rule

If the backend cannot categorize a query into a reporting skill, it still calls the GPT model normally with no `selected_reporting_skill` context.

Uncategorized responses also avoid showing retrieved rule-context sections unless a reporting workflow explicitly requires them.
