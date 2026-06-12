from __future__ import annotations

import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

from .file_context import extract_text_chunks


TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9-]*")


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    scope: str
    source: str
    citation: str
    title: str
    text: str
    path: str
    score: float = 0.0
    session_id: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "scope": self.scope,
            "source": self.source,
            "citation": self.citation,
            "title": self.title,
            "text": self.text,
            "path": self.path,
            "score": round(self.score, 4),
            "session_id": self.session_id,
        }


class KnowledgeDatabase:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS global_documents (
                  document_id TEXT PRIMARY KEY,
                  source_type TEXT NOT NULL,
                  title TEXT NOT NULL,
                  citation TEXT NOT NULL,
                  path TEXT NOT NULL UNIQUE,
                  metadata_json TEXT NOT NULL DEFAULT '{}',
                  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS global_rule_chunks (
                  chunk_id TEXT PRIMARY KEY,
                  document_id TEXT NOT NULL,
                  source_type TEXT NOT NULL,
                  citation TEXT NOT NULL,
                  title TEXT NOT NULL,
                  text TEXT NOT NULL,
                  page_number INTEGER,
                  token_text TEXT NOT NULL,
                  metadata_json TEXT NOT NULL DEFAULT '{}',
                  FOREIGN KEY(document_id) REFERENCES global_documents(document_id)
                );

                CREATE TABLE IF NOT EXISTS global_rule_edges (
                  edge_id TEXT PRIMARY KEY,
                  from_id TEXT NOT NULL,
                  to_id TEXT NOT NULL,
                  edge_type TEXT NOT NULL,
                  metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS user_documents (
                  document_id TEXT PRIMARY KEY,
                  session_id TEXT NOT NULL,
                  file_id TEXT,
                  filename TEXT NOT NULL,
                  source_type TEXT NOT NULL,
                  path TEXT NOT NULL,
                  metadata_json TEXT NOT NULL DEFAULT '{}',
                  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_document_chunks (
                  chunk_id TEXT PRIMARY KEY,
                  document_id TEXT NOT NULL,
                  session_id TEXT NOT NULL,
                  source_type TEXT NOT NULL,
                  title TEXT NOT NULL,
                  text TEXT NOT NULL,
                  token_text TEXT NOT NULL,
                  metadata_json TEXT NOT NULL DEFAULT '{}',
                  FOREIGN KEY(document_id) REFERENCES user_documents(document_id)
                );

                CREATE TABLE IF NOT EXISTS user_document_edges (
                  edge_id TEXT PRIMARY KEY,
                  session_id TEXT NOT NULL,
                  from_id TEXT NOT NULL,
                  to_id TEXT NOT NULL,
                  edge_type TEXT NOT NULL,
                  metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_global_chunks_token_text ON global_rule_chunks(token_text);
                CREATE INDEX IF NOT EXISTS idx_user_chunks_session ON user_document_chunks(session_id);
                """
            )

    def ingest_global_rules(self, raw_root: Path) -> dict[str, int]:
        files = list((raw_root / "FASB Accounting Standard Codifications (ASC)").glob("*.pdf"))
        files += list((raw_root / "SEC Regulation").glob("*.pdf"))
        document_count = 0
        chunk_count = 0
        edge_count = 0

        with self._connect() as conn:
            for path in files:
                document_id = _safe_id(path.stem)
                source_type = "SEC" if "SEC Regulation" in str(path) else "ASC"
                citation = _citation_for_path(path)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO global_documents
                    (document_id, source_type, title, citation, path, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        source_type,
                        path.stem,
                        citation,
                        str(path),
                        json.dumps({"source": "data/raw"}),
                    ),
                )
                conn.execute("DELETE FROM global_rule_chunks WHERE document_id = ?", (document_id,))
                conn.execute("DELETE FROM global_rule_edges WHERE from_id = ? OR to_id = ?", (document_id, document_id))
                document_count += 1

                chunks = _extract_pdf_chunks(path)
                for index, item in enumerate(chunks, start=1):
                    chunk_id = f"{document_id}_c{index}"
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO global_rule_chunks
                        (chunk_id, document_id, source_type, citation, title, text, page_number, token_text, metadata_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            chunk_id,
                            document_id,
                            source_type,
                            citation,
                            path.stem,
                            item["text"],
                            item.get("page_number"),
                            " ".join(_tokens(f"{path.stem} {citation} {item['text']}")),
                            json.dumps({"path": str(path)}),
                        ),
                    )
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO global_rule_edges
                        (edge_id, from_id, to_id, edge_type, metadata_json)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            f"{document_id}_contains_{chunk_id}",
                            document_id,
                            chunk_id,
                            "contains",
                            "{}",
                        ),
                    )
                    chunk_count += 1
                    edge_count += 1

                for concept in _concepts_for_title(path.stem):
                    edge_id = f"{document_id}_governs_{_safe_id(concept)}"
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO global_rule_edges
                        (edge_id, from_id, to_id, edge_type, metadata_json)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (edge_id, document_id, concept, "governs", json.dumps({"concept": concept})),
                    )
                    edge_count += 1

        return {"documents": document_count, "chunks": chunk_count, "edges": edge_count}

    def ingest_seed_rules(self, seed_path: Path) -> dict[str, int]:
        if not seed_path.exists():
            return {"documents": 0, "chunks": 0, "edges": 0}

        records = json.loads(seed_path.read_text())
        document_count = 0
        chunk_count = 0
        edge_count = 0
        with self._connect() as conn:
            for index, record in enumerate(records, start=1):
                citation = str(record.get("citation") or f"Seed {index}")
                title = str(record.get("title") or citation)
                source_type = str(record.get("source_type") or "SOURCE")
                text = str(record.get("text") or f"Reference seed for {citation}.")
                document_id = f"seed_{_safe_id(citation)}"
                chunk_id = f"{document_id}_c1"
                conn.execute(
                    """
                    INSERT OR REPLACE INTO global_documents
                    (document_id, source_type, title, citation, path, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        source_type,
                        title,
                        citation,
                        str(seed_path),
                        json.dumps({"source": "seed"}),
                    ),
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO global_rule_chunks
                    (chunk_id, document_id, source_type, citation, title, text, page_number, token_text, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk_id,
                        document_id,
                        source_type,
                        citation,
                        title,
                        text,
                        None,
                        " ".join(_tokens(f"{title} {citation} {text}")),
                        json.dumps({"path": str(seed_path), "source": "seed"}),
                    ),
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO global_rule_edges
                    (edge_id, from_id, to_id, edge_type, metadata_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        f"{document_id}_contains_{chunk_id}",
                        document_id,
                        chunk_id,
                        "contains",
                        "{}",
                    ),
                )
                document_count += 1
                chunk_count += 1
                edge_count += 1
        return {"documents": document_count, "chunks": chunk_count, "edges": edge_count}

    def ingest_user_document(
        self,
        session_id: str,
        file_id: str,
        filename: str,
        path: Path,
        data: bytes,
        summary: dict[str, Any],
    ) -> dict[str, int]:
        document_id = f"user_{file_id}"
        source_type = summary.get("type") or Path(filename).suffix.lower().lstrip(".") or "upload"
        chunks = extract_text_chunks(filename, data, summary)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO user_documents
                (document_id, session_id, file_id, filename, source_type, path, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (document_id, session_id, file_id, filename, source_type, str(path), json.dumps(summary, default=str)),
            )
            conn.execute("DELETE FROM user_document_chunks WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM user_document_edges WHERE session_id = ? AND from_id = ?", (session_id, document_id))
            for index, text in enumerate(chunks, start=1):
                chunk_id = f"{document_id}_c{index}"
                conn.execute(
                    """
                    INSERT OR REPLACE INTO user_document_chunks
                    (chunk_id, document_id, session_id, source_type, title, text, token_text, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk_id,
                        document_id,
                        session_id,
                        source_type,
                        filename,
                        text,
                        " ".join(_tokens(f"{filename} {text}")),
                        json.dumps({"file_id": file_id}),
                    ),
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO user_document_edges
                    (edge_id, session_id, from_id, to_id, edge_type, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (f"{document_id}_contains_{chunk_id}", session_id, document_id, chunk_id, "contains", "{}"),
                )
        return {"documents": 1, "chunks": len(chunks)}

    def retrieve_global(self, query: str, limit: int = 5) -> list[KnowledgeChunk]:
        return self._retrieve(query, limit, scope="global")

    def retrieve_user(self, session_id: str, query: str, limit: int = 5) -> list[KnowledgeChunk]:
        return self._retrieve(query, limit, scope="user", session_id=session_id)

    def global_document_count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM global_documents").fetchone()[0])

    def _retrieve(
        self,
        query: str,
        limit: int,
        scope: str,
        session_id: str | None = None,
    ) -> list[KnowledgeChunk]:
        query_tokens = set(_tokens(query))
        if not query_tokens:
            return []

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if scope == "global":
                rows = conn.execute(
                    """
                    SELECT chunk_id, source_type, citation, title, text, metadata_json
                    FROM global_rule_chunks
                    """
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT chunk_id, source_type, '' AS citation, title, text, metadata_json, session_id
                    FROM user_document_chunks
                    WHERE session_id = ?
                    """,
                    (session_id,),
                ).fetchall()

        scored = []
        hints = _topic_hints(query)
        for row in rows:
            haystack = f"{row['title']} {row['citation']} {row['text']}"
            counts = _token_counts(haystack)
            score = sum(1 + counts[token] for token in query_tokens if token in counts)
            for hint in hints:
                if hint.lower() in haystack.lower():
                    score += 12
            if score <= 0:
                continue
            metadata = json.loads(row["metadata_json"] or "{}")
            scored.append(
                KnowledgeChunk(
                    chunk_id=row["chunk_id"],
                    scope=scope,
                    source=row["source_type"],
                    citation=row["citation"] or metadata.get("file_id", ""),
                    title=row["title"],
                    text=row["text"],
                    path=metadata.get("path", ""),
                    score=float(score),
                    session_id=row["session_id"] if "session_id" in row.keys() else None,
                )
            )
        scored.sort(key=lambda chunk: chunk.score, reverse=True)
        return scored[:limit]

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)


def _extract_pdf_chunks(path: Path) -> list[dict[str, Any]]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(path.read_bytes()))
        chunks = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = _clean_text(page.extract_text() or "")
            for chunk in _chunk_text(text):
                chunks.append({"page_number": page_number, "text": chunk})
        return chunks or [{"page_number": None, "text": f"Reference document: {path.stem}"}]
    except Exception:
        return [{"page_number": None, "text": f"Reference document: {path.stem}"}]


def _chunk_text(text: str, size: int = 1600, overlap: int = 200) -> list[str]:
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return chunks


def _tokens(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text or "")]


def _token_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for token in _tokens(text):
        counts[token] = counts.get(token, 0) + 1
    return counts


def _citation_for_path(path: Path) -> str:
    if path.stem.startswith("ASC "):
        return path.stem.split(" - ", 1)[0]
    return path.stem.replace("SEC ", "")


def _concepts_for_title(title: str) -> list[str]:
    lower = title.lower()
    concepts = []
    if "cash flow" in lower:
        concepts.append("Statement of Cash Flows")
    if "regulation s-x" in lower:
        concepts.append("Financial Statement Presentation")
    if "regulation s-k" in lower:
        concepts.append("Narrative SEC Disclosure")
    if "revenue" in lower:
        concepts.append("Revenue Recognition")
    if "lease" in lower:
        concepts.append("Lease Accounting")
    if "business combination" in lower:
        concepts.append("Business Combinations")
    return concepts


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


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower() or uuid.uuid4().hex
