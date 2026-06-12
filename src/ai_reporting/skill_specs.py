from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .runtime import project_root


@dataclass(frozen=True)
class SkillSpec:
    skill_id: str
    path: Path
    content: str

    def to_context(self) -> dict[str, Any]:
        return {
            "id": self.skill_id,
            "source": str(self.path),
            "content": self.content,
        }


class SkillSpecStore:
    def __init__(self, specs_root: Path | None = None):
        self.specs_root = specs_root or project_root() / "config" / "skills"

    def load(self, skill_id: str) -> SkillSpec | None:
        safe_id = _safe_skill_id(skill_id)
        if not safe_id:
            return None
        path = self.specs_root / f"{safe_id}.md"
        if not path.exists():
            return None
        return SkillSpec(skill_id=safe_id, path=path, content=path.read_text())


def _safe_skill_id(skill_id: str) -> str:
    value = str(skill_id or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9_]+", value):
        return ""
    return value
