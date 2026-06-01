"""Google Docs editor-access checks and legal-document layout updates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


GOOGLE_DOC_URL_RE = re.compile(
    r"https?://docs\.google\.com/document/d/([A-Za-z0-9_-]+)"
)
GOOGLE_DOC_MIME_TYPE = "application/vnd.google-apps.document"
GOOGLE_DOC_SCOPES = (
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
)


class GoogleDocPermissionError(RuntimeError):
    """Raised when the active credentials cannot edit the target Google Doc."""


@dataclass(frozen=True)
class GoogleDocAccessCheck:
    """Result of checking whether a Google Doc can be edited."""

    document_id: str
    can_edit: bool
    title: str | None = None
    message: str = ""
    next_actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class GoogleDocLayoutResult:
    """Result after applying a legal-document layout batch update."""

    document_id: str
    title: str | None
    requests_sent: int
    summary: str


def extract_google_doc_id(url: str) -> str:
    """Extract the document id from a Google Docs URL."""

    match = GOOGLE_DOC_URL_RE.search(url.strip())
    if not match:
        raise ValueError(
            "Provide a Google Docs URL in the form "
            "https://docs.google.com/document/d/{document_id}/edit."
        )
    return match.group(1)


class GoogleDocsLegalFormatter:
    """Apply standard legal-document formatting to an editable Google Doc."""

    def __init__(self, *, docs_service: Any, drive_service: Any) -> None:
        self._docs_service = docs_service
        self._drive_service = drive_service

    def check_editor_access(self, doc_url: str) -> GoogleDocAccessCheck:
        """Confirm that the target is a Google Doc and the credentials can edit it."""

        document_id = extract_google_doc_id(doc_url)
        try:
            metadata = (
                self._drive_service.files()
                .get(
                    fileId=document_id,
                    fields="name,mimeType,capabilities/canEdit",
                    supportsAllDrives=True,
                )
                .execute()
            )
        except Exception as exc:  # pragma: no cover - provider objects vary by version.
            return GoogleDocAccessCheck(
                document_id=document_id,
                can_edit=False,
                message=(
                    "无法读取 Google Doc 权限。请确认链接存在，并在 Google Doc "
                    "共享设置中开放 Editor 编辑权限后重试。"
                ),
                next_actions=(
                    "打开 Google Doc 右上角 Share。",
                    "把当前应用使用的账号加入为 Editor，或改为 Anyone with the link can edit。",
                    f"Provider error: {exc}",
                ),
            )

        title = metadata.get("name")
        mime_type = metadata.get("mimeType")
        can_edit = bool(metadata.get("capabilities", {}).get("canEdit"))

        if mime_type and mime_type != GOOGLE_DOC_MIME_TYPE:
            return GoogleDocAccessCheck(
                document_id=document_id,
                can_edit=False,
                title=title,
                message="这个链接不是 Google Docs 文档，无法按法律文书格式编辑。",
                next_actions=("请提供 docs.google.com/document/d/.../edit 链接。",),
            )

        if not can_edit:
            return GoogleDocAccessCheck(
                document_id=document_id,
                can_edit=False,
                title=title,
                message=(
                    "Google Doc 链接已识别，但当前凭据没有 Editor 权限。"
                    "请开放编辑权限后再执行自动排版。"
                ),
                next_actions=(
                    "在 Google Doc 右上角点击 Share。",
                    "把当前应用使用的 Google 账号设置为 Editor。",
                    "不要只给 Viewer 或 Commenter 权限。",
                ),
            )

        return GoogleDocAccessCheck(
            document_id=document_id,
            can_edit=True,
            title=title,
            message="Google Doc 已确认具备 Editor 权限，可以自动调整法律文书版式。",
        )

    def apply_legal_layout(self, doc_url: str) -> GoogleDocLayoutResult:
        """Apply margin, font, paragraph, and spacing updates to a Google Doc."""

        access = self.check_editor_access(doc_url)
        if not access.can_edit:
            raise GoogleDocPermissionError(access.message)

        document = (
            self._docs_service.documents()
            .get(documentId=access.document_id)
            .execute()
        )
        end_index = _document_end_index(document)
        requests = _legal_layout_requests(end_index)
        if not requests:
            return GoogleDocLayoutResult(
                document_id=access.document_id,
                title=access.title,
                requests_sent=0,
                summary="Google Doc 没有可格式化正文内容。",
            )

        (
            self._docs_service.documents()
            .batchUpdate(documentId=access.document_id, body={"requests": requests})
            .execute()
        )
        return GoogleDocLayoutResult(
            document_id=access.document_id,
            title=access.title,
            requests_sent=len(requests),
            summary=(
                "Applied legal-document layout: 1 inch margins, Times New Roman "
                "11 pt body text, 115% line spacing, and consistent paragraph spacing."
            ),
        )

    def write_legal_draft(self, doc_url: str, draft_text: str) -> GoogleDocLayoutResult:
        """Replace the document body with a draft and apply legal-document layout."""

        text = draft_text.strip()
        if not text:
            raise ValueError("Draft text is empty.")

        access = self.check_editor_access(doc_url)
        if not access.can_edit:
            raise GoogleDocPermissionError(access.message)

        document = (
            self._docs_service.documents()
            .get(documentId=access.document_id)
            .execute()
        )
        current_end_index = _document_end_index(document)
        body_text = f"{text}\n"
        requests = _replace_body_requests(current_end_index, body_text)
        requests.extend(_legal_layout_requests(1 + _utf16_code_units(body_text)))

        (
            self._docs_service.documents()
            .batchUpdate(documentId=access.document_id, body={"requests": requests})
            .execute()
        )
        return GoogleDocLayoutResult(
            document_id=access.document_id,
            title=access.title,
            requests_sent=len(requests),
            summary=(
                "Wrote draft text and applied legal-document layout: 1 inch margins, "
                "Times New Roman 11 pt, 115% line spacing, and consistent spacing."
            ),
        )


def _document_end_index(document: dict[str, Any]) -> int:
    body_content = document.get("body", {}).get("content", [])
    end_indices = [
        item.get("endIndex", 1)
        for item in body_content
        if isinstance(item.get("endIndex"), int)
    ]
    return max(end_indices, default=1)


def _utf16_code_units(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def _replace_body_requests(end_index: int, text: str) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    if end_index > 2:
        requests.append(
            {
                "deleteContentRange": {
                    "range": {
                        "startIndex": 1,
                        "endIndex": end_index - 1,
                    }
                }
            }
        )
    requests.append(
        {
            "insertText": {
                "location": {"index": 1},
                "text": text,
            }
        }
    )
    return requests


def _legal_layout_requests(end_index: int) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = [
        {
            "updateDocumentStyle": {
                "documentStyle": {
                    "marginTop": {"magnitude": 72, "unit": "PT"},
                    "marginBottom": {"magnitude": 72, "unit": "PT"},
                    "marginLeft": {"magnitude": 72, "unit": "PT"},
                    "marginRight": {"magnitude": 72, "unit": "PT"},
                },
                "fields": "marginTop,marginBottom,marginLeft,marginRight",
            }
        }
    ]

    if end_index <= 1:
        return requests

    text_range = {"startIndex": 1, "endIndex": end_index - 1}
    requests.extend(
        [
            {
                "updateTextStyle": {
                    "range": text_range,
                    "textStyle": {
                        "weightedFontFamily": {
                            "fontFamily": "Times New Roman",
                            "weight": 400,
                        },
                        "fontSize": {"magnitude": 11, "unit": "PT"},
                    },
                    "fields": "weightedFontFamily,fontSize",
                }
            },
            {
                "updateParagraphStyle": {
                    "range": text_range,
                    "paragraphStyle": {
                        "alignment": "START",
                        "lineSpacing": 115,
                        "spaceAbove": {"magnitude": 0, "unit": "PT"},
                        "spaceBelow": {"magnitude": 8, "unit": "PT"},
                    },
                    "fields": "alignment,lineSpacing,spaceAbove,spaceBelow",
                }
            },
        ]
    )
    return requests


def build_google_docs_formatter(
    *,
    credentials_path: Path,
    token_path: Path,
) -> GoogleDocsLegalFormatter:
    """Create a formatter from Google OAuth client credentials."""

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:  # pragma: no cover - optional dependency guard.
        raise RuntimeError(
            "Google Docs support requires optional dependencies. "
            'Install them with: python -m pip install -e ".[google]"'
        ) from exc

    credentials = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(
            str(token_path),
            list(GOOGLE_DOC_SCOPES),
        )

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"Google OAuth client credentials were not found: {credentials_path}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path),
                list(GOOGLE_DOC_SCOPES),
            )
            credentials = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(credentials.to_json(), encoding="utf-8")

    docs_service = build("docs", "v1", credentials=credentials)
    drive_service = build("drive", "v3", credentials=credentials)
    return GoogleDocsLegalFormatter(
        docs_service=docs_service,
        drive_service=drive_service,
    )
