from __future__ import annotations

import unittest

from legal_doc_agent.prompts import (
    REQUIRED_TEMPLATE_DOCUMENTS,
    build_generation_jobs,
    messages_for_job,
)


class PromptTests(unittest.TestCase):
    def test_build_generation_jobs_splits_large_package(self) -> None:
        jobs = build_generation_jobs("SPEC", "BRIEF")

        self.assertEqual(len(jobs), 3 + len(REQUIRED_TEMPLATE_DOCUMENTS))
        self.assertEqual(jobs[0].title, "PART A - Required Document Checklist")
        self.assertIn("Generate only PART A", jobs[0].prompt)
        self.assertIn("Corporate Bylaws", jobs[3].title)

    def test_messages_include_system_and_user(self) -> None:
        job = build_generation_jobs("SPEC", "BRIEF")[0]
        messages = messages_for_job(job)

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertIn("qualified counsel", messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
