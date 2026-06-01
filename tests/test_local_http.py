from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
import unittest

from legal_doc_agent.local_http import (
    DEFAULT_ALLOWED_ORIGINS,
    read_json_body,
    request_allowed,
    send_json,
)


class _FakeWriter:
    def __init__(self) -> None:
        self.body = b""

    def write(self, body: bytes) -> None:
        self.body += body


class LocalHttpTests(unittest.TestCase):
    def test_health_style_request_can_omit_origin_on_loopback(self) -> None:
        handler = SimpleNamespace(
            client_address=("127.0.0.1", 54321),
            headers={},
        )

        self.assertTrue(
            request_allowed(
                handler,  # type: ignore[arg-type]
                allowed_origins=DEFAULT_ALLOWED_ORIGINS,
                require_origin=False,
            )
        )

    def test_mutating_request_requires_trusted_origin(self) -> None:
        handler = SimpleNamespace(
            client_address=("127.0.0.1", 54321),
            headers={},
        )

        self.assertFalse(
            request_allowed(
                handler,  # type: ignore[arg-type]
                allowed_origins=DEFAULT_ALLOWED_ORIGINS,
                require_origin=True,
            )
        )

        handler.headers = {"Origin": "http://localhost:5173/ignored/path"}
        self.assertTrue(
            request_allowed(
                handler,  # type: ignore[arg-type]
                allowed_origins=DEFAULT_ALLOWED_ORIGINS,
                require_origin=True,
            )
        )

    def test_read_json_body_requires_object_within_size_limit(self) -> None:
        handler = SimpleNamespace(
            headers={"Content-Length": "13"},
            rfile=BytesIO(b'{"ok": true}'),
        )

        self.assertEqual(
            read_json_body(handler, max_request_bytes=20),  # type: ignore[arg-type]
            {"ok": True},
        )

        handler = SimpleNamespace(
            headers={"Content-Length": "13"},
            rfile=BytesIO(b'["not dict"]'),
        )
        with self.assertRaises(ValueError):
            read_json_body(handler, max_request_bytes=20)  # type: ignore[arg-type]

    def test_send_json_only_echoes_allowed_origin(self) -> None:
        allowed_handler = _WritableHandler("http://localhost:5173")
        send_json(
            allowed_handler,  # type: ignore[arg-type]
            {"ok": True},
            allowed_origins=DEFAULT_ALLOWED_ORIGINS,
        )
        self.assertEqual(
            allowed_handler.headers_sent["Access-Control-Allow-Origin"],
            "http://localhost:5173",
        )

        blocked_handler = _WritableHandler("https://evil.example")
        send_json(
            blocked_handler,  # type: ignore[arg-type]
            {"ok": True},
            allowed_origins=DEFAULT_ALLOWED_ORIGINS,
        )
        self.assertNotIn("Access-Control-Allow-Origin", blocked_handler.headers_sent)


class _WritableHandler:
    def __init__(self, origin: str) -> None:
        self.headers = {"Origin": origin}
        self.headers_sent: dict[str, str] = {}
        self.status = 0
        self.wfile = _FakeWriter()

    def send_response(self, status: int) -> None:
        self.status = status

    def send_header(self, key: str, value: str) -> None:
        self.headers_sent[key] = value

    def end_headers(self) -> None:
        return None


if __name__ == "__main__":
    unittest.main()
