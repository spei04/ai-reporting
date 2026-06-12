from __future__ import annotations

import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from ai_reporting.llm import ReportingLlmClient


class FakeHttpResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FakeHttpError(urllib.error.HTTPError):
    def __init__(self, status_code, payload):
        super().__init__("https://api.openai.com/v1/responses", status_code, "error", {}, None)
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class ReportingLlmClientTest(unittest.TestCase):
    def setUp(self):
        self.env = dict(os.environ)
        os.environ["OPENAI_API_KEY"] = "test-key"
        os.environ.pop("OPENAI_MODEL", None)
        os.environ.pop("OPENAI_MODEL_CANDIDATES", None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)

    def test_auto_prefers_available_current_gpt_models(self):
        def fake_urlopen(request, timeout):
            self.assertEqual(request.full_url, "https://api.openai.com/v1/models")
            return FakeHttpResponse(
                {
                    "data": [
                        {"id": "gpt-5.5"},
                        {"id": "gpt-5.4-mini"},
                    ]
                }
            )

        with patch("ai_reporting.llm.urllib.request.urlopen", fake_urlopen):
            client = ReportingLlmClient()

        self.assertEqual(client.model_candidates[:2], ["gpt-5.4-mini", "gpt-5.5"])

    def test_complete_falls_back_to_next_model(self):
        os.environ["OPENAI_MODEL_CANDIDATES"] = "bad-model,gpt-5.4-mini"
        requested_models = []

        def fake_urlopen(request, timeout):
            payload = json.loads(request.data.decode("utf-8"))
            requested_models.append(payload["model"])
            if payload["model"] == "bad-model":
                raise FakeHttpError(400, {"error": {"message": "model not found"}})
            return FakeHttpResponse(
                {
                    "model": payload["model"],
                    "output_text": "Live GPT answer.",
                }
            )

        with patch("ai_reporting.llm.urllib.request.urlopen", fake_urlopen):
            client = ReportingLlmClient()
            response = client.complete("system", {}, "question")

        self.assertEqual(requested_models, ["bad-model", "gpt-5.4-mini"])
        self.assertTrue(response.used_live_model)
        self.assertEqual(response.provider, "openai")
        self.assertEqual(response.model, "gpt-5.4-mini")
        self.assertEqual(response.text, "Live GPT answer.")

    def test_quota_error_stops_model_fallback(self):
        os.environ["OPENAI_MODEL_CANDIDATES"] = "gpt-5.4-mini,gpt-5.4"
        requested_models = []

        def fake_urlopen(request, timeout):
            payload = json.loads(request.data.decode("utf-8"))
            requested_models.append(payload["model"])
            raise FakeHttpError(429, {"error": {"message": "You exceeded your current quota", "code": "insufficient_quota"}})

        with patch("ai_reporting.llm.urllib.request.urlopen", fake_urlopen):
            client = ReportingLlmClient()
            response = client.complete("system", {}, "question")

        self.assertEqual(requested_models, ["gpt-5.4-mini"])
        self.assertFalse(response.used_live_model)
        self.assertIn("quota", response.text)


if __name__ == "__main__":
    unittest.main()
