from __future__ import annotations

import unittest

from legal_doc_agent.google_docs import (
    GOOGLE_DOC_MIME_TYPE,
    GoogleDocPermissionError,
    GoogleDocsLegalFormatter,
    extract_google_doc_id,
)


class _FakeRequest:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def execute(self) -> dict[str, object]:
        return self._payload


class _FakeDriveFiles:
    def __init__(self, metadata: dict[str, object]) -> None:
        self.metadata = metadata

    def get(self, **kwargs: object) -> _FakeRequest:
        self.last_get = kwargs
        return _FakeRequest(self.metadata)


class _FakeDriveService:
    def __init__(self, metadata: dict[str, object]) -> None:
        self.files_resource = _FakeDriveFiles(metadata)

    def files(self) -> _FakeDriveFiles:
        return self.files_resource


class _FakeDocsDocuments:
    def __init__(self) -> None:
        self.batch_body: dict[str, object] | None = None

    def get(self, **kwargs: object) -> _FakeRequest:
        self.last_get = kwargs
        return _FakeRequest({"body": {"content": [{"endIndex": 32}]}})

    def batchUpdate(self, **kwargs: object) -> _FakeRequest:
        self.last_batch = kwargs
        self.batch_body = kwargs["body"]  # type: ignore[assignment]
        return _FakeRequest({})


class _FakeDocsService:
    def __init__(self) -> None:
        self.documents_resource = _FakeDocsDocuments()

    def documents(self) -> _FakeDocsDocuments:
        return self.documents_resource


class GoogleDocsTests(unittest.TestCase):
    def test_extract_google_doc_id(self) -> None:
        doc_id = extract_google_doc_id(
            "https://docs.google.com/document/d/abc_123-XYZ/edit?usp=sharing"
        )

        self.assertEqual(doc_id, "abc_123-XYZ")

    def test_extract_google_doc_id_rejects_non_doc_url(self) -> None:
        with self.assertRaises(ValueError):
            extract_google_doc_id("https://example.com/not-a-doc")

    def test_check_editor_access_requires_can_edit(self) -> None:
        formatter = GoogleDocsLegalFormatter(
            docs_service=_FakeDocsService(),
            drive_service=_FakeDriveService(
                {
                    "name": "Draft",
                    "mimeType": GOOGLE_DOC_MIME_TYPE,
                    "capabilities": {"canEdit": False},
                }
            ),
        )

        result = formatter.check_editor_access(
            "https://docs.google.com/document/d/doc123/edit"
        )

        self.assertFalse(result.can_edit)
        self.assertIn("开放编辑权限", result.message)

    def test_apply_legal_layout_sends_batch_requests(self) -> None:
        docs_service = _FakeDocsService()
        formatter = GoogleDocsLegalFormatter(
            docs_service=docs_service,
            drive_service=_FakeDriveService(
                {
                    "name": "Draft",
                    "mimeType": GOOGLE_DOC_MIME_TYPE,
                    "capabilities": {"canEdit": True},
                }
            ),
        )

        result = formatter.apply_legal_layout(
            "https://docs.google.com/document/d/doc123/edit"
        )

        self.assertEqual(result.requests_sent, 3)
        body = docs_service.documents_resource.batch_body
        self.assertIsNotNone(body)
        requests = body["requests"]  # type: ignore[index]
        self.assertEqual(requests[0]["updateDocumentStyle"]["documentStyle"]["marginTop"]["magnitude"], 72)
        self.assertEqual(requests[1]["updateTextStyle"]["textStyle"]["fontSize"]["magnitude"], 11)

    def test_apply_legal_layout_refuses_viewer_permission(self) -> None:
        formatter = GoogleDocsLegalFormatter(
            docs_service=_FakeDocsService(),
            drive_service=_FakeDriveService(
                {
                    "name": "Draft",
                    "mimeType": GOOGLE_DOC_MIME_TYPE,
                    "capabilities": {"canEdit": False},
                }
            ),
        )

        with self.assertRaises(GoogleDocPermissionError):
            formatter.apply_legal_layout("https://docs.google.com/document/d/doc123/edit")


if __name__ == "__main__":
    unittest.main()
