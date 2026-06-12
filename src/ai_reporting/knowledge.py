from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from .knowledge_db import KnowledgeChunk, KnowledgeDatabase


TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9-]*")


@dataclass(frozen=True)
class RuleChunk:
    chunk_id: str
    source: str
    citation: str
    title: str
    text: str
    path: str
    score: float = 0.0

    def to_json(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source": self.source,
            "citation": self.citation,
            "title": self.title,
            "text": self.text,
            "path": self.path,
            "score": round(self.score, 4),
        }


class ReportingKnowledgeBase:
    def __init__(self, reference_root: Path, cache_root: Path, database: KnowledgeDatabase | None = None):
        self.reference_root = reference_root
        self.asc_root = reference_root / "FASB Accounting Standard Codifications (ASC)"
        self.sec_root = reference_root / "SEC Regulation"
        self.cache_root = cache_root
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.database = database

    def retrieve(self, query: str, limit: int = 5) -> list[RuleChunk]:
        if self.database and self.database.global_document_count() > 0:
            return [_from_db_chunk(chunk) for chunk in self.database.retrieve_global(query, limit)]
        docs = self._rank_documents(query)[:5]
        chunks: list[RuleChunk] = []
        for doc in docs:
            chunks.extend(self._chunks_for_document(doc))
        scored = [self._score_chunk(query, chunk) for chunk in chunks]
        scored.sort(key=lambda chunk: chunk.score, reverse=True)
        return scored[:limit]

    def retrieve_user(self, session_id: str, query: str, limit: int = 5) -> list[RuleChunk]:
        if not self.database:
            return []
        return [_from_db_chunk(chunk) for chunk in self.database.retrieve_user(session_id, query, limit)]

    def ingest_user_document(
        self,
        session_id: str,
        file_id: str,
        filename: str,
        path: Path,
        data: bytes,
        summary: dict[str, Any],
    ) -> dict[str, int]:
        if not self.database:
            return {"documents": 0, "chunks": 0}
        return self.database.ingest_user_document(session_id, file_id, filename, path, data, summary)

    def _rank_documents(self, query: str) -> list[Path]:
        files = list(self.asc_root.glob("*.pdf")) + list(self.sec_root.glob("*.pdf"))
        query_tokens = set(_tokens(query))
        hints = _topic_hints(query)
        ranked = []
        for path in files:
            name_tokens = set(_tokens(path.stem))
            score = len(query_tokens & name_tokens) * 3
            for hint in hints:
                if hint.lower() in path.stem.lower():
                    score += 12
            if "sec" in query_tokens and "SEC Regulation" in str(path):
                score += 5
            if "filing" in query_tokens and "SEC Regulation" in str(path):
                score += 5
            ranked.append((score, path))
        ranked.sort(key=lambda item: (item[0], item[1].name), reverse=True)
        return [path for _, path in ranked[:8]]

    def _chunks_for_document(self, path: Path) -> list[RuleChunk]:
        cache_path = self.cache_root / f"{_safe_id(path.stem)}.json"
        if cache_path.exists():
            return [RuleChunk(**item) for item in json.loads(cache_path.read_text())]

        chunks = self._extract_pdf_chunks(path)
        cache_path.write_text(json.dumps([chunk.to_json() for chunk in chunks], indent=2))
        return chunks

    def _extract_pdf_chunks(self, path: Path) -> list[RuleChunk]:
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(path.read_bytes()))
            chunks = []
            for page_index, page in enumerate(reader.pages, start=1):
                text = _clean_text(page.extract_text() or "")
                for chunk_index, text_chunk in enumerate(_chunk_text(text), start=1):
                    citation = _citation_for_path(path)
                    chunks.append(
                        RuleChunk(
                            chunk_id=f"{_safe_id(path.stem)}_p{page_index}_{chunk_index}",
                            source="SEC" if "SEC Regulation" in str(path) else "ASC",
                            citation=citation,
                            title=path.stem,
                            text=text_chunk,
                            path=str(path),
                        )
                    )
            return chunks or [self._metadata_chunk(path)]
        except Exception:
            return [self._metadata_chunk(path)]

    def _metadata_chunk(self, path: Path) -> RuleChunk:
        return RuleChunk(
            chunk_id=f"{_safe_id(path.stem)}_metadata",
            source="SEC" if "SEC Regulation" in str(path) else "ASC",
            citation=_citation_for_path(path),
            title=path.stem,
            text=f"Reference document available for retrieval: {path.stem}.",
            path=str(path),
        )

    def _score_chunk(self, query: str, chunk: RuleChunk) -> RuleChunk:
        query_tokens = set(_tokens(query))
        text_tokens = _tokens(f"{chunk.title} {chunk.citation} {chunk.text}")
        if not query_tokens or not text_tokens:
            return RuleChunk(**{**chunk.to_json(), "score": 0.0})
        counts: dict[str, int] = {}
        for token in text_tokens:
            counts[token] = counts.get(token, 0) + 1
        score = 0.0
        for token in query_tokens:
            if token in counts:
                score += 1.0 + math.log(counts[token])
        for hint in _topic_hints(query):
            if hint.lower() in chunk.title.lower() or hint.lower() in chunk.citation.lower():
                score += 8
        return RuleChunk(
            chunk_id=chunk.chunk_id,
            source=chunk.source,
            citation=chunk.citation,
            title=chunk.title,
            text=chunk.text,
            path=chunk.path,
            score=score,
        )


def _tokens(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def _topic_hints(query: str) -> list[str]:
    lower = query.lower()
    hints = []
    mapping = {
        "ASC 230": ["cash flow", "statement of cash flows", "scf", "operating activities", "investing activities", "financing activities"],
        "ASC 606": ["revenue", "contract with customer", "booking"],
        "ASC 842": ["lease", "rou asset", "right-of-use"],
        "ASC 718": ["stock compensation", "sbc", "share-based"],
        "ASC 805": ["business combination", "acquisition", "purchase price"],
        "ASC 820": ["fair value", "mark to market"],
        "ASC 326": ["credit loss", "cecl", "allowance"],
        "ASC 740": ["income tax", "deferred tax"],
        "ASC 270": ["interim", "quarter", "10-q"],
        "Regulation S-X": ["financial statement", "10-k", "10-q", "sec filing", "statement"],
        "Regulation S-K": ["md&a", "risk factor", "business description", "disclosure"],
    }
    for topic, phrases in mapping.items():
        if any(phrase in lower for phrase in phrases):
            hints.append(topic)
    return hints


def _citation_for_path(path: Path) -> str:
    if path.stem.startswith("ASC "):
        return path.stem.split(" - ", 1)[0]
    return path.stem.replace("SEC ", "")


def _chunk_text(text: str, size: int = 1600, overlap: int = 200) -> list[str]:
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return chunks


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def _from_db_chunk(chunk: KnowledgeChunk) -> RuleChunk:
    return RuleChunk(
        chunk_id=chunk.chunk_id,
        source=chunk.source,
        citation=chunk.citation,
        title=chunk.title,
        text=chunk.text,
        path=chunk.path,
        score=chunk.score,
    )
