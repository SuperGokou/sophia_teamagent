from __future__ import annotations

import json
import base64
import sys
import tempfile
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from legal_doc_agent.agents import NvidiaAgentRouter, load_web_agent_profiles_from_env  # noqa: E402
from legal_doc_agent.config import ConfigurationError, NvidiaConfig  # noqa: E402
from legal_doc_agent.web_generation import generate_web_legal_package  # noqa: E402
from legal_doc_agent.web_kb import build_web_knowledge_context, web_kb_path  # noqa: E402


MAX_REQUEST_BYTES = 1_000_000
VERCEL_PROVIDER_TIMEOUT_SECONDS = 75


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_json({"ok": True})

    def do_GET(self) -> None:  # noqa: N802
        self._send_json(
            {
                "ok": True,
                "service": "legal-doc-generation",
                "runtime": "vercel-python",
                "requires": ["NVIDIA_API_KEY"],
                "rag": {
                    "enabled": web_kb_path().exists(),
                    "engine": "sqlite-fts5",
                    "path": web_kb_path().name,
                },
            }
        )

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
            brief = _required_string(payload, "brief")
            if len(brief) < 20:
                raise ValueError("Brief is too short for legal document generation.")

            run_id = uuid4().hex
            output_root = Path(tempfile.gettempdir()) / "legal-doc-agent" / run_id
            output_path = output_root / f"legal_package_{run_id}.docx"
            artifact_dir = output_root / "artifacts"

            client = NvidiaAgentRouter(
                base_config=NvidiaConfig.from_env(
                    timeout_seconds=VERCEL_PROVIDER_TIMEOUT_SECONDS
                ),
                profiles=load_web_agent_profiles_from_env(),
            )
            knowledge_context = build_web_knowledge_context(brief)
            result = generate_web_legal_package(
                client=client,
                brief=brief,
                output_path=output_path,
                artifact_dir=artifact_dir,
                knowledge_context=knowledge_context,
            )
            self._send_json(
                {
                    "ok": True,
                    "draft": _read_artifact_markdown(result.artifact_dir),
                    "docx_name": result.output_path.name,
                    "docx_base64": _read_docx_base64(result.output_path),
                    "generation_mode": result.generation_mode,
                    "artifact_id": run_id,
                    "observations": [
                        asdict(observation) for observation in result.observations
                    ],
                    "message": (
                        "Generated provider-timeout recovery package."
                        if result.generation_mode == "timeout_recovery"
                        else "Generated with Vercel NVIDIA multi-agent harness."
                    ),
                }
            )
        except ConfigurationError as exc:
            print(f"configuration error: {exc}")
            self._send_json(
                {
                    "ok": False,
                    "error": "configuration",
                    "message": (
                        "NVIDIA service is not configured. Set NVIDIA_API_KEY "
                        "in the Vercel project environment."
                    ),
                },
                status=503,
            )
        except ValueError as exc:
            self._send_json(
                {"ok": False, "error": "bad_request", "message": str(exc)},
                status=400,
            )
        except Exception as exc:
            print(f"provider error: {exc}")
            self._send_json(
                {
                    "ok": False,
                    "error": "provider",
                    "message": (
                        "Online NVIDIA generation failed. Check Vercel runtime "
                        "logs for provider details."
                    ),
                },
                status=500,
            )

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
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"Missing required field: {key}.")
    return value


def _read_artifact_markdown(artifact_dir: Path) -> str:
    blocks: list[str] = []
    for path in sorted(artifact_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if text:
            blocks.append(text)
    return "\n\n---\n\n".join(blocks)


def _read_docx_base64(output_path: Path) -> str:
    return base64.b64encode(output_path.read_bytes()).decode("ascii")
