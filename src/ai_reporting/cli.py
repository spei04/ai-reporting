from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import CashFlowEngine
from .parser_profile import ParserProfile
from .source_map import SourceCellMap
from .template import CashFlowTemplate
from .validation import DETAILED_BRIDGE_SHEET, compare_to_answer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Q1 2026 SCF outputs from support data.")
    parser.add_argument("--input", required=True, type=Path, help="Path to source support workbook.")
    parser.add_argument("--template", required=True, type=Path, help="Path to standard cash flow template JSON.")
    parser.add_argument("--source-map", type=Path, help="Optional learned source-cell map JSON.")
    parser.add_argument("--parser-profile", type=Path, help="Optional company parser profile JSON.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for generated artifacts.")
    parser.add_argument("--answer", type=Path, help="Optional development answer workbook for golden validation.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    template = CashFlowTemplate.load(args.template)
    source_map = SourceCellMap.load(args.source_map)
    parser_profile = ParserProfile.load(args.parser_profile)
    engine = CashFlowEngine(args.input, template, source_map, parser_profile)
    result = engine.generate(args.output_dir)

    payload = {
        "output_workbook": str(result.output_workbook),
        "values_json": str(result.values_json),
        "evidence_json": str(result.evidence_json),
        "normalized_support_json": str(result.normalized_support_json),
        "workbook_profile_json": str(result.workbook_profile_json),
        "mapping_review_json": str(result.mapping_review_json),
    }

    if args.answer:
        diffs = compare_to_answer(engine, args.answer)
        payload["golden_validation"] = {
            "status": "passed" if not diffs else "failed",
            "answer_workbook_tab": DETAILED_BRIDGE_SHEET,
            "note": "answer.xlsx is read only after generation completes",
            "differences": [diff.__dict__ for diff in diffs],
        }

    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
