from __future__ import annotations

import hmac
import hashlib
import os
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import urlencode

from ai_reporting.session_store import SessionStore
from ai_reporting.slack_integration import SlackContext, SlackIntegration


class FakeChatService:
    def __init__(self):
        self.calls = []

    def handle_message(self, session_id, message, uploads=None):
        self.calls.append({"session_id": session_id, "message": message, "uploads": uploads or []})
        return {
            "answer": "ASC 230 supports cash flow statement presentation.",
            "citations": [{"citation": "ASC 230", "title": "Cash Flow Statements"}],
        }


class SlackIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = SessionStore(self.root / "sessions")
        self.chat = FakeChatService()
        self.integration = SlackIntegration(self.root, self.store, self.chat)
        self.env_backup = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env_backup)
        self.tmp.cleanup()

    def test_verify_signed_request(self):
        os.environ["SLACK_SIGNING_SECRET"] = "test-secret"
        body = b"team_id=T123&channel_id=C123&user_id=U123&text=hello"
        timestamp = str(int(time.time()))
        digest = hmac.new(
            b"test-secret",
            b"v0:" + timestamp.encode("utf-8") + b":" + body,
            hashlib.sha256,
        ).hexdigest()
        headers = {
            "x-slack-request-timestamp": timestamp,
            "x-slack-signature": f"v0={digest}",
        }

        self.assertTrue(self.integration.verify_request(body, headers))

    def test_slash_command_routes_to_reporting_agent(self):
        os.environ["SLACK_ALLOW_UNSIGNED_DEV"] = "true"
        body = urlencode(
            {
                "team_id": "T123",
                "channel_id": "C456",
                "user_id": "U789",
                "text": "What does ASC 230 require?",
            }
        ).encode("utf-8")

        payload, status = self.integration.handle_slash_command(body, {})

        self.assertEqual(status, 200)
        self.assertIn("ASC 230", payload["text"])
        self.assertEqual(self.chat.calls[0]["session_id"], "slack_T123_C456_U789")
        self.assertTrue((self.root / "sessions" / "slack_T123_C456_U789").exists())

    def test_event_url_verification(self):
        os.environ["SLACK_ALLOW_UNSIGNED_DEV"] = "true"
        body = b'{"type":"url_verification","challenge":"abc123"}'

        payload, status = self.integration.handle_event(body, {})

        self.assertEqual(status, 200)
        self.assertEqual(payload["challenge"], "abc123")

    def test_slack_state_uses_runtime_directory(self):
        with tempfile.TemporaryDirectory() as runtime:
            os.environ["AI_REPORTING_RUNTIME_DIR"] = runtime
            integration = SlackIntegration(self.root, self.store, self.chat)

            self.assertEqual(integration.data_dir, Path(runtime) / "data" / "slack")

    def test_context_session_id_is_sanitized(self):
        context = SlackContext(team_id="T-1", channel_id="C.2", user_id="U 3")

        self.assertEqual(context.session_id, "slack_T-1_C2_U3")


if __name__ == "__main__":
    unittest.main()
