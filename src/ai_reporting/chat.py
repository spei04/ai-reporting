from __future__ import annotations

from pathlib import Path
from typing import Any

from .amortization import (
    generate_amortization_workbook,
    is_amortization_request,
    missing_amortization_inputs,
    parse_amortization_terms,
)
from .evidence import classify_support_status
from .file_context import summarize_upload
from .knowledge import ReportingKnowledgeBase
from .llm import ReportingLlmClient
from .reporting_prompt import REPORTING_SYSTEM_PROMPT
from .response_format import format_chat_response
from .runtime import prepare_runtime_knowledge_db, runtime_path
from .session_store import SessionStore, StoredUpload
from .skills import SkillRouter


RULE_CONTEXT_SKILLS = {
    "contract_accounting",
    "disclosure_checklist",
    "filing_draft",
    "review_validation",
    "rule_research",
    "scf_generation",
    "source_trace_evidence",
}


class ReportingChatService:
    def __init__(
        self,
        store: SessionStore,
        knowledge: ReportingKnowledgeBase,
        llm: ReportingLlmClient,
        skill_router: SkillRouter | None = None,
    ):
        self.store = store
        self.knowledge = knowledge
        self.llm = llm
        self.skill_router = skill_router or SkillRouter()

    def handle_message(
        self,
        session_id: str | None,
        message: str,
        uploads: list[tuple[str, bytes]] | None = None,
    ) -> dict[str, Any]:
        resolved_session_id = self.store.ensure_session(session_id)
        stored_uploads = self._save_uploads(resolved_session_id, uploads or [])

        file_ids = [upload.file_id for upload in stored_uploads]
        self.store.append_message(resolved_session_id, "user", message, file_ids=file_ids)
        session_context = self.store.context_summary(resolved_session_id)
        skill_route = self.skill_router.route(message, session_context)

        if self._should_handle_amortization(resolved_session_id, message):
            return self._handle_amortization(resolved_session_id, message, stored_uploads)

        rule_chunks = self.knowledge.retrieve(message, limit=5) if self._should_retrieve_rule_context(skill_route) else []
        user_chunks = self.knowledge.retrieve_user(resolved_session_id, message, limit=5)
        context_pack = {
            "permanent_reporting_instruction": "System prompt is applied separately on every model request.",
            "retrieved_reporting_guidance": [chunk.to_json() for chunk in rule_chunks],
            "retrieved_user_context": [chunk.to_json() for chunk in user_chunks],
            "session_context": session_context,
            "user_question": message,
        }
        if skill_route.has_skill and skill_route.skill:
            context_pack["selected_reporting_skill"] = skill_route.skill.to_context()
            context_pack["skill_routing"] = {
                "confidence": skill_route.confidence,
                "reason": skill_route.reason,
            }
        skill_context = skill_route.skill.to_context() if skill_route.has_skill and skill_route.skill else None
        llm_response = self.llm.complete(REPORTING_SYSTEM_PROMPT, context_pack, message)
        citations = [chunk.to_json() for chunk in rule_chunks]
        user_context = [chunk.to_json() for chunk in user_chunks]
        support_state = classify_support_status(skill_context, citations, user_context)
        display = format_chat_response(llm_response.text, citations, support_state)
        source_citations = display.get("source_citations", [])
        self.store.append_message(
            resolved_session_id,
            "assistant",
            display["summary"],
            metadata={
                "raw_answer": llm_response.text,
                "display": display,
                "provider": llm_response.provider,
                "model": llm_response.model,
                "used_live_model": llm_response.used_live_model,
                "citations": source_citations,
                "retrieved_rule_context": citations,
                "user_context": user_context,
                "selected_skill": skill_context,
                "support_state": support_state,
            },
        )

        payload = {
            "status": "answered",
            "session_id": resolved_session_id,
            "answer": display["summary"],
            "display": display,
            "provider": llm_response.provider,
            "model": llm_response.model,
            "used_live_model": llm_response.used_live_model,
            "citations": source_citations,
            "user_context": user_context,
            "uploaded_files": [
                self._upload_payload(upload)
                for upload in stored_uploads
            ],
        }
        if skill_context:
            payload["selected_skill"] = skill_context
        return payload

    def _should_retrieve_rule_context(self, skill_route) -> bool:
        if not skill_route.has_skill or not skill_route.skill:
            return False
        return skill_route.skill.id in RULE_CONTEXT_SKILLS

    def _should_handle_amortization(self, session_id: str, message: str) -> bool:
        if is_amortization_request(message):
            return True
        recent = self.store.messages(session_id, limit=4)
        return any(is_amortization_request(str(item.get("content", ""))) for item in recent)

    def _handle_amortization(self, session_id: str, message: str, stored_uploads) -> dict[str, Any]:
        terms = parse_amortization_terms(message, self.store.messages(session_id, limit=8))
        missing = missing_amortization_inputs(terms)
        if missing:
            summary = (
                f"I can generate the {terms.years or 3}-year fixed-rate amortization schedule. "
                "Please provide the principal amount and fixed annual interest rate."
            )
            display = {
                "summary": summary,
                "key_points": [],
                "rule_support": [],
                "next_step": "For example: principal amount is $100,000 and interest rate is 6%.",
                "raw_answer": summary,
            }
            self.store.append_message(
                session_id,
                "assistant",
                summary,
                metadata={
                    "display": display,
                    "provider": "deterministic-tool",
                    "model": "amortization-schedule",
                    "used_live_model": False,
                },
            )
            return self._chat_payload(
                session_id,
                display,
                stored_uploads,
                provider="deterministic-tool",
                model="amortization-schedule",
            )

        artifact_dir = self.store.session_dir(session_id) / "artifacts"
        workbook_path = artifact_dir / "amortization_schedule.xlsx"
        metrics = generate_amortization_workbook(terms, workbook_path)
        self.store.record_generated_artifacts(
            session_id,
            {
                "amortization_workbook": str(workbook_path),
            },
        )
        artifact = {
            "title": "Amortization schedule",
            "description": (
                f"Monthly fixed-rate schedule over {terms.years} years, "
                f"with {metrics['payment_count']} payments."
            ),
            "href": f"/data/sessions/{session_id}/artifacts/{workbook_path.name}",
            "type": "xlsx",
        }
        summary = (
            "Generated the amortization schedule in Excel. "
            f"Scheduled monthly payment is ${metrics['scheduled_payment']:,.2f}; "
            f"total interest is ${metrics['total_interest']:,.2f}."
        )
        display = {
            "summary": summary,
            "key_points": [
                f"Principal: ${metrics['principal']:,.2f}",
                f"Fixed annual interest rate: {metrics['annual_rate']:.2%}",
                f"Term: {metrics['years']} years",
            ],
            "rule_support": [],
            "next_step": "Download the workbook to review the full payment-by-payment schedule.",
            "raw_answer": summary,
        }
        self.store.append_message(
            session_id,
            "assistant",
            summary,
            metadata={
                "display": display,
                "provider": "deterministic-tool",
                "model": "amortization-schedule",
                "used_live_model": False,
                "artifacts": [artifact],
            },
        )
        payload = self._chat_payload(
            session_id,
            display,
            stored_uploads,
            provider="deterministic-tool",
            model="amortization-schedule",
        )
        payload["artifacts"] = [artifact]
        return payload

    def _chat_payload(
        self,
        session_id: str,
        display: dict[str, Any],
        stored_uploads,
        provider: str,
        model: str,
        used_live_model: bool = False,
        selected_skill: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "status": "answered",
            "session_id": session_id,
            "answer": display["summary"],
            "display": display,
            "provider": provider,
            "model": model,
            "used_live_model": used_live_model,
            "citations": [],
            "user_context": [],
            "uploaded_files": [
                self._upload_payload(upload)
                for upload in stored_uploads
            ],
        }
        if selected_skill:
            payload["selected_skill"] = selected_skill
        return payload

    def store_uploads(self, session_id: str | None, uploads: list[tuple[str, bytes]]) -> dict[str, Any]:
        resolved_session_id = self.store.ensure_session(session_id)
        stored_uploads = self._save_uploads(resolved_session_id, uploads)
        if stored_uploads:
            self.store.append_message(
                resolved_session_id,
                "user",
                f"Uploaded {len(stored_uploads)} file(s) to session context.",
                file_ids=[upload.file_id for upload in stored_uploads],
                metadata={"event": "session_upload"},
            )
        return {
            "status": "uploaded",
            "session_id": resolved_session_id,
            "uploaded_files": [
                self._upload_payload(upload)
                for upload in stored_uploads
            ],
        }

    def _save_uploads(self, session_id: str, uploads: list[tuple[str, bytes]]):
        stored_uploads = []
        for filename, data in uploads:
            if not filename or not data:
                continue
            summary = summarize_upload(filename, data)
            stored = self.store.save_upload(session_id, filename, data, summary)
            try:
                result = self.knowledge.ingest_user_document(
                    session_id,
                    stored.file_id,
                    stored.filename,
                    stored.path,
                    data,
                    stored.summary,
                )
                chunk_count = int(result.get("chunks", 0))
                ingestion = {
                    "status": "indexed" if chunk_count else "partial",
                    "chunk_count": chunk_count,
                    "message": "Indexed for this session." if chunk_count else "Stored, but no searchable text was extracted.",
                }
            except Exception as error:
                ingestion = {
                    "status": "failed",
                    "chunk_count": 0,
                    "message": f"Stored, but indexing failed: {error}",
                }
            self.store.update_upload_ingestion(session_id, stored.file_id, ingestion)
            stored = StoredUpload(
                file_id=stored.file_id,
                filename=stored.filename,
                path=stored.path,
                summary=stored.summary,
                ingestion=ingestion,
            )
            stored_uploads.append(stored)
        return stored_uploads

    def _upload_payload(self, upload) -> dict[str, Any]:
        return {
            "file_id": upload.file_id,
            "filename": upload.filename,
            "summary": upload.summary,
            "ingestion": upload.ingestion or {},
        }


def build_chat_service(root: Path) -> ReportingChatService:
    from .knowledge_db import KnowledgeDatabase

    store = SessionStore(runtime_path("data", "sessions", root=root))
    db = KnowledgeDatabase(prepare_runtime_knowledge_db(root))
    if db.global_document_count() == 0:
        db.ingest_seed_rules(root / "data" / "reporting_knowledge_seed.json")
    knowledge = ReportingKnowledgeBase(
        root / "data" / "raw",
        runtime_path("data", "knowledge", root=root),
        db,
    )
    return ReportingChatService(store, knowledge, ReportingLlmClient())
