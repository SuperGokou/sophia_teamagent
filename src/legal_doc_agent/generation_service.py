"""Local HTTP bridge for NVIDIA legal document generation."""

from __future__ import annotations

import base64
from threading import Thread
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from legal_doc_agent.agents import NvidiaAgentRouter, load_web_agent_profiles_from_env
from legal_doc_agent.config import ConfigurationError, NvidiaConfig
from legal_doc_agent.local_http import (
    DEFAULT_ALLOWED_ORIGINS,
    read_json_body,
    request_allowed,
    send_json,
)
from legal_doc_agent.run_events import RunStore
from legal_doc_agent.web_generation import generate_web_legal_package
from legal_doc_agent.web_kb import build_web_knowledge_context, web_kb_path


MAX_REQUEST_BYTES = 1_000_000
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_PATH = PROJECT_ROOT / "prompts" / "delaware_c_corp_post_formation.txt"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "web"


class LegalGenerationLocalService:
    """Small request dispatcher for local legal document generation."""

    def __init__(
        self,
        *,
        spec_path: Path = DEFAULT_SPEC_PATH,
        output_dir: Path = DEFAULT_OUTPUT_DIR,
        base_url: str | None = None,
        allowed_origins: frozenset[str] = DEFAULT_ALLOWED_ORIGINS,
        run_store: RunStore | None = None,
    ) -> None:
        self._spec_path = spec_path.resolve()
        self._output_dir = output_dir
        self._base_url = base_url
        self._allowed_origins = allowed_origins
        self._run_store = run_store or RunStore()

    @property
    def allowed_origins(self) -> frozenset[str]:
        return self._allowed_origins

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "service": "legal-doc-generation",
            "requires": ["NVIDIA_API_KEY"],
            "rag": {
                "enabled": web_kb_path().exists(),
                "engine": "sqlite-fts5",
                "path": web_kb_path().name,
            },
        }

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        brief = _required_string(payload, "brief")
        if len(brief) < 20:
            raise ValueError("Brief is too short for legal document generation.")

        run_id = uuid4().hex
        self._run_store.start(run_id, message="Accepted legal document generation request.")
        return self._complete_started_run(run_id, brief)

    def start_generation(self, payload: dict[str, Any]) -> dict[str, Any]:
        brief = _required_string(payload, "brief")
        if len(brief) < 20:
            raise ValueError("Brief is too short for legal document generation.")

        run_id = uuid4().hex
        self._run_store.start(run_id, message="Accepted async legal document generation request.")
        worker = Thread(
            target=self._complete_started_run_safely,
            args=(run_id, brief),
            daemon=True,
        )
        worker.start()
        return self.run_status(run_id)

    def _complete_started_run_safely(self, run_id: str, brief: str) -> None:
        try:
            self._complete_started_run(run_id, brief)
        except Exception as exc:  # pragma: no cover - worker failures are surfaced through run_status.
            print(f"generation worker error: run_id={run_id} error={exc}", flush=True)

    def _complete_started_run(self, run_id: str, brief: str) -> dict[str, Any]:
        output_path = self._output_dir / f"legal_package_{run_id}.docx"
        artifact_dir = self._output_dir / f"artifacts_{run_id}"

        try:
            client = NvidiaAgentRouter(
                base_config=NvidiaConfig.from_env(
                    base_url=self._base_url,
                    timeout_seconds=120,
                ),
                profiles=load_web_agent_profiles_from_env(),
            )
            print(f"generation started: run_id={run_id}", flush=True)
            self._run_store.append(
                run_id,
                event_type="rag_started",
                agent_id="browser",
                status="running",
                message="Searching deployed SQLite FTS5 legal knowledge base.",
            )
            knowledge_context = build_web_knowledge_context(brief)
            self._run_store.append(
                run_id,
                event_type="rag_completed",
                agent_id="browser",
                status="completed",
                message=(
                    "Retrieved legal authority context."
                    if knowledge_context
                    else "No matching local legal authority context was found."
                ),
            )
            self._run_store.append(
                run_id,
                event_type="draft_started",
                agent_id="file",
                status="running",
                message="Starting multi-agent legal package generation.",
            )
            result = generate_web_legal_package(
                client=client,
                brief=brief,
                output_path=output_path,
                artifact_dir=artifact_dir,
                knowledge_context=knowledge_context,
            )
            print(f"generation finished: run_id={run_id}", flush=True)
            for observation in result.observations:
                self._run_store.append(
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
            markdown = _read_artifact_markdown(result.artifact_dir)
            response = {
                "ok": True,
                "run_id": run_id,
                "status": "completed",
                "draft": markdown,
                "docx_name": result.output_path.name,
                "docx_base64": _read_docx_base64(result.output_path),
                "generation_mode": result.generation_mode,
                "artifact_id": result.artifact_dir.name,
                "observations": [asdict(observation) for observation in result.observations],
                "message": (
                    "Generated provider-timeout recovery package."
                    if result.generation_mode == "timeout_recovery"
                    else "Generated with local AI multi-agent harness."
                ),
            }
            self._run_store.append(
                run_id,
                event_type="docx_ready",
                agent_id="file",
                status="completed",
                message=f"Word package is ready: {result.output_path.name}.",
            )
            self._run_store.complete(
                run_id,
                result=_result_payload(response),
                message="Reviewer quality gate completed and package is ready.",
            )
            status = self.run_status(run_id)
            response["events"] = status.get("events", [])
            return response
        except Exception as exc:
            self._run_store.fail(
                run_id,
                error=type(exc).__name__,
                message=str(exc) or "Generation failed.",
            )
            raise

    def run_status(self, run_id: str) -> dict[str, Any]:
        record = self._run_store.get(run_id.strip())
        if record is None:
            return {"ok": False, "error": "run_not_found", "run_id": run_id}
        return record


def run_generation_service(
    *,
    host: str = "127.0.0.1",
    port: int = 9766,
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
    print("Endpoints: GET /health, GET /legal-doc/runs/<run_id>, POST /legal-doc/generate")
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
            run_id = _run_id_from_status_path(self.path)
            if run_id:
                self._send_json(service.run_status(run_id))
                return
            self._send_json({"ok": False, "error": "not_found"}, status=404)

        def do_POST(self) -> None:  # noqa: N802
            if not self._request_allowed(require_origin=True):
                self._send_json({"ok": False, "error": "request_not_allowed"}, status=403)
                return
            routes: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
                "/legal-doc/generate": service.generate,
                "/legal-doc/generate/start": service.start_generation,
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
                        "message": "AI generation service is not configured. Set the provider API key and restart the local service.",
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
                        "message": "AI generation failed. Check the local service terminal for details.",
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

    return LegalGenerationRequestHandler


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


def _agent_id_for_observation(summary: str) -> str:
    value = summary.lower()
    if any(token in value for token in ("rag", "sqlite", "citation", "knowledge", "authority")):
        return "browser"
    if any(token in value for token in ("draft", "docx", "word", "segment", "package")):
        return "file"
    if any(token in value for token in ("review", "quality", "gate")):
        return "reviewer"
    return "planner"


def _result_payload(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "draft": response.get("draft"),
        "docx_name": response.get("docx_name"),
        "docx_base64": response.get("docx_base64"),
        "generation_mode": response.get("generation_mode"),
        "artifact_id": response.get("artifact_id"),
        "observations": response.get("observations", []),
        "message": response.get("message"),
    }


def _run_id_from_status_path(path: str) -> str:
    prefix = "/legal-doc/runs/"
    if not path.startswith(prefix):
        return ""
    return path[len(prefix) :].strip("/")


def _read_docx_base64(output_path: Path) -> str:
    return base64.b64encode(output_path.read_bytes()).decode("ascii")
