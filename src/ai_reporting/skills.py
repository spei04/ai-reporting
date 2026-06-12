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
        id="tie_out_review",
        name="Tie-Out Review",
        purpose="Check whether a filing, disclosure, schedule, or generated output ties to source financial statements and support.",
        instruction=(
            "Compare reported amounts to source support, identify tie-out breaks, and separate mechanical differences "
            "from judgmental review comments."
        ),
        keywords=("tie-out", "tie out", "ties to", "does this tie", "agrees to", "reconcile to", "reconciliation"),
        required_when="The user asks whether numbers or disclosures agree to source financials, schedules, or workpapers.",
    ),
    ReportingSkill(
        id="variance_explanation",
        name="Variance Explanation",
        purpose="Explain period-over-period, budget-to-actual, or forecast-to-actual movements using uploaded support.",
        instruction=(
            "Identify the comparison basis, quantify the movement, explain drivers from source support, and flag "
            "unsupported explanations."
        ),
        keywords=("variance", "flux", "fluctuation", "quarter over quarter", "year over year", "qoq", "yoy", "budget to actual"),
        required_when="The user asks why balances, activity, KPIs, or disclosures changed between periods or against budget.",
    ),
    ReportingSkill(
        id="rule_to_claim_coverage",
        name="Rule-to-Claim Coverage",
        purpose="Check whether each claim, sentence, number, or disclosure assertion has source and rule support.",
        instruction=(
            "Break the text into reviewable claims, map each claim to source support and rule support, and identify "
            "unsupported or weakly supported claims."
        ),
        keywords=("claim support", "rule support", "supported by rules", "backed by rules", "coverage", "every claim", "every sentence"),
        required_when="The user asks whether disclosure statements or filing claims are backed by rules and source evidence.",
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
        id="disclosure_draft_redline",
        name="Disclosure Draft Redline",
        purpose="Rewrite or redline disclosure language while preserving source-backed facts and rule support.",
        instruction=(
            "Improve clarity and filing style without introducing unsupported facts. Separate revised text from "
            "review notes and source/rule support."
        ),
        keywords=("redline", "rewrite disclosure", "revise disclosure", "edit disclosure", "markup", "improve this disclosure"),
        required_when="The user asks to edit, redline, or rewrite disclosure language.",
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
        id="accounting_memo_draft",
        name="Accounting Memo Draft",
        purpose="Draft accounting memos from transaction facts, company policy, source support, and ASC/SEC guidance.",
        instruction=(
            "Structure the memo with facts, issue, authoritative guidance, analysis, conclusion, entries or impacts, "
            "and open questions. Do not assume missing facts."
        ),
        keywords=("accounting memo", "technical memo", "position memo", "memo draft", "accounting position", "technical accounting"),
        required_when="The user asks to draft a technical accounting memo or accounting position document.",
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
    ReportingSkill(
        id="reviewer_findings",
        name="Reviewer Findings",
        purpose="Produce audit-style review notes with severity, owner, source location, and recommended fix.",
        instruction=(
            "Lead with findings, group by severity, cite source locations, identify owners when clear, and recommend "
            "the smallest practical fix."
        ),
        keywords=("review notes", "review comments", "findings", "review findings", "audit comments", "open items", "review points"),
        required_when="The user wants reviewer-style findings or open items from a document, schedule, or generated output.",
    ),
    ReportingSkill(
        id="financial_statement_flux_analysis",
        name="Financial Statement Flux Analysis",
        purpose="Analyze balance sheet, income statement, or cash-flow movements and identify likely disclosure implications.",
        instruction=(
            "Use uploaded financial statements or support to identify material movements, drivers, and likely MD&A or "
            "footnote implications."
        ),
        keywords=("financial statement flux", "fs flux", "balance sheet flux", "income statement flux", "cash flow flux", "financial statement movement"),
        required_when="The user asks for financial statement movement analysis or disclosure implications.",
    ),
    ReportingSkill(
        id="close_package_review",
        name="Close Package Review",
        purpose="Review a reporting close package for missing schedules, stale support, broken links, and sign-off gaps.",
        instruction=(
            "Inventory the package, identify missing or stale support, check sign-off/readiness indicators, and return "
            "practical close review findings."
        ),
        keywords=("close package", "close binder", "month-end close", "quarter-end close", "close review", "support package"),
        required_when="The user asks whether a reporting close package is complete or ready for review.",
    ),
    ReportingSkill(
        id="xbrl_filing_mechanics",
        name="XBRL & Filing Mechanics",
        purpose="Handle SEC filing mechanics such as form requirements, exhibit checks, cover-page items, and XBRL considerations.",
        instruction=(
            "Focus on filing mechanics, required exhibits, form-specific checks, tagging considerations, and operational "
            "filing readiness."
        ),
        keywords=("xbrl", "ixbrl", "tagging", "edgar", "cover page", "exhibit", "filing mechanics", "form 10-k", "form 10-q"),
        required_when="The user asks about SEC filing mechanics, XBRL tagging, exhibits, or form readiness.",
    ),
    ReportingSkill(
        id="controls_evidence_review",
        name="Controls Evidence Review",
        purpose="Review SOX/control evidence for completeness, preparer/reviewer signoff, timing, and support quality.",
        instruction=(
            "Assess whether the evidence demonstrates control operation, includes preparer/reviewer attributes, and "
            "supports the control objective."
        ),
        keywords=("sox", "control evidence", "controls", "control review", "preparer", "reviewer signoff", "sign-off", "control owner"),
        required_when="The user asks whether control evidence is complete, sufficient, or review-ready.",
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
            if skill.id == "accounting_memo_draft" and "memo" in text and (
                "accounting" in text or "technical" in text or "position" in text
            ):
                score += 3
            if skill.id == "disclosure_draft_redline" and any(term in text for term in (" redline", " revise", " rewrite", " edit")) and (
                "disclosure" in text or "footnote" in text
            ):
                score += 3
            if skill.id == "disclosure_checklist" and (" disclosure" in text or " disclosures" in text) and any(
                term in text for term in (" correct", " included", " complete", " completeness", " missing")
            ):
                score += 3
            if skill.id == "tie_out_review" and (" tie" in text or " reconcile" in text or " agrees" in text):
                score += 2
            if skill.id == "rule_to_claim_coverage" and (" claim" in text or " sentence" in text) and (
                "support" in text or "rule" in text or "backed" in text
            ):
                score += 3
            if skill.id == "reviewer_findings" and any(
                term in text for term in (" finding", " findings", " review note", " review notes", " review comment")
            ):
                score += 3
            if skill.id == "financial_statement_flux_analysis" and (
                "financial statement" in text or "balance sheet" in text or "income statement" in text or "cash flow" in text
            ) and (" flux" in text or " movement" in text):
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
