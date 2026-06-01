"""Local HTTP bridge for Google Docs OAuth writing."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from legal_doc_agent.local_http import (
    DEFAULT_ALLOWED_ORIGINS,
    read_json_body,
    request_allowed,
    send_json,
)
from legal_doc_agent.google_docs import (
    GoogleDocPermissionError,
    GoogleDocsLegalFormatter,
)


MAX_REQUEST_BYTES = 2_000_000


class GoogleDocLocalService:
    """Small request dispatcher for local Google Docs operations."""

    def __init__(
        self,
        formatter: GoogleDocsLegalFormatter,
        *,
        allowed_origins: frozenset[str] = DEFAULT_ALLOWED_ORIGINS,
    ) -> None:
        self._formatter = formatter
        self._allowed_origins = allowed_origins

    @property
    def allowed_origins(self) -> frozenset[str]:
        return self._allowed_origins

    def check(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = _required_string(payload, "url")
        result = self._formatter.check_editor_access(url)
        return {
            "ok": result.can_edit,
            "document_id": result.document_id,
            "title": result.title,
            "message": result.message,
            "next_actions": list(result.next_actions),
        }

    def format(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = _required_string(payload, "url")
        result = self._formatter.apply_legal_layout(url)
        return _layout_response(result)

    def write(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = _required_string(payload, "url")
        draft = str(payload.get("draft") or payload.get("text") or "").strip()
        result = self._formatter.write_legal_draft(url, draft)
        return _layout_response(result)


def run_google_doc_service(
    formatter: GoogleDocsLegalFormatter,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    """Run the local Google Doc bridge until interrupted."""

    service = GoogleDocLocalService(formatter)
    server = ThreadingHTTPServer((host, port), _make_handler(service))
    print(f"Google Doc OAuth service listening on http://{host}:{port}")
    print("Endpoints: GET /health, POST /google-doc/check, /google-doc/format, /google-doc/write")
    server.serve_forever()


def _make_handler(service: GoogleDocLocalService) -> type[BaseHTTPRequestHandler]:
    class GoogleDocRequestHandler(BaseHTTPRequestHandler):
        server_version = "LegalDocGoogleBridge/0.1"

        def do_OPTIONS(self) -> None:  # noqa: N802
            if not self._request_allowed(require_origin=True):
                self._send_json({"ok": False, "error": "request_not_allowed"}, status=403)
                return
            self._send_json({"ok": True})

        def do_GET(self) -> None:  # noqa: N802
            if not self._request_allowed(require_origin=False):
                self._send_json({"ok": False, "error": "request_not_allowed"}, status=403)
                return
            if self.path == "/health":
                self._send_json({"ok": True, "service": "google-doc-oauth"})
                return
            self._send_json({"ok": False, "error": "not_found"}, status=404)

        def do_POST(self) -> None:  # noqa: N802
            if not self._request_allowed(require_origin=True):
                self._send_json({"ok": False, "error": "request_not_allowed"}, status=403)
                return
            routes: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
                "/google-doc/check": service.check,
                "/google-doc/format": service.format,
                "/google-doc/write": service.write,
            }
            handler = routes.get(self.path)
            if handler is None:
                self._send_json({"ok": False, "error": "not_found"}, status=404)
                return

            try:
                payload = self._read_json()
                self._send_json(handler(payload))
            except GoogleDocPermissionError as exc:
                self._send_json({"ok": False, "error": "permission", "message": str(exc)}, status=403)
            except ValueError as exc:
                self._send_json({"ok": False, "error": "bad_request", "message": str(exc)}, status=400)
            except Exception as exc:  # pragma: no cover - provider objects vary by version.
                print(f"provider error: {exc}")
                self._send_json(
                    {
                        "ok": False,
                        "error": "provider",
                        "message": "Google Doc operation failed. Check the local service terminal for details.",
                    },
                    status=500,
                )

        def log_message(self, format: str, *args: Any) -> None:
            print(f"{self.address_string()} - {format % args}")

        def _request_allowed(self, *, require_origin: bool) -> bool:
            return request_allowed(
                self,
                allowed_origins=service.allowed_origins,
                require_origin=require_origin,
            )

        def _read_json(self) -> dict[str, Any]:
            return read_json_body(self, max_request_bytes=MAX_REQUEST_BYTES)

        def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
            send_json(
                self,
                payload,
                allowed_origins=service.allowed_origins,
                status=status,
            )

    return GoogleDocRequestHandler


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"Missing required field: {key}.")
    return value


def _layout_response(result: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "document_id": result.document_id,
        "title": result.title,
        "requests_sent": result.requests_sent,
        "message": result.summary,
    }
