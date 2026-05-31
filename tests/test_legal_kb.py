from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from legal_doc_agent.legal_kb import FIRST_PHASE_CONNECTORS, LegalKnowledgeBase


class LegalKnowledgeBaseTests(unittest.TestCase):
    def test_initialize_seed_search_check_and_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            kb = LegalKnowledgeBase(root / "legal.sqlite")
            kb.initialize()

            sources = kb.seed_connector_sources()
            self.assertEqual(len(sources), len(FIRST_PHASE_CONNECTORS))

            document = kb.upsert_document(
                source_key="govinfo-uscode",
                citation="15 U.S.C. 77a",
                title="Securities Act definitions",
                jurisdiction="US-Federal",
                doc_type="us_code",
                version_date="2026-05-31",
                effective_date="2026-05-31",
                url="https://example.test/uscode/15/77a",
            )
            section = kb.upsert_section(
                document_id=document.id,
                citation="15 U.S.C. 77a",
                heading="Definitions",
                text="This sample section defines a security and issuer for test purposes.",
                path="/15/77a",
                order_index=1,
            )
            kb.add_chunk(section_id=section.id, chunk_text=section.text, token_count=12)

            exact_hits = kb.search("security issuer", citation="15 U.S.C. 77a")
            self.assertEqual(exact_hits[0].retrieval_mode, "citation")
            self.assertIn("security", exact_hits[0].text)

            fts_hits = kb.search("issuer")
            self.assertTrue(any(hit.citation == "15 U.S.C. 77a" for hit in fts_hits))

            supported = kb.check_citation("15 U.S.C. 77a", required_terms=["issuer"])
            self.assertTrue(supported.supported)

            unsupported = kb.check_citation("15 U.S.C. 77a", required_terms=["fiduciary"])
            self.assertFalse(unsupported.supported)
            self.assertEqual(unsupported.missing_terms, ("fiduciary",))

            vault = kb.export_obsidian(root / "vault", matter_name="Example AI Inc")
            self.assertTrue((vault / "Sources" / "govinfo-uscode.md").exists())
            retrieved = (
                vault
                / "Matters"
                / "Example AI Inc"
                / "retrieved-authorities.md"
            ).read_text(encoding="utf-8")
            self.assertIn("15 U.S.C. 77a", retrieved)
            self.assertIn("version_date:", retrieved)


if __name__ == "__main__":
    unittest.main()
