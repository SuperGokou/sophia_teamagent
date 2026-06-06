from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from docx import Document

from legal_doc_agent.web_generation import generate_web_legal_package


class TruncatedClient:
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        role: str | None = None,
    ) -> str:
        return (
            "# Planner Summary\n\n"
            "Matter type: Delaware post-formation package.\n\n"
            "# Draft Package\n\n"
            "1. Contractor Agreement: Purpose: Define contractor services. Prep: Scope of"
        )


class WebGenerationTests(unittest.TestCase):
    def test_truncated_generation_gets_completion_safeguard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = generate_web_legal_package(
                client=TruncatedClient(),
                brief="Generate a Delaware founder legal package.",
                output_path=root / "package.docx",
                artifact_dir=root / "artifacts",
            )

            artifact_text = (result.artifact_dir / "web_drafter_package.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("# Reviewer Quality Gate", artifact_text)
            self.assertIn("Completion Safeguard", artifact_text)
            self.assertNotIn("Scope of\n", artifact_text)

            doc_text = "\n".join(
                paragraph.text for paragraph in Document(result.output_path).paragraphs
            )
            self.assertIn("Reviewer Quality Gate", doc_text)
            self.assertIn("Completion Safeguard", doc_text)


if __name__ == "__main__":
    unittest.main()
