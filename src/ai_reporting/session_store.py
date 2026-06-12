from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class StoredUpload:
    file_id: str
    filename: str
    path: Path
    summary: dict[str, Any]
    ingestion: dict[str, Any] | None = None


class SessionStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def create_session(self) -> str:
        session_id = f"sess_{uuid.uuid4().hex[:16]}"
        return self._create_session(session_id)

    def ensure_named_session(self, session_id: str | None) -> str:
        safe = self.safe_session_id(session_id or "")
        if not safe:
            return self.create_session()
        if not self.session_dir(safe).exists():
            self._create_session(safe)
        return safe

    def _create_session(self, session_id: str) -> str:
        session_dir = self.session_dir(session_id)
        (session_dir / "uploads").mkdir(parents=True, exist_ok=True)
        (session_dir / "extracted").mkdir(parents=True, exist_ok=True)
        (session_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        self._write_json(
            session_dir / "manifest.json",
            {
                "session_id": session_id,
                "created_at": utc_now(),
                "updated_at": utc_now(),
                "uploads": [],
                "artifacts": [],
            },
        )
        self._write_json(session_dir / "messages.json", [])
        return session_id

    def ensure_session(self, session_id: str | None) -> str:
        safe = self.safe_session_id(session_id or "")
        if safe and self.session_dir(safe).exists():
            return safe
        return self.create_session()

    def session_dir(self, session_id: str) -> Path:
        return self.root / (self.safe_session_id(session_id) or "invalid_session")

    def safe_session_id(self, session_id: str) -> str:
        return "".join(ch for ch in session_id if ch.isalnum() or ch in "_-")

    def manifest(self, session_id: str) -> dict[str, Any]:
        return self._read_json(self.session_dir(session_id) / "manifest.json", {})

    def messages(self, session_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        messages = self._read_json(self.session_dir(session_id) / "messages.json", [])
        return messages[-limit:] if limit else messages

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        file_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        path = self.session_dir(session_id) / "messages.json"
        messages = self._read_json(path, [])
        messages.append(
            {
                "role": role,
                "content": content,
                "file_ids": file_ids or [],
                "metadata": metadata or {},
                "created_at": utc_now(),
            }
        )
        self._write_json(path, messages)
        self._touch_manifest(session_id)

    def save_upload(self, session_id: str, filename: str, data: bytes, summary: dict[str, Any]) -> StoredUpload:
        session_dir = self.session_dir(session_id)
        upload_dir = session_dir / "uploads"
        extracted_dir = session_dir / "extracted"
        upload_dir.mkdir(parents=True, exist_ok=True)
        extracted_dir.mkdir(parents=True, exist_ok=True)

        file_id = f"file_{uuid.uuid4().hex[:12]}"
        safe_name = self._safe_filename(filename)
        path = upload_dir / f"{file_id}_{safe_name}"
        path.write_bytes(data)

        summary_payload = {
            "file_id": file_id,
            "filename": filename,
            "stored_path": str(path),
            "summary": summary,
            "created_at": utc_now(),
        }
        self._write_json(extracted_dir / f"{file_id}.json", summary_payload)

        manifest = self.manifest(session_id)
        manifest.setdefault("uploads", []).append(summary_payload)
        manifest["updated_at"] = utc_now()
        self._write_json(session_dir / "manifest.json", manifest)
        return StoredUpload(file_id=file_id, filename=filename, path=path, summary=summary)

    def update_upload_ingestion(self, session_id: str, file_id: str, ingestion: dict[str, Any]) -> None:
        session_dir = self.session_dir(session_id)
        manifest = self.manifest(session_id)
        for item in manifest.get("uploads", []):
            if item.get("file_id") == file_id:
                item["ingestion"] = ingestion
                break
        manifest["updated_at"] = utc_now()
        self._write_json(session_dir / "manifest.json", manifest)

        extracted_path = session_dir / "extracted" / f"{file_id}.json"
        extracted = self._read_json(extracted_path, {})
        if extracted:
            extracted["ingestion"] = ingestion
            self._write_json(extracted_path, extracted)

    def record_generated_artifacts(self, session_id: str, artifacts: dict[str, Any]) -> None:
        manifest = self.manifest(session_id)
        manifest.setdefault("artifacts", []).append({"created_at": utc_now(), **artifacts})
        manifest["updated_at"] = utc_now()
        self._write_json(self.session_dir(session_id) / "manifest.json", manifest)

    def copy_artifact(self, session_id: str, source: Path, label: str) -> Path:
        artifact_dir = self.session_dir(session_id) / "artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        target = artifact_dir / f"{label}_{source.name}"
        shutil.copy2(source, target)
        return target

    def context_summary(self, session_id: str) -> dict[str, Any]:
        manifest = self.manifest(session_id)
        return {
            "session_id": session_id,
            "recent_messages": self.messages(session_id, limit=8),
            "uploads": manifest.get("uploads", [])[-8:],
            "artifacts": manifest.get("artifacts", [])[-8:],
        }

    def _touch_manifest(self, session_id: str) -> None:
        path = self.session_dir(session_id) / "manifest.json"
        manifest = self._read_json(path, {})
        manifest["updated_at"] = utc_now()
        self._write_json(path, manifest)

    def _read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text())

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, default=str))

    def _safe_filename(self, filename: str) -> str:
        safe = "".join(ch if ch.isalnum() or ch in "._- " else "_" for ch in Path(filename).name)
        return safe.strip() or "upload"
