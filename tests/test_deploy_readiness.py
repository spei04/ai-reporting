from __future__ import annotations

import base64
import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from ai_reporting import server


@dataclass
class FakeGenerationResult:
    output_workbook: Path
    evidence_json: Path
    mapping_review_json: Path
    normalized_support_json: Path


class DeployReadinessTest(unittest.TestCase):
    def test_health_payload_reports_deploy_requirements(self) -> None:
        payload = server._health_payload()

        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["runtime_writable"])
        self.assertTrue(payload["template_ready"])
        self.assertTrue(payload["source_map_ready"])
        self.assertTrue(payload["parser_profile_ready"])
        self.assertIn("knowledge_db_ready", payload)

    def test_inline_artifacts_are_browser_downloadable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workbook = root / "generated.xlsx"
            evidence = root / "evidence_links.json"
            mapping = root / "mapping_review.json"
            normalized = root / "normalized_support.json"
            workbook.write_bytes(b"xlsx bytes")
            evidence.write_text(json.dumps([{"output_cell": "B2"}]))
            mapping.write_text(json.dumps([{"status": "matched"}]))
            normalized.write_text(json.dumps({"items": []}))

            payload = server._inline_artifacts(
                FakeGenerationResult(
                    output_workbook=workbook,
                    evidence_json=evidence,
                    mapping_review_json=mapping,
                    normalized_support_json=normalized,
                )
            )

        by_key = {item["key"]: item for item in payload}
        self.assertEqual(set(by_key), {"output_workbook", "evidence_json", "mapping_review_json", "normalized_support_json"})
        self.assertEqual(base64.b64decode(by_key["output_workbook"]["base64"]), b"xlsx bytes")
        self.assertEqual(json.loads(base64.b64decode(by_key["evidence_json"]["base64"])), [{"output_cell": "B2"}])

    def test_slack_route_matching_tolerates_vercel_paths(self) -> None:
        self.assertTrue(server._is_slack_route("/api/slack/events", "events"))
        self.assertTrue(server._is_slack_route("/slack/events", "events"))
        self.assertTrue(server._is_slack_route("/events", "events"))
        self.assertTrue(server._is_slack_route("/api/index.py/slack/events", "events"))
        self.assertTrue(server._is_slack_route("/api/slack/commands", "commands"))
        self.assertFalse(server._is_slack_route("/api/health", "events"))
        self.assertEqual(server._normalized_request_path("/api/slack/events?x=1"), "/api/slack/events")


if __name__ == "__main__":
    unittest.main()
