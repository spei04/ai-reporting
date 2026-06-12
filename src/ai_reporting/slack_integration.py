from __future__ import annotations

import hmac
import hashlib
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode
from urllib.request import Request, urlopen

from .chat import ReportingChatService
from .session_store import SessionStore


SLACK_API_BASE = "https://slack.com/api"
DEFAULT_SCOPES = ",".join(
    [
        "commands",
        "chat:write",
        "app_mentions:read",
        "im:history",
        "im:read",
        "im:write",
        "files:read",
    ]
)


@dataclass(frozen=True)
class SlackContext:
    team_id: str
    channel_id: str
    user_id: str
    thread_ts: str | None = None

    @property
    def session_id(self) -> str:
        parts = ["slack", self.team_id or "team", self.channel_id or "channel", self.user_id or "user"]
        return "_".join(_safe_id(part) for part in parts)


class SlackIntegration:
    def __init__(self, root: Path, store: SessionStore, chat_service: ReportingChatService):
        self.root = root
        self.store = store
        self.chat_service = chat_service
        self.data_dir = root / "data" / "slack"
        self.installations_path = self.data_dir / "installations.json"
        self.states_path = self.data_dir / "oauth_states.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def install_url(self, public_base_url: str) -> dict[str, Any]:
        client_id = os.environ.get("SLACK_CLIENT_ID", "").strip()
        if not client_id:
            return {
                "status": "configuration_required",
                "message": "Set SLACK_CLIENT_ID before installing the Slack app.",
            }
        state = secrets.token_urlsafe(18)
        redirect_uri = self.redirect_uri(public_base_url)
        states = self._read_json(self.states_path, {})
        states[state] = {"created_at": time.time(), "redirect_uri": redirect_uri}
        self._write_json(self.states_path, states)
        query = urlencode(
            {
                "client_id": client_id,
                "scope": os.environ.get("SLACK_SCOPES", DEFAULT_SCOPES),
                "redirect_uri": redirect_uri,
                "state": state,
            }
        )
        return {
            "status": "ok",
            "install_url": f"https://slack.com/oauth/v2/authorize?{query}",
            "redirect_uri": redirect_uri,
        }

    def complete_oauth(self, query: dict[str, list[str]], public_base_url: str) -> dict[str, Any]:
        code = _first(query, "code")
        state = _first(query, "state")
        if not code:
            return {"status": "error", "message": "Slack OAuth did not include a code."}

        states = self._read_json(self.states_path, {})
        state_record = states.pop(state, None)
        self._write_json(self.states_path, states)
        if state and not state_record:
            return {"status": "error", "message": "Slack OAuth state was not recognized."}

        client_id = os.environ.get("SLACK_CLIENT_ID", "").strip()
        client_secret = os.environ.get("SLACK_CLIENT_SECRET", "").strip()
        if not client_id or not client_secret:
            return {
                "status": "configuration_required",
                "message": "Set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET before completing Slack OAuth.",
            }

        redirect_uri = (state_record or {}).get("redirect_uri") or self.redirect_uri(public_base_url)
        payload = self._post_slack_api(
            "oauth.v2.access",
            None,
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        if not payload.get("ok"):
            return {"status": "error", "message": payload.get("error", "Slack OAuth failed"), "slack": payload}

        team = payload.get("team") or {}
        team_id = str(team.get("id") or payload.get("team_id") or "")
        if not self._team_allowed(team_id):
            return {"status": "error", "message": "This Slack workspace is not allowed for this deployment."}

        installations = self._read_json(self.installations_path, {})
        installations[team_id] = {
            "team": team,
            "enterprise": payload.get("enterprise"),
            "authed_user": payload.get("authed_user"),
            "scope": payload.get("scope"),
            "bot_user_id": payload.get("bot_user_id"),
            "access_token": payload.get("access_token"),
            "installed_at": time.time(),
        }
        self._write_json(self.installations_path, installations)
        return {
            "status": "installed",
            "team_id": team_id,
            "team_name": team.get("name"),
            "bot_user_id": payload.get("bot_user_id"),
        }

    def handle_slash_command(self, raw_body: bytes, headers: dict[str, str]) -> tuple[dict[str, Any], int]:
        if not self.verify_request(raw_body, headers):
            return {"response_type": "ephemeral", "text": "Slack request verification failed."}, 401

        fields = {key: values[0] for key, values in parse_qs(raw_body.decode("utf-8")).items()}
        context = SlackContext(
            team_id=fields.get("team_id", ""),
            channel_id=fields.get("channel_id", ""),
            user_id=fields.get("user_id", ""),
        )
        question = fields.get("text", "").strip() or "How can you help with reporting?"
        response_url = fields.get("response_url", "")

        if response_url:
            self._run_background_answer(context, question, response_url=response_url)
            return {
                "response_type": "ephemeral",
                "text": "Working on it. I will respond here with a reporting-backed answer.",
            }, 200

        answer = self.answer_for_slack(context, question)
        return {"response_type": "ephemeral", "text": answer}, 200

    def handle_event(self, raw_body: bytes, headers: dict[str, str]) -> tuple[dict[str, Any], int]:
        if not self.verify_request(raw_body, headers):
            return {"status": "error", "message": "Slack request verification failed."}, 401

        payload = json.loads(raw_body.decode("utf-8"))
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge", "")}, 200

        event = payload.get("event") or {}
        event_type = event.get("type")
        if event.get("subtype") in {"bot_message", "message_deleted", "message_changed"}:
            return {"ok": True}, 200

        team_id = str(payload.get("team_id") or event.get("team") or "")
        channel_id = str(event.get("channel") or "")
        user_id = str(event.get("user") or "")
        thread_ts = str(event.get("thread_ts") or event.get("ts") or "")
        text = self._event_question(event)

        if event_type not in {"app_mention", "message"} or not text or not channel_id or not user_id:
            return {"ok": True}, 200

        context = SlackContext(team_id=team_id, channel_id=channel_id, user_id=user_id, thread_ts=thread_ts)
        file_refs = event.get("files") if isinstance(event.get("files"), list) else []
        self._run_background_answer(context, text, file_refs=file_refs)
        return {"ok": True}, 200

    def answer_for_slack(
        self,
        context: SlackContext,
        question: str,
        file_refs: list[dict[str, Any]] | None = None,
    ) -> str:
        session_id = self.store.ensure_named_session(context.session_id)
        uploads = self._download_event_files(context.team_id, file_refs or [])
        payload = self.chat_service.handle_message(session_id, question, uploads)
        answer = payload.get("answer") or payload.get("display", {}).get("summary") or "No answer returned."
        citations = payload.get("citations") or []
        if citations:
            top = citations[0]
            citation = top.get("citation") or top.get("title")
            if citation:
                answer = f"{answer}\n\nRule support: {citation}"
        return _slack_text(answer)

    def verify_request(self, raw_body: bytes, headers: dict[str, str]) -> bool:
        signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "").strip()
        if not signing_secret:
            return os.environ.get("SLACK_ALLOW_UNSIGNED_DEV", "").lower() in {"1", "true", "yes"}

        timestamp = headers.get("x-slack-request-timestamp", "")
        signature = headers.get("x-slack-signature", "")
        if not timestamp or not signature:
            return False
        try:
            if abs(time.time() - int(timestamp)) > 60 * 5:
                return False
        except ValueError:
            return False

        basestring = b"v0:" + timestamp.encode("utf-8") + b":" + raw_body
        digest = hmac.new(signing_secret.encode("utf-8"), basestring, hashlib.sha256).hexdigest()
        expected = f"v0={digest}"
        return hmac.compare_digest(expected, signature)

    def redirect_uri(self, public_base_url: str) -> str:
        configured = os.environ.get("SLACK_REDIRECT_URI", "").strip()
        if configured:
            return configured
        return f"{public_base_url.rstrip('/')}/api/slack/oauth/callback"

    def _run_background_answer(
        self,
        context: SlackContext,
        question: str,
        response_url: str | None = None,
        file_refs: list[dict[str, Any]] | None = None,
    ) -> None:
        def worker() -> None:
            try:
                answer = self.answer_for_slack(context, question, file_refs=file_refs)
            except Exception as exc:
                answer = f"I could not complete that reporting request: {exc}"
            if response_url:
                self._post_response_url(response_url, {"response_type": "ephemeral", "text": answer})
            else:
                self._post_channel_message(context, answer)

        threading.Thread(target=worker, daemon=True).start()

    def _event_question(self, event: dict[str, Any]) -> str:
        text = str(event.get("text") or "").strip()
        text = " ".join(part for part in text.split() if not (part.startswith("<@") and part.endswith(">")))
        if text:
            return text
        files = event.get("files")
        if files:
            return "Please review the uploaded file for reporting context."
        return ""

    def _download_event_files(self, team_id: str, file_refs: list[dict[str, Any]]) -> list[tuple[str, bytes]]:
        token = self._bot_token(team_id)
        if not token:
            return []
        uploads = []
        for file_ref in file_refs[:5]:
            url = file_ref.get("url_private_download") or file_ref.get("url_private")
            name = file_ref.get("name") or file_ref.get("title") or "slack-upload"
            if not url:
                continue
            request = Request(str(url), headers={"Authorization": f"Bearer {token}"})
            with urlopen(request, timeout=20) as response:
                uploads.append((str(name), response.read()))
        return uploads

    def _post_channel_message(self, context: SlackContext, text: str) -> None:
        token = self._bot_token(context.team_id)
        if not token:
            return
        payload: dict[str, Any] = {"channel": context.channel_id, "text": text}
        if context.thread_ts:
            payload["thread_ts"] = context.thread_ts
        self._post_slack_api("chat.postMessage", token, payload, json_body=True)

    def _post_response_url(self, response_url: str, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        request = Request(response_url, data=data, headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=20) as response:
            response.read()

    def _post_slack_api(
        self,
        method: str,
        token: str | None,
        payload: dict[str, Any],
        json_body: bool = False,
    ) -> dict[str, Any]:
        if json_body:
            data = json.dumps(payload).encode("utf-8")
            headers = {"Content-Type": "application/json; charset=utf-8"}
        else:
            data = urlencode(payload).encode("utf-8")
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(f"{SLACK_API_BASE}/{method}", data=data, headers=headers)
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def _bot_token(self, team_id: str) -> str:
        env_token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
        if env_token:
            return env_token
        installations = self._read_json(self.installations_path, {})
        return str((installations.get(team_id) or {}).get("access_token") or "")

    def _team_allowed(self, team_id: str) -> bool:
        allowed = [item.strip() for item in os.environ.get("SLACK_ALLOWED_TEAM_IDS", "").split(",") if item.strip()]
        return not allowed or team_id in allowed

    def _read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text())

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, default=str))


def _safe_id(value: str) -> str:
    safe = "".join(ch for ch in value if ch.isalnum() or ch in "_-")
    return safe or "unknown"


def _first(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key) or []
    return values[0] if values else ""


def _slack_text(value: str) -> str:
    text = str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text[:2900] + "\n\nResponse shortened for Slack." if len(text) > 3000 else text
