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
from legal_doc_agent.run_events import RunStore  # noqa: E402
from legal_doc_agent.web_generation import generate_web_legal_package  # noqa: E402
from legal_doc_agent.web_kb import build_web_knowledge_context, web_kb_path  # noqa: E402


MAX_REQUEST_BYTES = 1_000_000
VERCEL_PROVIDER_TIMEOUT_SECONDS = 75
_RUN_STORE = RunStore()


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_json({"ok": True})

    def do_GET(self) -> None:  # noqa: N802
        run_id = _run_id_from_status_path(self.path)
        if run_id:
            self._send_json(
                _RUN_STORE.get(run_id)
                or {"ok": False, "error": "run_not_found", "run_id": run_id},
                status=200,
            )
            return
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
            _RUN_STORE.start(run_id, message="Accepted Vercel legal document generation request.")
            output_root = Path(tempfile.gettempdir()) / "legal-doc-agent" / run_id
            output_path = output_root / f"legal_package_{run_id}.docx"
            artifact_dir = output_root / "artifacts"

            client = NvidiaAgentRouter(
                base_config=NvidiaConfig.from_env(
                    timeout_seconds=VERCEL_PROVIDER_TIMEOUT_SECONDS
                ),
                profiles=load_web_agent_profiles_from_env(),
            )
            _RUN_STORE.append(
                run_id,
                event_type="rag_started",
                agent_id="browser",
                status="running",
                message="Searching deployed SQLite FTS5 legal knowledge base.",
            )
            knowledge_context = build_web_knowledge_context(brief)
            _RUN_STORE.append(
                run_id,
                event_type="rag_completed",
                agent_id="browser",
                status="completed",
                message=(
                    "Retrieved legal authority context."
                    if knowledge_context
                    else "No matching deployed legal authority context was found."
                ),
            )
            _RUN_STORE.append(
                run_id,
                event_type="draft_started",
                agent_id="file",
                status="running",
                message="Starting Vercel multi-agent legal package generation.",
            )
            result = generate_web_legal_package(
                client=client,
                brief=brief,
                output_path=output_path,
                artifact_dir=artifact_dir,
                knowledge_context=knowledge_context,
            )
            for observation in result.observations:
                _RUN_STORE.append(
                    run_id,
                    event_type="agent_observation",
                    agent_id=_agent_id_for_observation(observation.summary),
                    status=observation.status,
                    message=observation.summary,
                    data={
                        "next_actions": observation.next_actions,
                        "artifacts": observation.artifacts,
                    },
                )
            response = {
                "ok": True,
                "run_id": run_id,
                "status": "completed",
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
                    else "Generated with Vercel AI multi-agent harness."
                ),
            }
            _RUN_STORE.append(
                run_id,
                event_type="docx_ready",
                agent_id="file",
                status="completed",
                message=f"Word package is ready: {result.output_path.name}.",
            )
            _RUN_STORE.complete(
                run_id,
                result=_result_summary(response),
                message="Reviewer quality gate completed and package is ready.",
            )
            response["events"] = (_RUN_STORE.get(run_id) or {}).get("events", [])
            self._send_json(response)
        except ConfigurationError as exc:
            print(f"configuration error: {exc}")
            if "run_id" in locals():
                _RUN_STORE.fail(
                    run_id,
                    error=type(exc).__name__,
                    message=str(exc) or "Configuration error.",
                )
            self._send_json(
                {
                    "ok": False,
                    "error": "configuration",
                    "message": (
                        "AI generation service is not configured. Set the provider API key "
                        "in the Vercel project environment."
                    ),
                },
                status=503,
            )
        except ValueError as exc:
            if "run_id" in locals():
                _RUN_STORE.fail(
                    run_id,
                    error=type(exc).__name__,
                    message=str(exc) or "Bad request.",
                )
            self._send_json(
                {"ok": False, "error": "bad_request", "message": str(exc)},
                status=400,
            )
        except Exception as exc:
            print(f"provider error: {exc}")
            if "run_id" in locals():
                _RUN_STORE.fail(
                    run_id,
                    error=type(exc).__name__,
                    message=str(exc) or "Provider error.",
                )
            self._send_json(
                {
                    "ok": False,
                    "error": "provider",
                    "message": (
                        "Online AI generation failed. Check Vercel runtime "
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


def _agent_id_for_observation(summary: str) -> str:
    value = summary.lower()
    if any(token in value for token in ("rag", "sqlite", "citation", "knowledge", "authority")):
        return "browser"
    if any(token in value for token in ("draft", "docx", "word", "segment", "package")):
        return "file"
    if any(token in value for token in ("review", "quality", "gate")):
        return "reviewer"
    return "planner"


def _result_summary(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "docx_name": response.get("docx_name"),
        "generation_mode": response.get("generation_mode"),
        "artifact_id": response.get("artifact_id"),
        "message": response.get("message"),
    }


def _run_id_from_status_path(path: str) -> str:
    normalized = path.split("?", 1)[0].strip("/")
    prefixes = ("api/runs/", "runs/")
    for prefix in prefixes:
        if normalized.startswith(prefix):
            return normalized[len(prefix) :].strip("/")
    return ""


def _read_artifact_markdown(artifact_dir: Path) -> str:
    blocks: list[str] = []
    for path in sorted(artifact_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if text:
            blocks.append(text)
    return "\n\n---\n\n".join(blocks)


def _read_docx_base64(output_path: Path) -> str:
    return base64.b64encode(output_path.read_bytes()).decode("ascii")
