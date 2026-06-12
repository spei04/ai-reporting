from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .file_context import csv_summary_text, pdf_text, workbook_summary_text
from .runtime import project_root


COMPLETENESS_TERMS = (
    "all the correct disclosures",
    "all required disclosures",
    "correct disclosures",
    "disclosures are included",
    "disclosures included",
    "disclosure completeness",
    "complete disclosure",
    "missing disclosures",
    "disclosures missing",
)


@dataclass(frozen=True)
class DisclosureChecklistItem:
    id: str
    label: str
    rule_reference: str
    required: bool
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class DisclosureTopic:
    id: str
    name: str
    topic_keywords: tuple[str, ...]
    items: tuple[DisclosureChecklistItem, ...]


@dataclass(frozen=True)
class DisclosureFinding:
    item_id: str
    label: str
    rule_reference: str
    status: str
    evidence: list[str]
    note: str


@dataclass(frozen=True)
class DisclosureReview:
    topic_id: str
    topic_name: str
    source_files: list[str]
    findings: list[DisclosureFinding]
    counts: dict[str, int]
    overall_status: str
    summary: str

    def to_json(self) -> dict[str, Any]:
        return {
            "topic_id": self.topic_id,
            "topic_name": self.topic_name,
            "source_files": self.source_files,
            "findings": [asdict(item) for item in self.findings],
            "counts": self.counts,
            "overall_status": self.overall_status,
            "summary": self.summary,
        }


class DisclosureChecklistEngine:
    def __init__(self, checklist_path: Path | None = None):
        self.checklist_path = checklist_path or project_root() / "config" / "disclosure_checklists.json"
        self.topics = self._load_topics()

    def review(self, message: str, uploads: list[dict[str, Any]]) -> DisclosureReview:
        documents = [_upload_text(upload) for upload in uploads]
        text = "\n\n".join(item["text"] for item in documents if item["text"])
        source_files = [item["filename"] for item in documents if item["filename"]]
        topic = self._select_topic(message, text)
        findings = [self._review_item(item, text) for item in topic.items]
        counts = _status_counts(findings)
        overall_status = _overall_status(counts)
        summary = _summary(topic.name, counts, bool(text))
        return DisclosureReview(
            topic_id=topic.id,
            topic_name=topic.name,
            source_files=source_files,
            findings=findings,
            counts=counts,
            overall_status=overall_status,
            summary=summary,
        )

    def _load_topics(self) -> tuple[DisclosureTopic, ...]:
        data = json.loads(self.checklist_path.read_text())
        topics = []
        for topic in data.get("topics", []):
            items = []
            for item in topic.get("items", []):
                items.append(
                    DisclosureChecklistItem(
                        id=str(item.get("id")),
                        label=str(item.get("label")),
                        rule_reference=str(item.get("rule_reference")),
                        required=bool(item.get("required", True)),
                        keywords=tuple(str(keyword).lower() for keyword in item.get("keywords", [])),
                    )
                )
            topics.append(
                DisclosureTopic(
                    id=str(topic.get("id")),
                    name=str(topic.get("name")),
                    topic_keywords=tuple(str(keyword).lower() for keyword in topic.get("topic_keywords", [])),
                    items=tuple(items),
                )
            )
        return tuple(topics)

    def _select_topic(self, message: str, text: str) -> DisclosureTopic:
        haystack = f"{message}\n{text[:5000]}".lower()
        scored = []
        for topic in self.topics:
            score = sum(3 for keyword in topic.topic_keywords if keyword in haystack)
            score += sum(1 for item in topic.items for keyword in item.keywords if keyword in haystack)
            scored.append((score, topic))
        scored.sort(key=lambda item: item[0], reverse=True)
        if scored and scored[0][0] > 0:
            return scored[0][1]
        for topic in self.topics:
            if topic.id == "general_financial_statement":
                return topic
        return self.topics[0]

    def _review_item(self, item: DisclosureChecklistItem, text: str) -> DisclosureFinding:
        if not text.strip():
            return DisclosureFinding(
                item_id=item.id,
                label=item.label,
                rule_reference=item.rule_reference,
                status="needs_facts",
                evidence=[],
                note="No extractable uploaded disclosure text was available for this item.",
            )

        evidence = _matching_evidence(text, item.keywords)
        if evidence:
            status = "included"
            note = "The uploaded disclosure appears to address this item."
        elif item.required:
            status = "missing"
            note = "I did not find this required disclosure area in the uploaded text."
        else:
            status = "needs_facts"
            note = "Applicability depends on company-specific facts."

        return DisclosureFinding(
            item_id=item.id,
            label=item.label,
            rule_reference=item.rule_reference,
            status=status,
            evidence=evidence,
            note=note,
        )


def is_disclosure_completeness_request(message: str, skill_id: str | None = None) -> bool:
    lower = f" {message.lower()} "
    if "disclosure" not in lower and "footnote" not in lower:
        return False
    if any(term in lower for term in COMPLETENESS_TERMS):
        return True
    if skill_id in {"disclosure_checklist", "review_validation"} and any(
        term in lower for term in (" included", " include ", " complete", " completeness", " correct", " missing")
    ):
        return True
    return False


def _upload_text(upload: dict[str, Any]) -> dict[str, str]:
    filename = str(upload.get("filename") or "")
    path = Path(str(upload.get("stored_path") or ""))
    summary = upload.get("summary") if isinstance(upload.get("summary"), dict) else {}
    suffix = Path(filename).suffix.lower()
    text = ""
    if path.exists():
        data = path.read_bytes()
        if suffix in {".txt", ".md"}:
            text = data.decode("utf-8", errors="replace")
        elif suffix == ".pdf":
            text = pdf_text(data) or str(summary.get("preview") or "")
    if not text:
        if suffix == ".xlsx":
            text = workbook_summary_text(summary)
        elif suffix == ".csv":
            text = csv_summary_text(summary)
        else:
            text = str(summary.get("preview") or summary)
    return {"filename": filename, "text": text}


def _matching_evidence(text: str, keywords: tuple[str, ...]) -> list[str]:
    clean = re.sub(r"\s+", " ", text or "")
    lower = clean.lower()
    snippets = []
    for keyword in keywords:
        index = lower.find(keyword)
        if index < 0:
            continue
        start = max(0, index - 90)
        end = min(len(clean), index + len(keyword) + 120)
        snippets.append(clean[start:end].strip())
        if len(snippets) >= 3:
            break
    return snippets


def _status_counts(findings: list[DisclosureFinding]) -> dict[str, int]:
    counts = {"included": 0, "incomplete": 0, "missing": 0, "needs_facts": 0}
    for finding in findings:
        counts[finding.status] = counts.get(finding.status, 0) + 1
    return counts


def _overall_status(counts: dict[str, int]) -> str:
    if counts.get("missing", 0):
        return "missing_items"
    if counts.get("incomplete", 0):
        return "incomplete"
    if counts.get("needs_facts", 0):
        return "needs_facts"
    return "appears_complete"


def _summary(topic_name: str, counts: dict[str, int], has_text: bool) -> str:
    if not has_text:
        return f"I could not extract enough text to test the {topic_name} disclosure checklist."
    if counts.get("missing", 0):
        return (
            f"The uploaded document does not appear complete for the {topic_name} checklist. "
            f"I found {counts['included']} included item(s), {counts['incomplete']} incomplete item(s), "
            f"and {counts['missing']} missing item(s)."
        )
    if counts.get("incomplete", 0):
        return (
            f"The uploaded document partially covers the {topic_name} checklist. "
            f"I found {counts['included']} included item(s) and {counts['incomplete']} item(s) needing more detail."
        )
    return f"The uploaded document appears to cover the {topic_name} checklist items I could test."
