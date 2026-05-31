"""SQLite-backed legal knowledge base primitives."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ConnectorSpec:
    """First-phase source connector metadata."""

    key: str
    name: str
    jurisdiction: str
    source_url: str
    official_level: str
    notes: str


@dataclass(frozen=True)
class SourceRecord:
    """Stored source row."""

    id: int
    key: str
    name: str
    jurisdiction: str
    source_url: str
    official_level: str
    retrieved_at: str


@dataclass(frozen=True)
class DocumentRecord:
    """Stored legal document row."""

    id: int
    source_id: int
    citation: str
    title: str
    jurisdiction: str
    doc_type: str
    effective_date: str | None
    version_date: str | None
    url: str
    sha256: str


@dataclass(frozen=True)
class SectionRecord:
    """Stored section row."""

    id: int
    document_id: int
    citation: str
    heading: str
    text: str
    path: str
    order_index: int
    sha256: str


@dataclass(frozen=True)
class SearchHit:
    """Hybrid retrieval hit from exact citation or FTS."""

    section_id: int
    document_id: int
    source_key: str
    citation: str
    heading: str
    text: str
    url: str
    version_date: str | None
    effective_date: str | None
    score: float
    retrieval_mode: str


@dataclass(frozen=True)
class CitationCheck:
    """Result of checking whether retrieved text supports a citation."""

    citation: str
    supported: bool
    missing_terms: tuple[str, ...]
    hits: tuple[SearchHit, ...]


FIRST_PHASE_CONNECTORS: tuple[ConnectorSpec, ...] = (
    ConnectorSpec(
        key="govinfo-uscode",
        name="GovInfo US Code",
        jurisdiction="US-Federal",
        source_url="https://www.govinfo.gov/app/collection/uscode",
        official_level="official",
        notes="Federal statutory text. Use GovInfo packages as the official version source.",
    ),
    ConnectorSpec(
        key="ecfr-current",
        name="eCFR Current",
        jurisdiction="US-Federal",
        source_url="https://www.ecfr.gov/developers/documentation/api/v1",
        official_level="official-current",
        notes="Current federal regulations with point-in-time API support.",
    ),
    ConnectorSpec(
        key="federal-register",
        name="Federal Register",
        jurisdiction="US-Federal",
        source_url="https://www.federalregister.gov/developers/documentation/api/v1",
        official_level="publication-api",
        notes="Rules, proposed rules, notices, and presidential documents. Verify final legal text against GovInfo when needed.",
    ),
    ConnectorSpec(
        key="congress-public-laws",
        name="Congress.gov Public Laws",
        jurisdiction="US-Federal",
        source_url="https://api.congress.gov/",
        official_level="official-api",
        notes="Bills, public/private laws, actions, and text metadata.",
    ),
)


class LegalKnowledgeBase:
    """Small SQLite/FTS5 legal authority store."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        """Open a configured SQLite connection."""

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        """Create schema and FTS indexes if they do not exist."""

        with closing(self.connect()) as connection, connection:
            connection.executescript(SCHEMA_SQL)
            connection.execute(
                """
                INSERT INTO metadata(key, value)
                VALUES ('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(SCHEMA_VERSION),),
            )

    def seed_connector_sources(self) -> list[SourceRecord]:
        """Insert first-phase official source definitions."""

        records: list[SourceRecord] = []
        for connector in FIRST_PHASE_CONNECTORS:
            records.append(
                self.upsert_source(
                    key=connector.key,
                    name=connector.name,
                    jurisdiction=connector.jurisdiction,
                    source_url=connector.source_url,
                    official_level=connector.official_level,
                )
            )
        return records

    def upsert_source(
        self,
        *,
        key: str,
        name: str,
        jurisdiction: str,
        source_url: str,
        official_level: str,
        retrieved_at: str | None = None,
    ) -> SourceRecord:
        """Create or update a source row."""

        retrieved = retrieved_at or _utc_now()
        with closing(self.connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO sources(key, name, jurisdiction, source_url, official_level, retrieved_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    name = excluded.name,
                    jurisdiction = excluded.jurisdiction,
                    source_url = excluded.source_url,
                    official_level = excluded.official_level,
                    retrieved_at = excluded.retrieved_at
                """,
                (key, name, jurisdiction, source_url, official_level, retrieved),
            )
            row = connection.execute("SELECT * FROM sources WHERE key = ?", (key,)).fetchone()
        return _source_from_row(row)

    def upsert_document(
        self,
        *,
        source_key: str,
        citation: str,
        title: str,
        jurisdiction: str,
        doc_type: str,
        url: str,
        effective_date: str | None = None,
        version_date: str | None = None,
        sha256: str | None = None,
    ) -> DocumentRecord:
        """Create or update a legal document row."""

        digest = sha256 or _sha256_text("\n".join([citation, title, url, version_date or ""]))
        version_key = version_date or ""
        with closing(self.connect()) as connection, connection:
            source = connection.execute(
                "SELECT id FROM sources WHERE key = ?",
                (source_key,),
            ).fetchone()
            if source is None:
                raise ValueError(f"Unknown source key: {source_key}")
            connection.execute(
                """
                INSERT INTO documents(
                    source_id, citation, title, jurisdiction, doc_type,
                    effective_date, version_date, version_key, url, sha256
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, citation, version_key) DO UPDATE SET
                    title = excluded.title,
                    jurisdiction = excluded.jurisdiction,
                    doc_type = excluded.doc_type,
                    effective_date = excluded.effective_date,
                    url = excluded.url,
                    sha256 = excluded.sha256
                """,
                (
                    int(source["id"]),
                    citation,
                    title,
                    jurisdiction,
                    doc_type,
                    effective_date,
                    version_date,
                    version_key,
                    url,
                    digest,
                ),
            )
            row = connection.execute(
                """
                SELECT *
                FROM documents
                WHERE source_id = ? AND citation = ? AND version_key = ?
                """,
                (int(source["id"]), citation, version_key),
            ).fetchone()
        return _document_from_row(row)

    def upsert_section(
        self,
        *,
        document_id: int,
        citation: str,
        heading: str,
        text: str,
        path: str,
        order_index: int,
    ) -> SectionRecord:
        """Create or update a section and its FTS index."""

        digest = _sha256_text(text)
        with closing(self.connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO sections(document_id, citation, heading, text, path, order_index, sha256)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id, citation, path) DO UPDATE SET
                    heading = excluded.heading,
                    text = excluded.text,
                    order_index = excluded.order_index,
                    sha256 = excluded.sha256
                """,
                (document_id, citation, heading, text, path, order_index, digest),
            )
            row = connection.execute(
                """
                SELECT *
                FROM sections
                WHERE document_id = ? AND citation = ? AND path = ?
                """,
                (document_id, citation, path),
            ).fetchone()
        return _section_from_row(row)

    def add_chunk(
        self,
        *,
        section_id: int,
        chunk_text: str,
        token_count: int,
        embedding_id: str | None = None,
    ) -> int:
        """Store a RAG chunk. Embedding vectors live outside SQLite for MVP."""

        with closing(self.connect()) as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO chunks(section_id, chunk_text, token_count, embedding_id)
                VALUES (?, ?, ?, ?)
                """,
                (section_id, chunk_text, token_count, embedding_id),
            )
            return int(cursor.lastrowid)

    def search(
        self,
        query: str,
        *,
        citation: str | None = None,
        limit: int = 8,
    ) -> list[SearchHit]:
        """Hybrid retrieval using exact citation first, then SQLite FTS5."""

        seen: set[int] = set()
        hits: list[SearchHit] = []
        with closing(self.connect()) as connection, connection:
            if citation:
                for row in connection.execute(
                    SEARCH_BASE_SQL
                    + """
                    WHERE lower(s.citation) = lower(?)
                       OR lower(d.citation) = lower(?)
                    ORDER BY s.order_index
                    LIMIT ?
                    """,
                    (citation, citation, limit),
                ):
                    hit = _hit_from_row(row, score=100.0, retrieval_mode="citation")
                    hits.append(hit)
                    seen.add(hit.section_id)

            fts_query = _to_fts_query(query)
            if fts_query:
                remaining = max(0, limit - len(hits))
                for row in connection.execute(
                    FTS_SEARCH_SQL,
                    (fts_query, remaining),
                ):
                    if int(row["section_id"]) in seen:
                        continue
                    hits.append(
                        _hit_from_row(
                            row,
                            score=float(row["rank_score"]),
                            retrieval_mode="fts5",
                        )
                    )
                    seen.add(int(row["section_id"]))

        return hits[:limit]

    def check_citation(
        self,
        citation: str,
        *,
        required_terms: Iterable[str] = (),
        limit: int = 5,
    ) -> CitationCheck:
        """Confirm a citation exists and includes required support terms."""

        terms = tuple(term.strip() for term in required_terms if term.strip())
        hits = tuple(self.search(" ".join(terms) or citation, citation=citation, limit=limit))
        combined = "\n".join(hit.text for hit in hits).lower()
        missing = tuple(term for term in terms if term.lower() not in combined)
        return CitationCheck(
            citation=citation,
            supported=bool(hits) and not missing,
            missing_terms=missing,
            hits=hits,
        )

    def export_obsidian(
        self,
        vault_root: Path,
        *,
        matter_name: str = "Example Matter",
    ) -> Path:
        """Export source and authority notes into an Obsidian-friendly vault."""

        base = vault_root / "Sophia Legal"
        sources_dir = base / "Sources"
        matter_dir = base / "Matters" / _safe_filename(matter_name)
        sources_dir.mkdir(parents=True, exist_ok=True)
        matter_dir.mkdir(parents=True, exist_ok=True)

        with closing(self.connect()) as connection, connection:
            sources = list(connection.execute("SELECT * FROM sources ORDER BY name"))
            sections = list(connection.execute(EXPORT_SECTIONS_SQL))

        for source in sources:
            note = _source_note(_source_from_row(source))
            (sources_dir / f"{_safe_filename(source['key'])}.md").write_text(
                note,
                encoding="utf-8",
            )

        retrieved = matter_dir / "retrieved-authorities.md"
        retrieved.write_text(_retrieved_authorities_note(sections), encoding="utf-8")
        (matter_dir / "index.md").write_text(
            _matter_index_note(matter_name),
            encoding="utf-8",
        )
        return base


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    source_url TEXT NOT NULL,
    official_level TEXT NOT NULL,
    retrieved_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    citation TEXT NOT NULL,
    title TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    effective_date TEXT,
    version_date TEXT,
    version_key TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    UNIQUE(source_id, citation, version_key)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_identity
ON documents(source_id, citation, version_key);

CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    citation TEXT NOT NULL,
    heading TEXT NOT NULL,
    text TEXT NOT NULL,
    path TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    UNIQUE(document_id, citation, path)
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    section_id INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    embedding_id TEXT
);

CREATE TABLE IF NOT EXISTS citations (
    id INTEGER PRIMARY KEY,
    from_section_id INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    target_citation TEXT NOT NULL,
    target_url TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS updates (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    old_hash TEXT NOT NULL,
    new_hash TEXT NOT NULL,
    changed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS embedding_index (
    id INTEGER PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    vector_ref TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts
USING fts5(citation, heading, text, content='sections', content_rowid='id');

CREATE TRIGGER IF NOT EXISTS sections_ai AFTER INSERT ON sections BEGIN
    INSERT INTO sections_fts(rowid, citation, heading, text)
    VALUES (new.id, new.citation, new.heading, new.text);
END;

CREATE TRIGGER IF NOT EXISTS sections_ad AFTER DELETE ON sections BEGIN
    INSERT INTO sections_fts(sections_fts, rowid, citation, heading, text)
    VALUES ('delete', old.id, old.citation, old.heading, old.text);
END;

CREATE TRIGGER IF NOT EXISTS sections_au AFTER UPDATE ON sections BEGIN
    INSERT INTO sections_fts(sections_fts, rowid, citation, heading, text)
    VALUES ('delete', old.id, old.citation, old.heading, old.text);
    INSERT INTO sections_fts(rowid, citation, heading, text)
    VALUES (new.id, new.citation, new.heading, new.text);
END;
"""

SEARCH_BASE_SQL = """
SELECT
    s.id AS section_id,
    s.document_id AS document_id,
    src.key AS source_key,
    s.citation AS citation,
    s.heading AS heading,
    s.text AS text,
    d.url AS url,
    d.version_date AS version_date,
    d.effective_date AS effective_date
FROM sections s
JOIN documents d ON d.id = s.document_id
JOIN sources src ON src.id = d.source_id
"""

FTS_SEARCH_SQL = """
SELECT
    s.id AS section_id,
    s.document_id AS document_id,
    src.key AS source_key,
    s.citation AS citation,
    s.heading AS heading,
    s.text AS text,
    d.url AS url,
    d.version_date AS version_date,
    d.effective_date AS effective_date,
    bm25(sections_fts) AS rank_score
FROM sections_fts
JOIN sections s ON s.id = sections_fts.rowid
JOIN documents d ON d.id = s.document_id
JOIN sources src ON src.id = d.source_id
WHERE sections_fts MATCH ?
ORDER BY rank_score
LIMIT ?
"""

EXPORT_SECTIONS_SQL = """
SELECT
    src.key AS source_key,
    src.name AS source_name,
    d.title,
    d.doc_type,
    d.jurisdiction,
    d.version_date,
    d.effective_date,
    d.url,
    s.citation,
    s.heading,
    s.text
FROM sections s
JOIN documents d ON d.id = s.document_id
JOIN sources src ON src.id = d.source_id
ORDER BY src.name, d.citation, s.order_index
"""


def _source_from_row(row: sqlite3.Row) -> SourceRecord:
    return SourceRecord(
        id=int(row["id"]),
        key=str(row["key"]),
        name=str(row["name"]),
        jurisdiction=str(row["jurisdiction"]),
        source_url=str(row["source_url"]),
        official_level=str(row["official_level"]),
        retrieved_at=str(row["retrieved_at"]),
    )


def _document_from_row(row: sqlite3.Row) -> DocumentRecord:
    return DocumentRecord(
        id=int(row["id"]),
        source_id=int(row["source_id"]),
        citation=str(row["citation"]),
        title=str(row["title"]),
        jurisdiction=str(row["jurisdiction"]),
        doc_type=str(row["doc_type"]),
        effective_date=row["effective_date"],
        version_date=row["version_date"],
        url=str(row["url"]),
        sha256=str(row["sha256"]),
    )


def _section_from_row(row: sqlite3.Row) -> SectionRecord:
    return SectionRecord(
        id=int(row["id"]),
        document_id=int(row["document_id"]),
        citation=str(row["citation"]),
        heading=str(row["heading"]),
        text=str(row["text"]),
        path=str(row["path"]),
        order_index=int(row["order_index"]),
        sha256=str(row["sha256"]),
    )


def _hit_from_row(row: sqlite3.Row, *, score: float, retrieval_mode: str) -> SearchHit:
    return SearchHit(
        section_id=int(row["section_id"]),
        document_id=int(row["document_id"]),
        source_key=str(row["source_key"]),
        citation=str(row["citation"]),
        heading=str(row["heading"]),
        text=str(row["text"]),
        url=str(row["url"]),
        version_date=row["version_date"],
        effective_date=row["effective_date"],
        score=score,
        retrieval_mode=retrieval_mode,
    )


def _to_fts_query(query: str) -> str:
    terms = re.findall(r"[A-Za-z0-9]{2,}", query)
    return " OR ".join(f'"{term}"' for term in terms[:12])


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_. -]+", "-", value).strip(" .-")
    return cleaned or "untitled"


def _source_note(source: SourceRecord) -> str:
    return (
        "---\n"
        f"jurisdiction: {source.jurisdiction}\n"
        f"source: {source.key}\n"
        f"official_level: {source.official_level}\n"
        f"retrieved_at: {source.retrieved_at}\n"
        "verified: true\n"
        "---\n\n"
        f"# {source.name}\n\n"
        f"- URL: {source.source_url}\n"
    )


def _retrieved_authorities_note(rows: list[sqlite3.Row]) -> str:
    lines = [
        "---",
        "jurisdiction: US-Federal",
        "source: sophia-legal-kb",
        f"version_date: {_utc_now()[:10]}",
        "verified: true",
        "---",
        "",
        "# Retrieved Authorities",
        "",
    ]
    for row in rows:
        excerpt = str(row["text"]).replace("\n", " ").strip()
        if len(excerpt) > 320:
            excerpt = excerpt[:317].rstrip() + "..."
        lines.extend(
            [
                f"## {row['citation']} - {row['heading']}",
                "",
                f"- Source: {row['source_name']}",
                f"- Jurisdiction: {row['jurisdiction']}",
                f"- Version date: {row['version_date'] or 'unknown'}",
                f"- Effective date: {row['effective_date'] or 'unknown'}",
                f"- URL: {row['url']}",
                "",
                excerpt,
                "",
            ]
        )
    return "\n".join(lines)


def _matter_index_note(matter_name: str) -> str:
    return (
        "---\n"
        "matter_type: legal-document-package\n"
        "jurisdiction: US-Federal\n"
        "verified: false\n"
        "---\n\n"
        f"# {matter_name}\n\n"
        "- [[retrieved-authorities]]\n"
        "- risk-analysis.md\n"
        "- generated-word-log.md\n"
    )
