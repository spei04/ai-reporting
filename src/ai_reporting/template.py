from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TemplateCell:
    cell: str
    value: Any = None
    formula: str | None = None


@dataclass(frozen=True)
class TemplateSheet:
    name: str
    cells: dict[str, TemplateCell]


class CashFlowTemplate:
    """Versioned standard template used to generate output tabs."""

    def __init__(self, version: str, sheets: dict[str, TemplateSheet]):
        self.version = version
        self.sheets = sheets

    @classmethod
    def load(cls, path: Path) -> "CashFlowTemplate":
        data = json.loads(path.read_text())
        sheets: dict[str, TemplateSheet] = {}
        for sheet_name, sheet_data in data["sheets"].items():
            cells = {
                item["cell"]: TemplateCell(
                    cell=item["cell"],
                    value=item.get("value"),
                    formula=item.get("formula"),
                )
                for item in sheet_data["cells"]
            }
            sheets[sheet_name] = TemplateSheet(name=sheet_name, cells=cells)
        return cls(version=data["version"], sheets=sheets)

