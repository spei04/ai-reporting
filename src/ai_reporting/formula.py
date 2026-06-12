from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from openpyxl.utils.cell import range_boundaries, get_column_letter


SHEET_REF_RE = re.compile(
    r"(?:'(?P<quoted>[^']+)'|(?P<plain>[A-Za-z0-9_. &]+))!"
    r"\$?(?P<col>[A-Z]{1,3})\$?(?P<row>\d+)"
)
_LOCAL_CELL_RE = re.compile(r"(?<![A-Za-z0-9_])\$?(?P<col>[A-Z]{1,3})\$?(?P<row>\d+)(?![A-Za-z0-9_])")
_SUM_RE = re.compile(r"SUM\((?P<arg>[^()]+)\)")
_ROUND_RE = re.compile(r"ROUND\(", re.IGNORECASE)


def _coerce_number(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, str) and value.startswith("#"):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class FormulaEvaluator:
    """Small deterministic evaluator for the Excel formulas used by the Q1 SCF fixture."""

    get_value: Callable[[str, str], Any]
    dependencies: dict[str, set[str]] = field(default_factory=dict)

    def evaluate(self, sheet_name: str, cell: str, formula: str) -> Any:
        expression = formula[1:] if formula.startswith("=") else formula
        expression = expression.replace("\u2212", "-")

        expression = self._replace_sheet_refs(expression, sheet_name, cell)
        expression = self._replace_sum_calls(expression, sheet_name, cell)
        expression = _ROUND_RE.sub("round(", expression)
        expression = self._replace_local_refs(expression, sheet_name, cell)

        try:
            return eval(expression, {"__builtins__": {}}, {"round": round})
        except Exception as exc:
            raise ValueError(f"Unsupported formula at {sheet_name}!{cell}: {formula}") from exc

    def _record_dependency(self, output_key: str, sheet_name: str, cell: str) -> None:
        self.dependencies.setdefault(output_key, set()).add(f"{sheet_name}!{cell}")

    def _replace_sheet_refs(self, expression: str, current_sheet: str, output_cell: str) -> str:
        output_key = f"{current_sheet}!{output_cell}"

        def replace(match: re.Match[str]) -> str:
            sheet = match.group("quoted") or match.group("plain")
            cell = f"{match.group('col')}{match.group('row')}"
            self._record_dependency(output_key, sheet, cell)
            return repr(_coerce_number(self.get_value(sheet, cell)))

        return SHEET_REF_RE.sub(replace, expression)

    def _replace_local_refs(self, expression: str, current_sheet: str, output_cell: str) -> str:
        output_key = f"{current_sheet}!{output_cell}"

        def replace(match: re.Match[str]) -> str:
            cell = f"{match.group('col')}{match.group('row')}"
            self._record_dependency(output_key, current_sheet, cell)
            return repr(_coerce_number(self.get_value(current_sheet, cell)))

        return _LOCAL_CELL_RE.sub(replace, expression)

    def _replace_sum_calls(self, expression: str, current_sheet: str, output_cell: str) -> str:
        while True:
            match = _SUM_RE.search(expression)
            if not match:
                return expression
            total = self._sum_arg(match.group("arg"), current_sheet, output_cell)
            expression = f"{expression[:match.start()]}{total!r}{expression[match.end():]}"

    def _sum_arg(self, arg: str, current_sheet: str, output_cell: str) -> float:
        output_key = f"{current_sheet}!{output_cell}"
        total = 0.0
        for part in arg.split(","):
            part = part.strip().replace("$", "")
            if ":" in part:
                start, end = part.split(":", 1)
                min_col, min_row, max_col, max_row = range_boundaries(f"{start}:{end}")
                for row in range(min_row, max_row + 1):
                    for col in range(min_col, max_col + 1):
                        cell = f"{get_column_letter(col)}{row}"
                        self._record_dependency(output_key, current_sheet, cell)
                        total += _coerce_number(self.get_value(current_sheet, cell))
            else:
                self._record_dependency(output_key, current_sheet, part)
                total += _coerce_number(self.get_value(current_sheet, part))
        return total
