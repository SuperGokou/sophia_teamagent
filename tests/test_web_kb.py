from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from legal_doc_agent.legal_kb import LegalKnowledgeBase
from legal_doc_agent.web_kb import build_web_knowledge_context


class WebKnowledgeContextTests(unittest.TestCase):
    def test_builds_context_from_sqlite_fts_hits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "legal.sqlite"
            kb = LegalKnowledgeBase(db_path)
            kb.initialize()
            kb.upsert_source(
                key="delaware-code-title8",
                name="Delaware Code Title 8",
                jurisdiction="Delaware",
                source_url="https://delcode.delaware.gov/title8/c001/",
                official_level="official",
                retrieved_at="2026-06-06T00:00:00Z",
            )
            document = kb.upsert_document(
                source_key="delaware-code-title8",
                citation="8 Del. C. § 141(f)",
                title="Board action without meeting",
                jurisdiction="Delaware",
                doc_type="statute",
                version_date="2026-06-06",
                effective_date="2026-06-06",
                url="https://delcode.delaware.gov/title8/c001/sc04/index.html#141",
            )
            kb.upsert_section(
                document_id=document.id,
                citation="8 Del. C. § 141(f)",
                heading="Board consent authority note",
                text=(
                    "Authority note for Delaware board consent. The board may act "
                    "without a meeting by written or electronic consent, subject to "
                    "the corporation's governing documents."
                ),
                path="/title8/c001/sc04/141/f",
                order_index=1,
            )

            context = build_web_knowledge_context(
                "Need founder board consent and stock issuance package.",
                db_path=db_path,
            )

        self.assertIsNotNone(context)
        assert context is not None
        self.assertIn("8 Del. C. § 141(f)", context)
        self.assertIn("version_date: 2026-06-06", context)
        self.assertIn("retrieval_mode: fts5", context)
        self.assertIn("Do not cite authority that is not listed here", context)

    def test_missing_database_returns_none(self) -> None:
        context = build_web_knowledge_context(
            "Need founder board consent.",
            db_path=Path("/tmp/definitely-missing-legal-kb.sqlite"),
        )

        self.assertIsNone(context)

    def test_domain_terms_are_prioritized_for_long_briefs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "legal.sqlite"
            kb = LegalKnowledgeBase(db_path)
            kb.initialize()
            kb.upsert_source(
                key="us-code-house",
                name="U.S. Code",
                jurisdiction="US-Federal",
                source_url="https://uscode.house.gov/",
                official_level="official",
                retrieved_at="2026-06-06T00:00:00Z",
            )
            document = kb.upsert_document(
                source_key="us-code-house",
                citation="26 U.S.C. § 83(b)",
                title="83(b) election",
                jurisdiction="US-Federal",
                doc_type="statute",
                version_date="2026-06-06",
                effective_date="2026-06-06",
                url="https://uscode.house.gov/view.xhtml?req=(title:26%20section:83%20edition:prelim)",
            )
            kb.upsert_section(
                document_id=document.id,
                citation="26 U.S.C. § 83(b)",
                heading="83(b) authority note",
                text="Authority note for 83(b) election, restricted founder stock, tax filing, and vesting.",
                path="/title26/83/b",
                order_index=1,
            )

            context = build_web_knowledge_context(
                (
                    "Company legal name: Very Long Name Automation Inc. "
                    "Delaware file number: TBD. Founder one and founder two. "
                    "Special notes: include 83(b) election instructions."
                ),
                db_path=db_path,
            )

        self.assertIsNotNone(context)
        assert context is not None
        self.assertIn("26 U.S.C. § 83(b)", context)


if __name__ == "__main__":
    unittest.main()
