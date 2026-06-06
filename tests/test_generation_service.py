from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import base64
import tempfile
import time
import unittest

from legal_doc_agent.generation_service import (
    LegalGenerationLocalService,
    _make_handler,
)
from legal_doc_agent.local_http import is_loopback_address, normalize_origin


class LegalGenerationLocalServiceTests(unittest.TestCase):
    def test_health_reports_generation_service(self) -> None:
        service = LegalGenerationLocalService()

        result = service.health()

        self.assertTrue(result["ok"])
        self.assertEqual(result["service"], "legal-doc-generation")
        self.assertIn("NVIDIA_API_KEY", result["requires"])

    def test_generate_requires_non_empty_brief(self) -> None:
        service = LegalGenerationLocalService()

        with self.assertRaises(ValueError):
            service.generate({})

    def test_generate_rejects_too_short_brief(self) -> None:
        service = LegalGenerationLocalService()

        with self.assertRaises(ValueError):
            service.generate({"brief": "short"})

    def test_normalize_origin_strips_path_and_rejects_invalid_values(self) -> None:
        self.assertEqual(
            normalize_origin("http://localhost:5173/some/path"),
            "http://localhost:5173",
        )
        self.assertEqual(normalize_origin("not a url"), "")
        self.assertTrue(is_loopback_address("127.0.0.1"))
        self.assertFalse(is_loopback_address("192.168.1.10"))

    def test_post_requires_loopback_and_allowed_origin(self) -> None:
        service = LegalGenerationLocalService()
        handler_type = _make_handler(service)
        handler = object.__new__(handler_type)
        handler.client_address = ("127.0.0.1", 12345)
        handler.headers = {"Origin": "http://localhost:5173"}
        self.assertTrue(handler._request_allowed(require_origin=True))

        handler.headers = {}
        self.assertFalse(handler._request_allowed(require_origin=True))

        handler.client_address = ("192.168.1.10", 12345)
        handler.headers = {"Origin": "http://localhost:5173"}
        self.assertFalse(handler._request_allowed(require_origin=True))

    def test_generate_ignores_payload_spec_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            allowed_spec = base / "allowed_spec.txt"
            allowed_spec.write_text("allowed", encoding="utf-8")
            forbidden_spec = base / "secret.txt"
            forbidden_spec.write_text("secret", encoding="utf-8")
            captured: dict[str, Path] = {}

            def fake_generate_web_legal_package(
                *,
                client: object,
                brief: str,
                output_path: Path,
                artifact_dir: Path,
                knowledge_context: str | None = None,
            ) -> SimpleNamespace:
                captured["brief"] = brief
                captured["knowledge_context"] = knowledge_context
                artifact_dir.mkdir(parents=True)
                (artifact_dir / "draft.md").write_text("# Draft", encoding="utf-8")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("docx placeholder", encoding="utf-8")
                return SimpleNamespace(
                    output_path=output_path,
                    artifact_dir=artifact_dir,
                    observations=[],
                    generation_mode="nvidia",
                )

            service = LegalGenerationLocalService(
                spec_path=allowed_spec,
                output_dir=base / "out",
            )

            with (
                patch("legal_doc_agent.generation_service.NvidiaConfig.from_env", return_value=object()) as from_env,
                patch("legal_doc_agent.generation_service.NvidiaAgentRouter", return_value=object()),
                patch(
                    "legal_doc_agent.generation_service.generate_web_legal_package",
                    fake_generate_web_legal_package,
                ),
            ):
                result = service.generate(
                    {
                        "brief": "Generate a real legal package with sufficient detail.",
                        "spec": str(forbidden_spec),
                    }
                )

            self.assertTrue(result["ok"])
            self.assertEqual(from_env.call_args.kwargs["timeout_seconds"], 120)
            self.assertIn("docx_name", result)
            self.assertEqual(
                base64.b64decode(result["docx_base64"]),
                b"docx placeholder",
            )
            self.assertNotIn("docx_path", result)
            self.assertNotIn("artifact_dir", result)
            self.assertRegex(result["run_id"], r"^[0-9a-f]{32}$")
            self.assertEqual(result["status"], "completed")
            self.assertGreaterEqual(len(result["events"]), 3)
            self.assertEqual(result["events"][0]["type"], "run_started")
            self.assertEqual(result["events"][-1]["type"], "run_completed")
            self.assertTrue(all(event["run_id"] == result["run_id"] for event in result["events"]))
            status = service.run_status(result["run_id"])
            self.assertTrue(status["ok"])
            self.assertEqual(status["status"], "completed")
            self.assertEqual(status["run_id"], result["run_id"])
            self.assertEqual(status["result"]["docx_name"], result["docx_name"])
            self.assertEqual(
                captured["brief"],
                "Generate a real legal package with sufficient detail.",
            )
            self.assertIn("# Draft", result["draft"])

    def test_start_generation_returns_run_id_before_result_is_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)

            def fake_generate_web_legal_package(
                *,
                client: object,
                brief: str,
                output_path: Path,
                artifact_dir: Path,
                knowledge_context: str | None = None,
            ) -> SimpleNamespace:
                artifact_dir.mkdir(parents=True)
                (artifact_dir / "draft.md").write_text("# Async Draft", encoding="utf-8")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("async docx", encoding="utf-8")
                return SimpleNamespace(
                    output_path=output_path,
                    artifact_dir=artifact_dir,
                    observations=[],
                    generation_mode="nvidia",
                )

            service = LegalGenerationLocalService(output_dir=base / "out")

            with (
                patch("legal_doc_agent.generation_service.NvidiaConfig.from_env", return_value=object()),
                patch("legal_doc_agent.generation_service.NvidiaAgentRouter", return_value=object()),
                patch(
                    "legal_doc_agent.generation_service.generate_web_legal_package",
                    fake_generate_web_legal_package,
                ),
            ):
                started = service.start_generation(
                    {"brief": "Generate an async legal package with sufficient detail."}
                )

                self.assertTrue(started["ok"])
                self.assertRegex(started["run_id"], r"^[0-9a-f]{32}$")
                self.assertEqual(started["status"], "running")

                status = started
                for _ in range(30):
                    status = service.run_status(started["run_id"])
                    if status["status"] == "completed":
                        break
                    time.sleep(0.02)

            self.assertEqual(status["status"], "completed")
            self.assertEqual(status["result"]["docx_name"], f"legal_package_{started['run_id']}.docx")
            self.assertEqual(
                base64.b64decode(status["result"]["docx_base64"]),
                b"async docx",
            )

    def test_run_status_reports_missing_run(self) -> None:
        service = LegalGenerationLocalService()

        result = service.run_status("missing")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "run_not_found")


if __name__ == "__main__":
    unittest.main()
