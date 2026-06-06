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


class TimeoutThenSuccessClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        role: str | None = None,
    ) -> str:
        self.calls.append(messages)
        if len(self.calls) == 1:
            raise TimeoutError("The read operation timed out")
        return (
            "# Planner Summary\n\n"
            "Matter type: Delaware post-formation package.\n\n"
            "# Draft Package\n\n"
            "Founder agreement and board consent package with placeholders.\n\n"
            "# Reviewer Quality Gate\n\n"
            "Counsel must review all placeholders and filing dates.\n\n"
            "END OF PACKAGE"
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

    def test_provider_timeout_retries_with_short_package_prompt(self) -> None:
        client = TimeoutThenSuccessClient()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = generate_web_legal_package(
                client=client,
                brief="Generate a Delaware founder legal package.",
                output_path=root / "package.docx",
                artifact_dir=root / "artifacts",
            )

            artifact_text = (result.artifact_dir / "web_drafter_package.md").read_text(
                encoding="utf-8"
            )
            retry_prompt = client.calls[1][1]["content"]
            self.assertEqual(len(client.calls), 2)
            self.assertIn("Target 700-1,100 words", retry_prompt)
            self.assertIn("Founder agreement and board consent package", artifact_text)
            self.assertTrue(result.output_path.exists())


if __name__ == "__main__":
    unittest.main()
