from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MappingOverride:
    canonical_sheet: str
    canonical_cell: str
    actual_sheet: str
    actual_cell: str
    note: str | None = None


class ParserProfile:
    def __init__(self, overrides: dict[str, MappingOverride] | None = None):
        self.overrides = overrides or {}

    @classmethod
    def load(cls, path: Path | None) -> "ParserProfile":
        if path is None or not path.exists():
            return cls()
        data = json.loads(path.read_text())
        overrides = {
            _key(item["canonical_sheet"], item["canonical_cell"]): MappingOverride(
                canonical_sheet=item["canonical_sheet"],
                canonical_cell=item["canonical_cell"],
                actual_sheet=item["actual_sheet"],
                actual_cell=item["actual_cell"],
                note=item.get("note"),
            )
            for item in data.get("mapping_overrides", [])
        }
        return cls(overrides)

    def override_for(self, canonical_sheet: str, canonical_cell: str) -> MappingOverride | None:
        return self.overrides.get(_key(canonical_sheet, canonical_cell))

    def with_override(self, override: MappingOverride) -> "ParserProfile":
        overrides = dict(self.overrides)
        overrides[_key(override.canonical_sheet, override.canonical_cell)] = override
        return ParserProfile(overrides)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_json(), indent=2, default=str))

    def to_json(self) -> dict[str, Any]:
        return {
            "version": 1,
            "mapping_overrides": [
                asdict(override)
                for _, override in sorted(self.overrides.items())
            ],
        }


def _key(sheet_name: str, cell: str) -> str:
    return f"{sheet_name}!{cell}"
