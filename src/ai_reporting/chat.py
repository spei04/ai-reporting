from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .amortization import (
    generate_amortization_workbook,
    is_amortization_request,
    missing_amortization_inputs,
    parse_amortization_terms,
)
from .disclosure import DisclosureChecklistEngine, is_disclosure_completeness_request
from .evidence import classify_support_status
from .file_context import summarize_upload
from .knowledge import ReportingKnowledgeBase
from .llm import ReportingLlmClient
from .reporting_prompt import REPORTING_SYSTEM_PROMPT
from .response_format import format_chat_response
from .runtime import prepare_runtime_knowledge_db, runtime_path
from .session_store import SessionStore, StoredUpload
from .skill_specs import SkillSpecStore
from .skills import SkillRouter


RULE_CONTEXT_SKILLS = {
    "accounting_memo_draft",
    "contract_accounting",
    "disclosure_draft_redline",
    "disclosure_checklist",
    "filing_draft",
    "rule_to_claim_coverage",
    "review_validation",
    "rule_research",
    "scf_generation",
    "source_trace_evidence",
    "xbrl_filing_mechanics",
}


class ReportingChatService:
    def __init__(
        self,
        store: SessionStore,
        knowledge: ReportingKnowledgeBase,
        llm: ReportingLlmClient,
        skill_router: SkillRouter | None = None,
        skill_specs: SkillSpecStore | None = None,
        disclosure_engine: DisclosureChecklistEngine | None = None,
    ):
        self.store = store
        self.knowledge = knowledge
        self.llm = llm
        self.skill_router = skill_router or SkillRouter()
        self.skill_specs = skill_specs or SkillSpecStore()
        self.disclosure_engine = disclosure_engine or DisclosureChecklistEngine()

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

        skill_context = skill_route.skill.to_context() if skill_route.has_skill and skill_route.skill else None
        skill_spec = self.skill_specs.load(skill_route.skill.id) if skill_route.has_skill and skill_route.skill else None
        if is_disclosure_completeness_request(message, skill_context.get("id") if skill_context else None):
            return self._handle_disclosure_completeness(
                resolved_session_id,
                message,
                stored_uploads,
                skill_context,
                skill_spec.to_context() if skill_spec else None,
            )
        retrieval_query = self._rule_retrieval_query(message, skill_context, skill_spec.to_context() if skill_spec else None)
        rule_chunks = self.knowledge.retrieve(retrieval_query, limit=5) if self._should_retrieve_rule_context(skill_route) else []
        user_chunks = self.knowledge.retrieve_user(resolved_session_id, message, limit=5)
        context_pack = {
            "permanent_reporting_instruction": "System prompt is applied separately on every model request.",
        }
        if skill_context:
            context_pack["selected_reporting_skill"] = skill_context
            context_pack["skill_routing"] = {
                "confidence": skill_route.confidence,
                "reason": skill_route.reason,
            }
        if skill_spec:
            context_pack["selected_skill_spec"] = skill_spec.to_context()
        context_pack.update(
            {
                "retrieved_reporting_guidance": [chunk.to_json() for chunk in rule_chunks],
                "retrieved_user_context": [chunk.to_json() for chunk in user_chunks],
                "session_context": session_context,
                "user_question": message,
            }
        )
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
                "selected_skill_spec": skill_spec.to_context() if skill_spec else None,
                "support_state": support_state,
            },
        )

        payload = {
            "status": "answered",
            "session_id": resolved_session_id,
            "answer": display["summary"],
            "raw_answer": llm_response.text,
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
        if skill_spec:
            payload["selected_skill_spec"] = {
                "id": skill_spec.skill_id,
                "source": str(skill_spec.path),
            }
        return payload

    def _should_retrieve_rule_context(self, skill_route) -> bool:
        if not skill_route.has_skill or not skill_route.skill:
            return False
        return skill_route.skill.id in RULE_CONTEXT_SKILLS

    def _rule_retrieval_query(
        self,
        message: str,
        skill_context: dict[str, str] | None,
        skill_spec: dict[str, Any] | None,
    ) -> str:
        if not skill_context:
            return message
        hints = {
            "accounting_memo_draft": "ASC accounting memo technical accounting guidance recognition measurement disclosure",
            "contract_accounting": "ASC 606 ASC 842 contract accounting revenue lease recognition",
            "disclosure_draft_redline": "ASC SEC disclosure filing language Regulation S-K Regulation S-X",
            "disclosure_checklist": "ASC SEC disclosure requirements checklist Regulation S-K Regulation S-X",
            "filing_draft": "SEC Regulation S-X Regulation S-K financial statement disclosure MD&A footnote",
            "rule_to_claim_coverage": "ASC SEC rule support disclosure claim source evidence Regulation S-K Regulation S-X",
            "review_validation": "ASC SEC review validation tie-out disclosure source support",
            "rule_research": "ASC SEC accounting guidance reporting rule",
            "scf_generation": "ASC 230 statement of cash flows operating investing financing activities noncash disclosures",
            "source_trace_evidence": "ASC SEC source support evidence reporting tie-out",
            "xbrl_filing_mechanics": "SEC EDGAR XBRL inline XBRL exhibit cover page filing requirements",
        }
        skill_id = skill_context.get("id", "")
        spec_preview = ""
        if skill_spec:
            spec_preview = str(skill_spec.get("content", ""))[:800]
        return " ".join(part for part in [message, hints.get(skill_id, ""), spec_preview] if part)

    def _should_handle_amortization(self, session_id: str, message: str) -> bool:
        if is_amortization_request(message):
            return True
        recent = self.store.messages(session_id, limit=4)
        return any(is_amortization_request(str(item.get("content", ""))) for item in recent)

    def _handle_disclosure_completeness(
        self,
        session_id: str,
        message: str,
        stored_uploads,
        selected_skill: dict[str, str] | None,
        selected_skill_spec: dict[str, Any] | None,
    ) -> dict[str, Any]:
        uploads = self.store.manifest(session_id).get("uploads", [])
        review = self.disclosure_engine.review(message, uploads)
        review_json = review.to_json()
        artifact_dir = self.store.session_dir(session_id) / "artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = artifact_dir / "disclosure_completeness_review.json"
        artifact_path.write_text(json.dumps(review_json, indent=2, default=str))
        self.store.record_generated_artifacts(
            session_id,
            {
                "disclosure_completeness_review": str(artifact_path),
            },
        )
        artifact = {
            "title": "Disclosure completeness review",
            "description": f"Checklist review for {review.topic_name}.",
            "href": f"/data/sessions/{session_id}/artifacts/{artifact_path.name}",
            "type": "json",
        }
        display = self._disclosure_display(review)
        self.store.append_message(
            session_id,
            "assistant",
            display["summary"],
            metadata={
                "display": display,
                "provider": "deterministic-tool",
                "model": "disclosure-completeness",
                "used_live_model": False,
                "selected_skill": selected_skill,
                "selected_skill_spec": selected_skill_spec,
                "disclosure_review": review_json,
                "artifacts": [artifact],
            },
        )
        payload = self._chat_payload(
            session_id,
            display,
            stored_uploads,
            provider="deterministic-tool",
            model="disclosure-completeness",
            selected_skill=selected_skill,
        )
        payload["artifacts"] = [artifact]
        payload["disclosure_review"] = review_json
        if selected_skill_spec:
            payload["selected_skill_spec"] = {
                "id": selected_skill_spec.get("id"),
                "source": selected_skill_spec.get("source"),
            }
        return payload

    def _disclosure_display(self, review) -> dict[str, Any]:
        critical = [
            item for item in review.findings
            if item.status in {"missing", "incomplete", "needs_facts"}
        ][:4]
        if critical:
            key_points = [
                f"{item.status.replace('_', ' ').title()}: {item.label}"
                for item in critical
            ]
        else:
            key_points = ["No missing checklist items were detected in the uploaded text."]
        return {
            "summary": review.summary,
            "key_points": key_points,
            "rule_support": _disclosure_rule_support(review),
            "next_step": "Review the checklist statuses and provide missing company facts before relying on completeness.",
            "raw_answer": review.summary,
            "checklist_items": [
                {
                    "item": item.label,
                    "status": item.status.replace("_", " ").title(),
                    "rule": item.rule_reference,
                    "note": item.note,
                    "evidence": item.evidence[:1],
                }
                for item in review.findings
            ],
            "support_status": "supported" if review.overall_status == "appears_complete" else "partially_supported",
            "support_label": "Checklist reviewed",
            "support_note": "This is a deterministic checklist review, not a legal or audit sign-off.",
        }

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
            "raw_answer": display.get("raw_answer", display["summary"]),
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


def _disclosure_rule_support(review) -> list[dict[str, str]]:
    seen = set()
    support = []
    for item in review.findings:
        citation = item.rule_reference
        if not citation or citation in seen:
            continue
        seen.add(citation)
        support.append({"citation": citation, "title": citation})
        if len(support) >= 3:
            break
    return support


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
