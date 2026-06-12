from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .workbook import SourceWorkbook


STANDARD_SECTIONS = {
    "balance_sheet": ["BS"],
    "income_statement": ["IS"],
    "investments": ["3. STI", "3a. MTM", "3b. Hedging"],
    "fixed_assets": ["6. Fixed Assets", "6a. Unpaid FA", "6b. Capitalized SBC"],
    "leases": ["4. Leases"],
    "sbc_equity": ["8. Equity RF", "8a. SBC Exp", "8b. SBC P&L"],
    "business_combinations": ["7. PPA"],
    "repurchases": ["9. Repurchase"],
    "reserves": ["10. CECL_E&O"],
    "other_investing": ["5. Sale of Origin Inv"],
}


@dataclass(frozen=True)
class NormalizedSupportItem:
    section_key: str
    source_sheet: str
    actual_sheet: str | None
    source_cell: str
    label: str
    value: Any
    status: str = "mapped"


def normalize_support(workbook: SourceWorkbook) -> list[NormalizedSupportItem]:
    """Map the uploaded workbook into the first standard support template.

    This first milestone keeps normalization intentionally conservative:
    it identifies the expected support tabs and records representative cells
    used by the cash-flow mapping/evidence layer.
    """

    items: list[NormalizedSupportItem] = []
    for section, sheets in STANDARD_SECTIONS.items():
        for sheet_name in sheets:
            ws = workbook.value_sheet(sheet_name)
            actual_sheet = workbook.actual_sheet_name(sheet_name)
            if ws is None:
                items.append(
                    NormalizedSupportItem(
                        section_key=section,
                        source_sheet=sheet_name,
                        actual_sheet=None,
                        source_cell="",
                        label=f"Missing required source sheet: {sheet_name}",
                        value=None,
                        status="missing",
                    )
                )
                continue
            for row in ws.iter_rows():
                label_cell = row[0]
                value_cells = [cell for cell in row[1:] if cell.value not in (None, "")]
                if label_cell.value not in (None, "") and value_cells:
                    first_value = value_cells[0]
                    items.append(
                        NormalizedSupportItem(
                            section_key=section,
                            source_sheet=sheet_name,
                            actual_sheet=actual_sheet,
                            source_cell=first_value.coordinate,
                            label=str(label_cell.value),
                            value=first_value.value,
                        )
                    )
                    break
    return items


def normalized_support_to_json(items: list[NormalizedSupportItem]) -> list[dict[str, Any]]:
    return [asdict(item) for item in items]
