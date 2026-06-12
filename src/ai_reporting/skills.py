from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReportingSkill:
    id: str
    name: str
    purpose: str
    instruction: str
    keywords: tuple[str, ...]
    required_when: str

    def to_context(self) -> dict[str, str]:
        return {
            "id": self.id,
            "name": self.name,
            "purpose": self.purpose,
            "instruction": self.instruction,
            "required_when": self.required_when,
        }


@dataclass(frozen=True)
class SkillRoute:
    skill: ReportingSkill | None
    confidence: float = 0.0
    reason: str = ""

    @property
    def has_skill(self) -> bool:
        return self.skill is not None


SKILLS: tuple[ReportingSkill, ...] = (
    ReportingSkill(
        id="intake_context",
        name="Intake & Context",
        purpose="Clarify the request, identify missing inputs, and decide what reporting workflow should run.",
        instruction=(
            "Ask only for the missing information needed to proceed. Do not produce a final artifact until "
            "required inputs are available."
        ),
        keywords=("what do you need", "what information", "missing", "requirements", "help me start"),
        required_when="The user is trying to start a workflow but the needed files, amounts, dates, or scope are unclear.",
    ),
    ReportingSkill(
        id="source_file_parsing",
        name="Source File Parsing",
        purpose="Understand uploaded company files and map them into standard reporting context.",
        instruction=(
            "Summarize what was uploaded, identify tables/sheets/documents, and explain how the source data can be "
            "used in downstream reporting workflows."
        ),
        keywords=("parse", "uploaded file", "uploaded workbook", "spreadsheet", "support file", "template"),
        required_when="The user asks what is in an uploaded file or how uploaded support should be standardized.",
    ),
    ReportingSkill(
        id="scf_generation",
        name="SCF Generation",
        purpose="Generate a statement of cash flows summary and detailed bridge from support data.",
        instruction=(
            "Focus on standardized SCF generation. If a support workbook is missing, ask the user to upload it. "
            "If generation has already occurred, discuss the generated workbook and evidence artifacts."
        ),
        keywords=("scf", "cash flow", "statement of cash flows", "cash flows", "support workbook"),
        required_when="The user asks to draft, generate, review, or explain a statement of cash flows.",
    ),
    ReportingSkill(
        id="schedule_generation",
        name="Schedule Generation",
        purpose="Create standard reporting workpaper schedules such as debt, lease, depreciation, or rollforward schedules.",
        instruction=(
            "Identify the schedule type, collect only the missing assumptions required for that schedule, and return "
            "a downloadable artifact when the deterministic tool supports it."
        ),
        keywords=("schedule", "depreciation", "rollforward", "debt schedule", "lease schedule"),
        required_when="The user asks to build a reporting schedule or supporting workpaper.",
    ),
    ReportingSkill(
        id="source_trace_evidence",
        name="Source Trace & Evidence",
        purpose="Explain where a number came from and connect outputs to source files, formulas, evidence, and rules.",
        instruction=(
            "Prioritize evidence, source cells/files, formulas, and rule support. If the specific output value is "
            "unclear, ask which value or artifact to inspect."
        ),
        keywords=("source trace", "where did", "where this number", "evidence", "support", "tie", "trace"),
        required_when="The user asks where a reported value came from or whether it is supported.",
    ),
    ReportingSkill(
        id="rule_research",
        name="ASC/SEC Rule Research",
        purpose="Answer accounting and SEC rule questions using the shared ASC/SEC knowledge base.",
        instruction=(
            "Use retrieved ASC/SEC context first. Cite rule references when available, keep the answer concise, "
            "and identify missing facts if the rule conclusion depends on company-specific details."
        ),
        keywords=("asc", "sec", "regulation", "rule", "guidance", "accounting standard", "s-x", "s-k"),
        required_when="The user asks what accounting or SEC rules apply or requests a rule-backed explanation.",
    ),
    ReportingSkill(
        id="filing_draft",
        name="Filing Draft",
        purpose="Draft SEC filing sections from source financials, support schedules, and rule context.",
        instruction=(
            "Draft filing language only from available source support and retrieved rules. Separate draft text, "
            "required support, and open questions."
        ),
        keywords=("10-k", "10-q", "sec filing", "filing", "disclosure draft", "md&a", "footnote"),
        required_when="The user asks to draft or revise SEC filing content or financial statement disclosures.",
    ),
    ReportingSkill(
        id="disclosure_checklist",
        name="Disclosure Checklist",
        purpose="Identify likely required disclosures, support needs, and open reporting questions for a topic.",
        instruction=(
            "Return a compact checklist with required disclosures, supporting data needed, likely rule references, "
            "and unresolved judgments."
        ),
        keywords=(
            "checklist",
            "disclosures required",
            "what disclosures",
            "required disclosure",
            "disclosure requirements",
            "correct disclosures",
            "disclosures included",
            "missing disclosures",
            "disclosures missing",
            "disclosure completeness",
        ),
        required_when="The user asks what disclosures are required or what support should be prepared.",
    ),
    ReportingSkill(
        id="contract_accounting",
        name="Contract Accounting",
        purpose="Analyze contracts and draft accounting booking or memo support.",
        instruction=(
            "Focus on contract facts, accounting treatment, journal-entry implications, rule support, and missing "
            "contract terms. Do not assume terms not present in the source context."
        ),
        keywords=("contract", "booking", "memo", "revenue", "asc 606", "lease contract", "embedded derivative"),
        required_when="The user asks for contract accounting analysis, booking treatment, or a memo.",
    ),
    ReportingSkill(
        id="review_validation",
        name="Review & Validation",
        purpose="Check generated outputs for tie-outs, completeness, missing support, and rule coverage.",
        instruction=(
            "List review issues by severity, identify missing support and tie-out breaks, and distinguish validation "
            "results from judgmental review comments."
        ),
        keywords=("review", "validate", "tie-out", "tie out", "check", "errors", "missing support", "completeness"),
        required_when="The user asks whether generated reporting output is correct, complete, or review-ready.",
    ),
)


class SkillRouter:
    def __init__(self, skills: tuple[ReportingSkill, ...] = SKILLS):
        self.skills = skills

    def route(self, message: str, session_context: dict[str, Any] | None = None) -> SkillRoute:
        text = f" {message.lower()} "
        best_skill: ReportingSkill | None = None
        best_score = 0
        best_matches: list[str] = []

        for skill in self.skills:
            matches = [keyword for keyword in skill.keywords if keyword in text]
            score = len(matches)
            if skill.id == "rule_research" and any(token in text for token in (" asc ", " sec ")):
                score += 2
            if skill.id == "filing_draft" and "draft" in text and (
                "filing" in text or "disclosure" in text or "footnote" in text
            ):
                score += 2
            if skill.id == "disclosure_checklist" and (" disclosure" in text or " disclosures" in text) and any(
                term in text for term in (" correct", " included", " complete", " completeness", " missing")
            ):
                score += 3
            if score > best_score:
                best_skill = skill
                best_score = score
                best_matches = matches

        if not best_skill or best_score <= 0:
            return SkillRoute(skill=None, confidence=0.0, reason="No reporting skill matched with enough confidence.")

        confidence = min(0.95, 0.45 + 0.15 * best_score)
        reason = f"Matched: {', '.join(best_matches) if best_matches else best_skill.name}."
        return SkillRoute(skill=best_skill, confidence=confidence, reason=reason)
