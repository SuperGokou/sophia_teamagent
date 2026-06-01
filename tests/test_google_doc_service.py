from __future__ import annotations

import unittest
from types import SimpleNamespace

from legal_doc_agent.google_doc_service import GoogleDocLocalService


class _FakeFormatter:
    def check_editor_access(self, url: str) -> SimpleNamespace:
        return SimpleNamespace(
            document_id="doc123",
            can_edit=True,
            title="Draft",
            message=f"checked {url}",
            next_actions=(),
        )

    def apply_legal_layout(self, url: str) -> SimpleNamespace:
        return SimpleNamespace(
            document_id="doc123",
            title="Draft",
            requests_sent=3,
            summary=f"formatted {url}",
        )

    def write_legal_draft(self, url: str, draft: str) -> SimpleNamespace:
        return SimpleNamespace(
            document_id="doc123",
            title="Draft",
            requests_sent=5,
            summary=f"wrote {len(draft)} chars to {url}",
        )


class GoogleDocLocalServiceTests(unittest.TestCase):
    def test_write_dispatches_to_formatter(self) -> None:
        service = GoogleDocLocalService(_FakeFormatter())  # type: ignore[arg-type]

        result = service.write(
            {
                "url": "https://docs.google.com/document/d/doc123/edit",
                "draft": "Company legal name: Example AI, Inc.",
            }
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["document_id"], "doc123")
        self.assertEqual(result["requests_sent"], 5)
        self.assertIn("wrote", result["message"])

    def test_missing_url_is_bad_request(self) -> None:
        service = GoogleDocLocalService(_FakeFormatter())  # type: ignore[arg-type]

        with self.assertRaises(ValueError):
            service.check({})


if __name__ == "__main__":
    unittest.main()
