from __future__ import annotations

import argparse
import json
from pathlib import Path

from .knowledge_db import KnowledgeDatabase


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_ROOT = ROOT / "data" / "raw"
DEFAULT_DB_PATH = ROOT / "data" / "reporting_knowledge.db"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest ASC and SEC reference PDFs into the reporting knowledge database.")
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    db = KnowledgeDatabase(args.db)
    result = db.ingest_global_rules(args.raw_root)
    print(json.dumps({"database": str(args.db), "raw_root": str(args.raw_root), **result}, indent=2))


if __name__ == "__main__":
    main()
