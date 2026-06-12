from __future__ import annotations

from typing import Any


SOURCE_HEAVY_SKILLS = {
    "contract_accounting",
    "filing_draft",
    "review_validation",
    "scf_generation",
    "source_file_parsing",
    "source_trace_evidence",
}


def classify_support_status(
    skill_context: dict[str, Any] | None,
    rule_chunks: list[dict[str, Any]],
    user_chunks: list[dict[str, Any]],
) -> dict[str, str] | None:
    if not skill_context and not rule_chunks and not user_chunks:
        return None

    skill_id = str((skill_context or {}).get("id") or "")
    if not rule_chunks and not user_chunks:
        return {
            "status": "no_source_found",
            "label": "No source found",
            "note": "I did not find relevant ASC/SEC guidance or session support for this reporting request.",
        }

    if skill_id in SOURCE_HEAVY_SKILLS and not user_chunks:
        return {
            "status": "partially_supported",
            "label": "Partially supported",
            "note": "I found rule context, but no company-specific support was retrieved for this workflow.",
        }

    if skill_id == "rule_research" and not rule_chunks:
        return {
            "status": "partially_supported",
            "label": "Partially supported",
            "note": "I found session context, but no authoritative ASC/SEC rule context was retrieved.",
        }

    return {
        "status": "supported",
        "label": "Source backed",
        "note": "This response is backed by retrieved reporting context.",
    }
