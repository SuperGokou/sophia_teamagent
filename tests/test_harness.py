from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from legal_doc_agent.harness import DryRunClient, LegalDocumentAgent


class RecordingClient:
    def __init__(self) -> None:
        self.roles: list[str | None] = []

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        role: str | None = None,
    ) -> str:
        self.roles.append(role)
        return f"# Generated\n\nRole: {role}\n"


class HarnessTests(unittest.TestCase):
    def test_generate_writes_artifacts_and_docx(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            spec = root / "spec.txt"
            spec.write_text("SPEC", encoding="utf-8")
            output = root / "out.docx"
            artifact_dir = root / "artifacts"
            agent = LegalDocumentAgent(DryRunClient())

            result = agent.generate(
                specification_path=spec,
                brief="Company: Example AI, Inc.",
                output_path=output,
                artifact_dir=artifact_dir,
            )

            self.assertTrue(result.output_path.exists())
            self.assertTrue((artifact_dir / "part_a_required_checklist.md").exists())
            self.assertGreaterEqual(len(result.observations), 3)

    def test_generate_routes_jobs_by_role(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            spec = root / "spec.txt"
            spec.write_text("SPEC", encoding="utf-8")
            client = RecordingClient()
            agent = LegalDocumentAgent(client)

            agent.generate(
                specification_path=spec,
                brief="Company: Example AI, Inc.",
                output_path=root / "out.docx",
                artifact_dir=root / "artifacts",
            )

            self.assertIn("planner", client.roles)
            self.assertIn("analyst", client.roles)
            self.assertIn("drafter", client.roles)


if __name__ == "__main__":
    unittest.main()
