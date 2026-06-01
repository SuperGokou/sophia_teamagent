from __future__ import annotations

import unittest
from types import SimpleNamespace

from legal_doc_agent.google_doc_service import GoogleDocLocalService, _make_handler


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

    def test_handler_rejects_untrusted_origins(self) -> None:
        service = GoogleDocLocalService(_FakeFormatter())  # type: ignore[arg-type]
        handler_type = _make_handler(service)
        handler = object.__new__(handler_type)
        handler.client_address = ("127.0.0.1", 12345)
        handler.headers = {"Origin": "https://evil.example"}

        self.assertFalse(handler._request_allowed(require_origin=True))

    def test_handler_accepts_local_ui_origins(self) -> None:
        service = GoogleDocLocalService(_FakeFormatter())  # type: ignore[arg-type]
        handler_type = _make_handler(service)
        handler = object.__new__(handler_type)
        handler.client_address = ("127.0.0.1", 12345)
        handler.headers = {"Origin": "http://localhost:5173"}

        self.assertTrue(handler._request_allowed(require_origin=True))

    def test_handler_rejects_missing_origin_for_post(self) -> None:
        service = GoogleDocLocalService(_FakeFormatter())  # type: ignore[arg-type]
        handler_type = _make_handler(service)
        handler = object.__new__(handler_type)
        handler.client_address = ("127.0.0.1", 12345)
        handler.headers = {}

        self.assertFalse(handler._request_allowed(require_origin=True))

    def test_handler_rejects_non_loopback_clients(self) -> None:
        service = GoogleDocLocalService(_FakeFormatter())  # type: ignore[arg-type]
        handler_type = _make_handler(service)
        handler = object.__new__(handler_type)
        handler.client_address = ("192.168.1.10", 12345)
        handler.headers = {"Origin": "http://localhost:5173"}

        self.assertFalse(handler._request_allowed(require_origin=True))


if __name__ == "__main__":
    unittest.main()
