from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import openpyxl

from .engine import CashFlowEngine

DETAILED_BRIDGE_SHEET = "2. 26Q1 QTD"


@dataclass(frozen=True)
class ValidationDifference:
    sheet: str
    cell: str
    generated: Any
    expected: Any
    delta: float | None


def compare_to_answer(
    engine: CashFlowEngine,
    answer_path: Path,
    tolerance: float = 1.0,
) -> list[ValidationDifference]:
    """Validate generated output against the development-only answer workbook.

    This intentionally validates only the second tab in `answer.xlsx`,
    `2. 26Q1 QTD`, because that detailed bridge is the engine's primary
    ground-truth test for the first milestone. The answer workbook must not be
    read during generation; it is read only here, after generation completes.
    """

    expected = openpyxl.load_workbook(answer_path, data_only=True, read_only=True)
    second_tab = expected.worksheets[1].title if len(expected.worksheets) >= 2 else None
    if second_tab != DETAILED_BRIDGE_SHEET:
        raise ValueError(
            f"Expected second answer workbook tab to be {DETAILED_BRIDGE_SHEET!r}; "
            f"found {second_tab!r}"
        )
    diffs: list[ValidationDifference] = []
    generated_values = engine._evaluate_all()

    checks = {
        DETAILED_BRIDGE_SHEET: [
            "B5", "B7", "B8", "B9", "B10", "B11", "B12", "B14", "B15", "B16",
            "B17", "B18", "B19", "B20", "B21", "B24", "B25", "B26", "B27",
            "B28", "B29", "B35", "B36", "B42", "B43", "B44", "B47", "B48", "B49",
        ],
    }

    for sheet_name, cells in checks.items():
        for cell in cells:
            generated = generated_values.get(sheet_name, {}).get(cell)
            expected_value = expected[sheet_name][cell].value
            delta = _delta(generated, expected_value)
            if delta is None:
                if generated != expected_value:
                    diffs.append(ValidationDifference(sheet_name, cell, generated, expected_value, None))
            elif abs(delta) > tolerance:
                diffs.append(ValidationDifference(sheet_name, cell, generated, expected_value, delta))
    return diffs


def _delta(left: Any, right: Any) -> float | None:
    try:
        return float(left) - float(right)
    except (TypeError, ValueError):
        return None
