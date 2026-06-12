from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .normalize import STANDARD_SECTIONS
from .source_map import SourceCellSignature
from .workbook import SourceWorkbook


@dataclass(frozen=True)
class MappingReviewItem:
    section_key: str
    canonical_sheet: str
    canonical_cell: str
    actual_sheet: str | None
    actual_cell: str | None
    status: str
    confidence: float
    row_label: str | None
    column_label: str | None
    expected_formula: str | None
    actual_formula: Any
    value: Any
    review_note: str


def build_mapping_review(workbook: SourceWorkbook) -> list[MappingReviewItem]:
    if workbook.source_map is None:
        return []

    items: list[MappingReviewItem] = []
    for signature in sorted(
        workbook.source_map.signatures.values(),
        key=lambda item: (item.canonical_sheet, item.canonical_cell),
    ):
        items.append(_review_signature(workbook, signature))
    return items


def mapping_review_to_json(items: list[MappingReviewItem]) -> list[dict[str, Any]]:
    return [asdict(item) for item in items]


def _review_signature(workbook: SourceWorkbook, signature: SourceCellSignature) -> MappingReviewItem:
    actual_sheet = workbook.resolve_cell_sheet(signature.canonical_sheet, signature.canonical_cell)
    actual_cell = None
    actual_formula = None
    value = None

    if actual_sheet is not None:
        actual_cell = workbook.actual_cell_name(signature.canonical_sheet, signature.canonical_cell)
        actual_formula = workbook.formula(signature.canonical_sheet, signature.canonical_cell)
        value = workbook.value(signature.canonical_sheet, signature.canonical_cell)

    status = workbook.cell_resolution_status(signature.canonical_sheet, signature.canonical_cell)
    return MappingReviewItem(
        section_key=_section_for_sheet(signature.canonical_sheet),
        canonical_sheet=signature.canonical_sheet,
        canonical_cell=signature.canonical_cell,
        actual_sheet=actual_sheet,
        actual_cell=actual_cell,
        status=status,
        confidence=_confidence(status, signature),
        row_label=signature.row_label,
        column_label=signature.column_label,
        expected_formula=signature.formula,
        actual_formula=actual_formula,
        value=value,
        review_note=_review_note(status, signature),
    )


def _section_for_sheet(sheet_name: str) -> str:
    for section, sheets in STANDARD_SECTIONS.items():
        if sheet_name in sheets:
            return section
    if sheet_name.startswith("26Q"):
        return "prior_period_support"
    return "template_support"


def _confidence(status: str, signature: SourceCellSignature) -> float:
    if status == "manual_override":
        return 1.0
    if status == "exact":
        return 1.0
    if status == "moved":
        return 0.95 if signature.formula else 0.8
    if status == "unmapped":
        return 0.6
    return 0.0


def _review_note(status: str, signature: SourceCellSignature) -> str:
    if status == "manual_override":
        return "Using reviewer-approved parser profile override."
    if status == "exact":
        return "Matched expected source location."
    if status == "moved":
        if signature.formula:
            return "Found by formula signature after layout movement."
        return "Found by nearby row/column labels after layout movement."
    if status == "missing_sheet":
        return "Required source sheet was not found in the uploaded workbook."
    if status == "needs_review":
        return "Could not confidently match the learned source signature."
    return "No learned source signature was available for this cell."
