# Slack Integration

## Purpose

Let reporting teams interact with the AI Reporting agent from Slack.

## Current Features

- OAuth install URL endpoint: `GET /api/slack/install`.
- OAuth callback endpoint: `GET /api/slack/oauth/callback`.
- Slash command endpoints:
  - `POST /slack/commands`
  - `POST /api/slack/commands`
- Events API endpoints:
  - `POST /slack/events`
  - `POST /api/slack/events`
- Slack request signature verification.
- Persistent Slack session mapping:
  - `slack_{team_id}_{channel_id}_{user_id}`
- Slack file download and private session ingestion when a bot token is available.
- Background response handling for longer reporting answers.

## Planned Next Slack Features

- Interactive approvals.
- Download buttons.
- Source-trace buttons.
- Review workflow actions.
