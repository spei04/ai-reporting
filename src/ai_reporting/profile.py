from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable


CANONICAL_SHEET_ALIASES: dict[str, list[str]] = {
    "BS": ["bs", "balance sheet", "balance sheets", "fs-1 bs", "statement of financial position"],
    "IS": ["is", "income statement", "p&l", "profit and loss", "statement of operations"],
    "3. STI": ["3. sti", "sti", "short-term investments", "short term investments", "st investments"],
    "3a. MTM": ["3a. mtm", "mtm", "mark to market", "fair value"],
    "3b. Hedging": ["3b. hedging", "hedging", "hedge", "fas 133"],
    "4. Leases": ["4. leases", "leases", "lease"],
    "5. Sale of Origin Inv": [
        "5. sale of origin inv",
        "sale of origin inv",
        "sale of investment",
        "sale of strategic investment",
    ],
    "6. Fixed Assets": ["6. fixed assets", "fixed assets", "ppe", "pp&e", "property and equipment"],
    "6a. Unpaid FA": ["6a. unpaid fa", "unpaid fa", "unpaid fixed assets", "unpaid capex"],
    "6b. Capitalized SBC": ["6b. capitalized sbc", "capitalized sbc", "capitalized stock comp"],
    "7. PPA": ["7. ppa", "ppa", "purchase price allocation", "business acquisition"],
    "8. Equity RF": ["8. equity rf", "equity rf", "equity rollforward", "equity roll forward"],
    "8a. SBC Exp": ["8a. sbc exp", "sbc exp", "sbc expense", "stock-based compensation"],
    "8b. SBC P&L": ["8b. sbc p&l", "sbc p&l", "sbc pl", "stock comp p&l"],
    "9. Repurchase": ["9. repurchase", "repurchase", "stock repurchase", "share repurchase"],
    "10. CECL_E&O": ["10. cecl_e&o", "cecl_e&o", "cecl", "e&o", "reserves", "inventory reserve"],
}


@dataclass(frozen=True)
class SheetMatch:
    canonical_name: str
    actual_name: str | None
    confidence: float
    match_reason: str


@dataclass(frozen=True)
class WorkbookProfile:
    sheet_matches: dict[str, SheetMatch]

    def actual_sheet(self, canonical_name: str) -> str | None:
        match = self.sheet_matches.get(canonical_name)
        return match.actual_name if match else None

    def to_json(self) -> dict[str, object]:
        return {
            "sheet_matches": {
                key: asdict(value) for key, value in self.sheet_matches.items()
            }
        }


def build_workbook_profile(sheet_names: Iterable[str]) -> WorkbookProfile:
    names = list(sheet_names)
    normalized_to_actual = {_normalize_name(name): name for name in names}
    matches: dict[str, SheetMatch] = {}

    for canonical, aliases in CANONICAL_SHEET_ALIASES.items():
        actual = _find_sheet(canonical, aliases, normalized_to_actual)
        if actual:
            confidence = 1.0 if _normalize_name(actual) == _normalize_name(canonical) else 0.86
            reason = "exact_name" if confidence == 1.0 else "alias_match"
            matches[canonical] = SheetMatch(canonical, actual, confidence, reason)
        else:
            matches[canonical] = SheetMatch(canonical, None, 0.0, "not_found")

    return WorkbookProfile(matches)


def _find_sheet(
    canonical: str,
    aliases: list[str],
    normalized_to_actual: dict[str, str],
) -> str | None:
    canonical_norm = _normalize_name(canonical)
    if canonical_norm in normalized_to_actual:
        return normalized_to_actual[canonical_norm]

    for alias in aliases:
        alias_norm = _normalize_name(alias)
        if alias_norm in normalized_to_actual:
            return normalized_to_actual[alias_norm]

    for normalized_name, actual in normalized_to_actual.items():
        for alias in aliases:
            alias_norm = _normalize_name(alias)
            if alias_norm and (alias_norm in normalized_name or normalized_name in alias_norm):
                return actual

    return None


def _normalize_name(value: str) -> str:
    normalized = value.lower().replace("&", "and")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()

