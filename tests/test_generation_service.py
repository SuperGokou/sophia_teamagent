from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
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
            ) -> SimpleNamespace:
                captured["brief"] = brief
                artifact_dir.mkdir(parents=True)
                (artifact_dir / "draft.md").write_text("# Draft", encoding="utf-8")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("docx placeholder", encoding="utf-8")
                return SimpleNamespace(
                    output_path=output_path,
                    artifact_dir=artifact_dir,
                    observations=[],
                )

            service = LegalGenerationLocalService(
                spec_path=allowed_spec,
                output_dir=base / "out",
            )

            with (
                patch("legal_doc_agent.generation_service.NvidiaConfig.from_env", return_value=object()),
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
            self.assertIn("docx_name", result)
            self.assertNotIn("docx_path", result)
            self.assertNotIn("artifact_dir", result)
            self.assertEqual(
                captured["brief"],
                "Generate a real legal package with sufficient detail.",
            )
            self.assertIn("# Draft", result["draft"])


if __name__ == "__main__":
    unittest.main()
