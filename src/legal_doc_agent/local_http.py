"""Shared helpers for local-only HTTP bridge services."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlparse


DEFAULT_ALLOWED_ORIGINS = frozenset(
    {
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    }
)


def normalize_origin(origin: str | None) -> str:
    """Return the scheme, host, and port for an Origin header."""

    if not origin:
        return ""
    parsed = urlparse(origin.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    host = parsed.hostname
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{host}{port}"


def is_loopback_address(address: str) -> bool:
    """Return whether an address refers to the local machine."""

    if address in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ip_address(address).is_loopback
    except ValueError:
        return False


def request_allowed(
    handler: BaseHTTPRequestHandler,
    *,
    allowed_origins: frozenset[str],
    require_origin: bool,
) -> bool:
    """Validate local bridge requests by client address and Origin."""

    if not is_loopback_address(str(handler.client_address[0])):
        return False
    origin = handler.headers.get("Origin")
    if not origin:
        return not require_origin
    return normalize_origin(origin) in allowed_origins


def read_json_body(
    handler: BaseHTTPRequestHandler,
    *,
    max_request_bytes: int,
) -> dict[str, Any]:
    """Read a bounded JSON object from an HTTP request body."""

    try:
        content_length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise ValueError("Invalid Content-Length.") from exc
    if content_length <= 0:
        return {}
    if content_length > max_request_bytes:
        raise ValueError("Request body is too large.")
    raw_body = handler.rfile.read(content_length)
    try:
        data = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be JSON.") from exc
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")
    return data


def send_json(
    handler: BaseHTTPRequestHandler,
    payload: dict[str, Any],
    *,
    allowed_origins: frozenset[str],
    status: int = 200,
) -> None:
    """Send JSON with the local bridge CORS policy."""

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    origin = handler.headers.get("Origin")
    normalized_origin = normalize_origin(origin) if origin else ""
    if normalized_origin in allowed_origins:
        handler.send_header("Access-Control-Allow-Origin", normalized_origin)
    handler.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(body)
