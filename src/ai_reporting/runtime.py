from __future__ import annotations

import os
import shutil
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def is_vercel_runtime() -> bool:
    return bool(os.environ.get("VERCEL"))


def runtime_root(root: Path | None = None) -> Path:
    project = root or project_root()
    configured = os.environ.get("AI_REPORTING_RUNTIME_DIR", "").strip()
    if configured:
        return Path(configured)
    if is_vercel_runtime():
        return Path("/tmp/ai_reporting")
    return project


def runtime_path(*parts: str, root: Path | None = None) -> Path:
    return runtime_root(root).joinpath(*parts)


def prepare_runtime_knowledge_db(root: Path | None = None) -> Path:
    project = root or project_root()
    source = project / "data" / "reporting_knowledge.db"
    target = runtime_path("data", "reporting_knowledge.db", root=project)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return target
    if source.exists() and source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return target
