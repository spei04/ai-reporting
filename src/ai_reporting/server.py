from __future__ import annotations

import json
import base64
import mimetypes
import os
import re
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from .chat import ReportingChatService, build_chat_service
from .engine import CashFlowEngine
from .env import load_local_env
from .file_context import summarize_upload
from .parser_profile import MappingOverride, ParserProfile
from .runtime import runtime_path, runtime_root
from .session_store import SessionStore
from .slack_integration import SlackIntegration
from .source_map import SourceCellMap
from .template import CashFlowTemplate
from .validation import DETAILED_BRIDGE_SHEET, compare_to_answer


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = runtime_root(ROOT)
DEFAULT_TEMPLATE = ROOT / "config" / "standard_q1_scf_template.json"
DEFAULT_SOURCE_MAP = ROOT / "config" / "source_cell_map_q1.json"
DEFAULT_PARSER_PROFILE = ROOT / "config" / "company_parser_profile.json"
DEFAULT_OUTPUT_DIR = runtime_path("outputs", "first_milestone", root=ROOT)
UPLOAD_DIR = runtime_path("uploads", root=ROOT)
ENV_FILE = ROOT / ".env"
SESSION_STORE = SessionStore(runtime_path("data", "sessions", root=ROOT))
CHAT_SERVICE: ReportingChatService | None = None
SLACK_INTEGRATION: SlackIntegration | None = None


class ReportingRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.path = "/web/index.html"
            super().do_GET()
            return
        if parsed.path == "/api/parser-profile":
            profile = ParserProfile.load(DEFAULT_PARSER_PROFILE)
            self._send_json(profile.to_json())
            return
        if parsed.path == "/api/health":
            self._send_json(_health_payload())
            return
        if parsed.path == "/api/session-library":
            query = parse_qs(parsed.query)
            session_id = query.get("session_id", [""])[0]
            self._send_json(_session_library_payload(session_id))
            return
        if parsed.path == "/api/slack/install":
            self._send_json(_slack_integration().install_url(_public_base_url(self)))
            return
        if parsed.path == "/api/slack/oauth/callback":
            query = parse_qs(parsed.query)
            payload = _slack_integration().complete_oauth(query, _public_base_url(self))
            self._send_json(payload, HTTPStatus.OK if payload.get("status") == "installed" else HTTPStatus.BAD_REQUEST)
            return
        super().do_GET()

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/api/sessions":
            self._handle_create_session()
            return
        if self.path == "/api/chat":
            self._handle_chat()
            return
        if self.path == "/api/uploads":
            self._handle_session_uploads()
            return
        if self.path in {"/slack/commands", "/api/slack/commands"}:
            self._handle_slack_command()
            return
        if self.path in {"/slack/events", "/api/slack/events"}:
            self._handle_slack_event()
            return
        if self.path == "/api/generate":
            self._handle_generate()
            return
        if self.path == "/api/mapping-override":
            self._handle_mapping_override()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Answer-Workbook, X-Session-ID")
        super().end_headers()

    def _handle_create_session(self) -> None:
        session_id = SESSION_STORE.create_session()
        self._send_json({"status": "created", "session_id": session_id})

    def _handle_chat(self) -> None:
        try:
            content_type = self.headers.get("Content-Type", "")
            if content_type.startswith("multipart/form-data"):
                fields, files = self._read_multipart_body()
                session_id = fields.get("session_id") or self.headers.get("X-Session-ID")
                message = fields.get("message", "")
                uploads = [(item["filename"], item["data"]) for item in files]
            else:
                data = self._read_json_body()
                session_id = str(data.get("session_id") or self.headers.get("X-Session-ID") or "")
                message = str(data.get("message") or "")
                uploads = []

            if not message.strip() and not uploads:
                raise ValueError("Expected a message or uploaded file")
            payload = _chat_service().handle_message(session_id, message, uploads)
            self._send_json(payload)
        except Exception as exc:
            self._send_json({"status": "error", "message": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _handle_session_uploads(self) -> None:
        try:
            fields, files = self._read_multipart_body()
            session_id = fields.get("session_id") or self.headers.get("X-Session-ID")
            uploads = [
                (str(item["filename"]), item["data"])
                for item in files
                if isinstance(item.get("data"), bytes)
            ]
            if not uploads:
                raise ValueError("Select at least one file to upload")
            payload = _chat_service().store_uploads(session_id, uploads)
            self._send_json(payload)
        except Exception as exc:
            self._send_json({"status": "error", "message": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _handle_slack_command(self) -> None:
        raw_body = self._read_raw_body()
        payload, status_code = _slack_integration().handle_slash_command(raw_body, _lower_headers(self.headers))
        self._send_json(payload, HTTPStatus(status_code))

    def _handle_slack_event(self) -> None:
        raw_body = self._read_raw_body()
        payload, status_code = _slack_integration().handle_event(raw_body, _lower_headers(self.headers))
        self._send_json(payload, HTTPStatus(status_code))

    def _handle_generate(self) -> None:
        try:
            fields, files = self._read_multipart_body()
            uploaded, original_name, uploaded_bytes = self._save_uploaded_workbook(files)
            result, validation = self._generate_from_workbook(uploaded)
            payload = self._generation_payload(uploaded, result, validation)
            session_id = fields.get("session_id") or self.headers.get("X-Session-ID")
            if session_id:
                session_id = SESSION_STORE.ensure_session(session_id)
                summary = summarize_upload(original_name, uploaded_bytes)
                stored_upload = SESSION_STORE.save_upload(session_id, original_name, uploaded_bytes, summary)
                _chat_service().knowledge.ingest_user_document(
                    session_id,
                    stored_upload.file_id,
                    stored_upload.filename,
                    stored_upload.path,
                    uploaded_bytes,
                    stored_upload.summary,
                )
                SESSION_STORE.record_generated_artifacts(
                    session_id,
                    {
                        "source_file_id": stored_upload.file_id,
                        "output_workbook": str(result.output_workbook),
                        "evidence_json": str(result.evidence_json),
                        "mapping_review_json": str(result.mapping_review_json),
                        "normalized_support_json": str(result.normalized_support_json),
                    },
                )
                payload["session_id"] = session_id
                payload["stored_file_id"] = stored_upload.file_id
            self._send_json(payload)
        except Exception as exc:
            self._send_json({"status": "error", "message": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _handle_mapping_override(self) -> None:
        try:
            data = self._read_json_body()
            override = MappingOverride(
                canonical_sheet=str(data["canonical_sheet"]),
                canonical_cell=str(data["canonical_cell"]).upper(),
                actual_sheet=str(data["actual_sheet"]),
                actual_cell=str(data["actual_cell"]).upper(),
                note=str(data.get("note") or "").strip() or None,
            )
            profile = ParserProfile.load(DEFAULT_PARSER_PROFILE).with_override(override)
            profile.save(DEFAULT_PARSER_PROFILE)

            workbook = self._latest_uploaded_workbook()
            result, validation = self._generate_from_workbook(workbook)
            payload = self._generation_payload(workbook, result, validation)
            payload["parser_profile_json"] = _web_path(DEFAULT_PARSER_PROFILE)
            payload["saved_override"] = override.__dict__
            self._send_json(payload)
        except Exception as exc:
            self._send_json({"status": "error", "message": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _generate_from_workbook(self, workbook: Path):
        template = CashFlowTemplate.load(DEFAULT_TEMPLATE)
        source_map = SourceCellMap.load(DEFAULT_SOURCE_MAP)
        parser_profile = ParserProfile.load(DEFAULT_PARSER_PROFILE)
        engine = CashFlowEngine(workbook, template, source_map, parser_profile)
        result = engine.generate(DEFAULT_OUTPUT_DIR)

        answer_header = self.headers.get("X-Answer-Workbook")
        validation = None
        if answer_header:
            answer_path = Path(answer_header)
            if not answer_path.exists():
                raise ValueError(f"Answer workbook not found: {answer_path}")
            diffs = compare_to_answer(engine, answer_path)
            validation = {
                "status": "passed" if not diffs else "failed",
                "answer_workbook_tab": DETAILED_BRIDGE_SHEET,
                "note": "answer.xlsx is read only after generation completes",
                "differences": [diff.__dict__ for diff in diffs],
            }
        return result, validation

    def _generation_payload(self, uploaded: Path, result, validation: dict[str, object] | None) -> dict[str, object]:
        return {
            "status": "generated",
            "uploaded_workbook": str(uploaded),
            "output_workbook": _web_path(result.output_workbook),
            "values_json": _web_path(result.values_json),
            "evidence_json": _web_path(result.evidence_json),
            "normalized_support_json": _web_path(result.normalized_support_json),
            "workbook_profile_json": _web_path(result.workbook_profile_json),
            "mapping_review_json": _web_path(result.mapping_review_json),
            "inline_artifacts": _inline_artifacts(result),
            "evidence_data": _read_json_artifact(result.evidence_json),
            "mapping_review_data": _read_json_artifact(result.mapping_review_json),
            "golden_validation": validation,
        }

    def _read_json_body(self) -> dict[str, object]:
        return json.loads(self._read_raw_body().decode("utf-8"))

    def _read_raw_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise ValueError("Expected request body")
        return self.rfile.read(length)

    def _latest_uploaded_workbook(self) -> Path:
        workbooks = sorted(UPLOAD_DIR.glob("*.xlsx"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not workbooks:
            raise ValueError("Upload a workbook before saving mapping overrides")
        return workbooks[0]

    def _read_multipart_body(self) -> tuple[dict[str, str], list[dict[str, object]]]:
        content_type = self.headers.get("Content-Type", "")
        boundary_match = re.search(r"boundary=(.+)", content_type)
        if not boundary_match:
            raise ValueError("Expected multipart form upload")

        boundary = boundary_match.group(1).strip().strip('"')
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        boundary_bytes = f"--{boundary}".encode()
        fields: dict[str, str] = {}
        files: list[dict[str, object]] = []

        for part in body.split(boundary_bytes):
            if b"Content-Disposition" not in part:
                continue
            header_blob, _, file_blob = part.partition(b"\r\n\r\n")
            if not header_blob or not file_blob:
                continue
            data = file_blob.rsplit(b"\r\n", 1)[0]
            headers = header_blob.decode("utf-8", errors="ignore")
            name = _extract_field_name(headers)
            filename = _extract_filename(headers)
            if filename:
                files.append({"name": name, "filename": filename, "data": data})
            elif name:
                fields[name] = data.decode("utf-8", errors="replace")

        return fields, files

    def _save_uploaded_workbook(self, files: list[dict[str, object]]) -> tuple[Path, str, bytes]:
        for item in files:
            filename = str(item["filename"])
            data = item["data"]
            if not isinstance(data, bytes):
                continue
            if not filename.lower().endswith(".xlsx"):
                continue
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            path = UPLOAD_DIR / _safe_filename(filename)
            path.write_bytes(data)
            return path, filename, data

        raise ValueError("No .xlsx workbook file found in upload")

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, indent=2, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _extract_filename(headers: str) -> str:
    match = re.search(r'filename="([^"]+)"', headers)
    return unquote(match.group(1)) if match else ""


def _extract_field_name(headers: str) -> str:
    match = re.search(r'name="([^"]+)"', headers)
    return unquote(match.group(1)) if match else ""


def _safe_filename(filename: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_. -]+", "_", Path(filename).name)
    return stem or "uploaded.xlsx"


def _web_path(path: Path) -> str:
    try:
        return "/" + path.relative_to(ROOT).as_posix()
    except ValueError:
        return ""


def _web_download_path(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(ROOT)
    except ValueError:
        return ""
    return "/" + quote(relative.as_posix())


def _inline_artifacts(result) -> list[dict[str, object]]:
    artifacts = [
        ("output_workbook", "Generated SCF workbook", result.output_workbook),
        ("evidence_json", "Evidence links", result.evidence_json),
        ("mapping_review_json", "Mapping review", result.mapping_review_json),
        ("normalized_support_json", "Normalized support", result.normalized_support_json),
    ]
    payload = []
    for key, label, path in artifacts:
        if not path.exists():
            continue
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        payload.append(
            {
                "key": key,
                "title": label,
                "filename": path.name,
                "mime_type": mime_type,
                "base64": base64.b64encode(path.read_bytes()).decode("ascii"),
            }
        )
    return payload


def _read_json_artifact(path: Path) -> object | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _session_library_payload(session_id: str) -> dict[str, object]:
    uploads: list[dict[str, object]] = []
    outputs: list[dict[str, object]] = []
    if session_id and SESSION_STORE.session_dir(session_id).exists():
        manifest = SESSION_STORE.manifest(session_id)
        for item in manifest.get("uploads", []):
            path = Path(str(item.get("stored_path", "")))
            uploads.append(
                {
                    "name": item.get("filename") or path.name,
                    "href": _web_download_path(path),
                    "kind": item.get("summary", {}).get("type", "upload"),
                    "created_at": item.get("created_at", ""),
                }
            )
        for artifact in manifest.get("artifacts", []):
            for key, label in [
                ("output_workbook", "Generated SCF workbook"),
                ("evidence_json", "Evidence links"),
                ("mapping_review_json", "Mapping review"),
                ("normalized_support_json", "Normalized support"),
                ("amortization_workbook", "Amortization schedule"),
            ]:
                path_value = artifact.get(key)
                if not path_value:
                    continue
                path = Path(str(path_value))
                outputs.append(
                    {
                        "name": label,
                        "filename": path.name,
                        "href": _web_download_path(path),
                        "kind": key,
                        "created_at": artifact.get("created_at", ""),
                    }
                )

    rules = []
    raw_root = ROOT / "data" / "raw"
    for path in sorted(raw_root.glob("FASB Accounting Standard Codifications (ASC)/*.pdf")):
        rules.append({"name": path.stem, "href": _web_download_path(path), "kind": "ASC"})
    for path in sorted(raw_root.glob("SEC Regulation/*.pdf")):
        rules.append({"name": path.stem, "href": _web_download_path(path), "kind": "SEC"})

    return {
        "status": "ok",
        "session_id": session_id,
        "uploads": uploads,
        "outputs": outputs,
        "rules": rules,
    }


def _health_payload() -> dict[str, object]:
    runtime_probe = RUNTIME_ROOT / ".write_check"
    runtime_writable = False
    try:
        runtime_probe.parent.mkdir(parents=True, exist_ok=True)
        runtime_probe.write_text("ok")
        runtime_probe.unlink(missing_ok=True)
        runtime_writable = True
    except Exception:
        runtime_writable = False

    return {
        "status": "ok",
        "runtime_root": str(RUNTIME_ROOT),
        "runtime_writable": runtime_writable,
        "template_ready": DEFAULT_TEMPLATE.exists(),
        "source_map_ready": DEFAULT_SOURCE_MAP.exists(),
        "parser_profile_ready": DEFAULT_PARSER_PROFILE.exists(),
        "knowledge_db_ready": (ROOT / "data" / "reporting_knowledge.db").exists()
        or (ROOT / "data" / "reporting_knowledge_seed.json").exists(),
        "openai_configured": bool(os.environ.get("OPENAI_API_KEY")),
    }


def _chat_service() -> ReportingChatService:
    global CHAT_SERVICE
    if CHAT_SERVICE is None:
        CHAT_SERVICE = build_chat_service(ROOT)
    return CHAT_SERVICE


def _slack_integration() -> SlackIntegration:
    global SLACK_INTEGRATION
    if SLACK_INTEGRATION is None:
        SLACK_INTEGRATION = SlackIntegration(ROOT, SESSION_STORE, _chat_service())
    return SLACK_INTEGRATION


def _lower_headers(headers) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in headers.items()}


def _public_base_url(handler: SimpleHTTPRequestHandler) -> str:
    configured = os.environ.get("AI_REPORTING_PUBLIC_BASE_URL", "").strip()
    if configured:
        return configured
    host = handler.headers.get("Host", "127.0.0.1:8001")
    scheme = "https" if handler.headers.get("X-Forwarded-Proto") == "https" else "http"
    return f"{scheme}://{host}"


def main() -> None:
    load_local_env(ENV_FILE)
    server = ThreadingHTTPServer(("127.0.0.1", 8001), ReportingRequestHandler)
    print("Serving AI Reporting on http://127.0.0.1:8001/web/")
    if os.environ.get("OPENAI_API_KEY"):
        print(f"OpenAI key loaded. Model: {os.environ.get('OPENAI_MODEL', 'auto')}")
    else:
        print("OpenAI key not set. Chat model calls will use local preview behavior.")
    server.serve_forever()


if __name__ == "__main__":
    main()
