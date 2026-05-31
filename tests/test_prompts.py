from __future__ import annotations

import unittest

from legal_doc_agent.agents import (
    ANALYST_ROLE,
    DRAFTER_ROLE,
    PLANNER_ROLE,
    REASONER_ROLE,
    REVIEWER_ROLE,
)
from legal_doc_agent.docx_writer import DocumentSection
from legal_doc_agent.prompts import (
    REQUIRED_TEMPLATE_DOCUMENTS,
    build_final_review_job,
    build_generation_jobs,
    messages_for_job,
)


class PromptTests(unittest.TestCase):
    def test_build_generation_jobs_splits_large_package(self) -> None:
        jobs = build_generation_jobs("SPEC", "BRIEF")

        self.assertEqual(len(jobs), 3 + len(REQUIRED_TEMPLATE_DOCUMENTS))
        self.assertEqual(jobs[0].title, "PART A - Required Document Checklist")
        self.assertEqual(jobs[0].agent_role, PLANNER_ROLE)
        self.assertEqual(jobs[1].agent_role, ANALYST_ROLE)
        self.assertEqual(jobs[2].agent_role, REASONER_ROLE)
        self.assertIn("Generate only PART A", jobs[0].prompt)
        self.assertIn("Corporate Bylaws", jobs[3].title)
        self.assertEqual(jobs[3].agent_role, DRAFTER_ROLE)

    def test_messages_include_system_and_user(self) -> None:
        job = build_generation_jobs("SPEC", "BRIEF")[0]
        messages = messages_for_job(job)

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertIn("qualified counsel", messages[0]["content"])

    def test_knowledge_context_is_supplemental(self) -> None:
        jobs = build_generation_jobs("SPEC", "BRIEF", knowledge_context="15 U.S.C. 77a")

        self.assertIn("SUPPLEMENTAL LEGAL KNOWLEDGE BASE CONTEXT", jobs[0].prompt)
        self.assertIn("15 U.S.C. 77a", jobs[0].prompt)
        self.assertIn("Do not invent citations", jobs[0].prompt)

    def test_final_review_job_checks_generated_package(self) -> None:
        job = build_final_review_job(
            "SPEC",
            "BRIEF",
            [DocumentSection(title="Checklist", markdown="Company name: Example AI")],
            knowledge_context="15 U.S.C. 77a",
        )

        self.assertEqual(job.job_id, "final_reviewer_quality_gate")
        self.assertEqual(job.agent_role, REVIEWER_ROLE)
        self.assertIn("Final Reviewer Quality Gate", job.prompt)
        self.assertIn("Approval Status", job.prompt)
        self.assertIn("Company name: Example AI", job.prompt)
        self.assertIn("15 U.S.C. 77a", job.prompt)


if __name__ == "__main__":
    unittest.main()
