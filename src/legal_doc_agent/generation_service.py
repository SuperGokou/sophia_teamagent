"""Local HTTP bridge for NVIDIA legal document generation."""

from __future__ import annotations

import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from uuid import uuid4

from legal_doc_agent.agents import NvidiaAgentRouter
from legal_doc_agent.config import ConfigurationError, NvidiaConfig
from legal_doc_agent.harness import LegalDocumentAgent


MAX_REQUEST_BYTES = 1_000_000
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_PATH = PROJECT_ROOT / "prompts" / "delaware_c_corp_post_formation.txt"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "web"
DEFAULT_ALLOWED_ORIGINS = frozenset(
    {
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    }
)


class LegalGenerationLocalService:
    """Small request dispatcher for local legal document generation."""

    def __init__(
        self,
        *,
        spec_path: Path = DEFAULT_SPEC_PATH,
        output_dir: Path = DEFAULT_OUTPUT_DIR,
        base_url: str | None = None,
        allowed_origins: frozenset[str] = DEFAULT_ALLOWED_ORIGINS,
    ) -> None:
        self._spec_path = spec_path.resolve()
        self._output_dir = output_dir
        self._base_url = base_url
        self._allowed_origins = allowed_origins

    @property
    def allowed_origins(self) -> frozenset[str]:
        return self._allowed_origins

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "service": "legal-doc-generation",
            "requires": ["NVIDIA_API_KEY"],
        }

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        brief = _required_string(payload, "brief")
        if len(brief) < 20:
            raise ValueError("Brief is too short for legal document generation.")

        spec_path = self._spec_path
        run_id = uuid4().hex
        output_path = self._output_dir / f"legal_package_{run_id}.docx"
        artifact_dir = self._output_dir / f"artifacts_{run_id}"

        client = NvidiaAgentRouter(
            base_config=NvidiaConfig.from_env(base_url=self._base_url),
        )
        result = LegalDocumentAgent(client).generate(
            specification_path=spec_path,
            brief=brief,
            output_path=output_path,
            artifact_dir=artifact_dir,
        )
        markdown = _read_artifact_markdown(result.artifact_dir)
        return {
            "ok": True,
            "draft": markdown,
            "docx_name": result.output_path.name,
            "artifact_id": result.artifact_dir.name,
            "observations": [asdict(observation) for observation in result.observations],
            "message": "Generated with local NVIDIA multi-agent harness.",
        }


def run_generation_service(
    *,
    host: str = "127.0.0.1",
    port: int = 8766,
    spec_path: Path = DEFAULT_SPEC_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    base_url: str | None = None,
) -> None:
    """Run the local legal generation bridge until interrupted."""

    service = LegalGenerationLocalService(
        spec_path=spec_path,
        output_dir=output_dir,
        base_url=base_url,
    )
    server = ThreadingHTTPServer((host, port), _make_handler(service))
    print(f"Legal generation service listening on http://{host}:{port}")
    print("Endpoints: GET /health, POST /legal-doc/generate")
    server.serve_forever()


def _make_handler(service: LegalGenerationLocalService) -> type[BaseHTTPRequestHandler]:
    class LegalGenerationRequestHandler(BaseHTTPRequestHandler):
        server_version = "LegalDocGenerationBridge/0.1"

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
                self._send_json(service.health())
                return
            self._send_json({"ok": False, "error": "not_found"}, status=404)

        def do_POST(self) -> None:  # noqa: N802
            if not self._request_allowed(require_origin=True):
                self._send_json({"ok": False, "error": "request_not_allowed"}, status=403)
                return
            routes: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
                "/legal-doc/generate": service.generate,
            }
            handler = routes.get(self.path)
            if handler is None:
                self._send_json({"ok": False, "error": "not_found"}, status=404)
                return

            try:
                payload = self._read_json()
                self._send_json(handler(payload))
            except ConfigurationError as exc:
                print(f"configuration error: {exc}")
                self._send_json(
                    {
                        "ok": False,
                        "error": "configuration",
                        "message": "NVIDIA service is not configured. Set NVIDIA_API_KEY and restart the local service.",
                    },
                    status=503,
                )
            except ValueError as exc:
                self._send_json({"ok": False, "error": "bad_request", "message": str(exc)}, status=400)
            except Exception as exc:  # pragma: no cover - provider objects vary by version.
                print(f"provider error: {exc}")
                self._send_json(
                    {
                        "ok": False,
                        "error": "provider",
                        "message": "NVIDIA generation failed. Check the local service terminal for details.",
                    },
                    status=500,
                )

        def log_message(self, format: str, *args: Any) -> None:
            print(f"{self.address_string()} - {format % args}")

        def _request_allowed(self, *, require_origin: bool) -> bool:
            if not _is_loopback_address(str(self.client_address[0])):
                return False
            origin = self.headers.get("Origin")
            if not origin:
                return not require_origin
            return _normalize_origin(origin) in service.allowed_origins

        def _read_json(self) -> dict[str, Any]:
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise ValueError("Invalid Content-Length.") from exc
            if content_length <= 0:
                return {}
            if content_length > MAX_REQUEST_BYTES:
                raise ValueError("Request body is too large.")
            raw_body = self.rfile.read(content_length)
            try:
                data = json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise ValueError("Request body must be JSON.") from exc
            if not isinstance(data, dict):
                raise ValueError("Request body must be a JSON object.")
            return data

        def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            origin = self.headers.get("Origin")
            normalized_origin = _normalize_origin(origin) if origin else ""
            if normalized_origin in service.allowed_origins:
                self.send_header("Access-Control-Allow-Origin", normalized_origin)
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)

    return LegalGenerationRequestHandler


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"Missing required field: {key}.")
    return value


def _normalize_origin(origin: str | None) -> str:
    if not origin:
        return ""
    parsed = urlparse(origin.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    host = parsed.hostname
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{host}{port}"


def _is_loopback_address(address: str) -> bool:
    if address in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ip_address(address).is_loopback
    except ValueError:
        return False


def _read_artifact_markdown(artifact_dir: Path) -> str:
    blocks: list[str] = []
    for path in sorted(artifact_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if text:
            blocks.append(text)
    return "\n\n---\n\n".join(blocks)
