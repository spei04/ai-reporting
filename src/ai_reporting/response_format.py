from __future__ import annotations

import re
from typing import Any


MAX_KEY_POINTS = 4


def format_chat_response(
    raw_text: str,
    citations: list[dict[str, Any]],
    support_state: dict[str, str] | None = None,
) -> dict[str, Any]:
    cleaned = clean_response_text(raw_text)
    parts = split_response_parts(cleaned)
    summary = parts[0] if parts else "I do not have enough context to answer that yet."
    key_points = parts[1 : 1 + MAX_KEY_POINTS]
    if not key_points and len(summary) > 220:
        sentences = split_sentences(summary)
        summary = " ".join(sentences[:2]).strip()
        key_points = sentences[2 : 2 + MAX_KEY_POINTS]

    source_citations = build_source_citations(citations)
    rule_support = [
        {"citation": item["citation"], "title": item["title"]}
        for item in source_citations
        if item.get("citation")
    ][:3]

    if support_state and support_state.get("status") == "no_source_found":
        summary = support_state["note"]

    payload = {
        "summary": polish_sentence(concise(summary, 360)),
        "key_points": [polish_sentence(concise(point, 240)) for point in key_points if point],
        "rule_support": rule_support,
        "source_citations": source_citations,
        "next_step": polish_sentence(next_step_for_response(cleaned)),
        "raw_answer": raw_text,
    }
    if support_state:
        payload["support_status"] = support_state.get("status")
        payload["support_label"] = support_state.get("label")
        payload["support_note"] = support_state.get("note")
    return payload


def build_source_citations(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    structured = []
    seen = set()
    for index, citation in enumerate(citations, start=1):
        label = clean_response_text(str(citation.get("citation") or citation.get("title") or "Source")).strip()
        title = clean_response_text(str(citation.get("title") or label)).strip()
        source_type = clean_response_text(str(citation.get("source") or "Source")).strip().upper()
        source_id = str(citation.get("chunk_id") or f"source_{index}")
        dedupe_key = (label, title, source_id)
        if not label or dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        structured.append(
            {
                "id": source_id,
                "number": len(structured) + 1,
                "source_type": source_type,
                "citation": label,
                "title": title,
                "location": clean_response_text(str(citation.get("location") or citation.get("page") or "")),
                "excerpt": concise(str(citation.get("text") or ""), 260),
                "path": str(citation.get("path") or ""),
                "score": citation.get("score"),
            }
        )
        if len(structured) >= 4:
            break
    return structured


def clean_response_text(text: str) -> str:
    value = str(text or "")
    value = value.replace("\u2014", " - ").replace("\u2013", " - ")
    value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    value = re.sub(r"__(.*?)__", r"\1", value)
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"^#{1,6}\s*", "", value, flags=re.MULTILINE)
    value = re.sub(r"^\s*[-*]\s+", "", value, flags=re.MULTILINE)
    value = re.sub(r"^\s*\d+[.)]\s+", "", value, flags=re.MULTILINE)
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = re.sub(r"\b(Yes|No|Sure|Okay|Ok) - ", r"\1, ", value)
    value = re.sub(r"([,;:]){2,}", r"\1", value)
    value = re.sub(r"([.!?]){2,}", r"\1", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def split_response_parts(text: str) -> list[str]:
    if not text:
        return []
    semicolon_parts = [part.strip() for part in text.split(";") if part.strip()]
    if 2 <= len(semicolon_parts) <= 5:
        return semicolon_parts
    sentences = split_sentences(text)
    if len(sentences) <= 1:
        return [text]
    summary = " ".join(sentences[:2]).strip()
    return [summary, *sentences[2:]]


def split_sentences(text: str) -> list[str]:
    protected = re.sub(r"\b(ASC|SEC|Reg|S-X|S-K)\.", lambda match: match.group(0).replace(".", "<DOT>"), text)
    pieces = re.split(r"(?<=[.!?])\s+", protected)
    return [piece.replace("<DOT>", ".").strip() for piece in pieces if piece.strip()]


def concise(text: str, limit: int) -> str:
    value = clean_response_text(text)
    if len(value) <= limit:
        return value
    clipped = value[: limit - 1].rsplit(" ", 1)[0].strip()
    return f"{clipped}."


def polish_sentence(text: str | None) -> str | None:
    if text is None:
        return None
    value = clean_response_text(text)
    if not value:
        return None
    value = value.strip(" ,;:")
    if not value:
        return None
    value = value[0].upper() + value[1:] if value[0].isalpha() else value
    if not re.search(r"[.!?]$", value):
        value = f"{value}."
    return value


def next_step_for_response(text: str) -> str | None:
    lower = text.lower()
    if "insufficient" in lower or "missing" in lower:
        return "Upload or identify the missing support, then ask me to refresh the analysis."
    if "cash flow" in lower or "statement of cash flows" in lower or "scf" in lower:
        return "Ask about a specific cash flow line if you want source support."
    if "filing" in lower or "regulation s-" in lower:
        return "Attach the approved statement or support schedule before drafting filing language."
    if "contract" in lower or "booking" in lower:
        return "Attach the contract and any company policy memo to draft a supported booking view."
    return None
