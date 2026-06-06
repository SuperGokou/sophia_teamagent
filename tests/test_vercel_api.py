from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import unittest

from api.index import handler


class _Writable:
    def __init__(self) -> None:
        self.body = b""

    def write(self, body: bytes) -> None:
        self.body += body


class VercelApiTests(unittest.TestCase):
    def test_post_returns_structured_run_events(self) -> None:
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
                (artifact_dir / "draft.md").write_text("# Draft", encoding="utf-8")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"docx")
                return SimpleNamespace(
                    output_path=output_path,
                    artifact_dir=artifact_dir,
                    observations=[],
                    generation_mode="nvidia",
                )

            instance = object.__new__(handler)
            body = json.dumps({"brief": "Generate a long enough legal document package."}).encode("utf-8")
            instance.headers = {"Content-Length": str(len(body))}
            instance.rfile = BytesIO(body)
            instance.wfile = _Writable()
            instance.status = 0
            instance.headers_sent = {}
            instance.send_response = lambda status: setattr(instance, "status", status)
            instance.send_header = lambda key, value: instance.headers_sent.__setitem__(key, value)
            instance.end_headers = lambda: None

            with (
                patch("api.index.tempfile.gettempdir", return_value=str(base)),
                patch("api.index.NvidiaConfig.from_env", return_value=object()),
                patch("api.index.NvidiaAgentRouter", return_value=object()),
                patch("api.index.generate_web_legal_package", fake_generate_web_legal_package),
            ):
                instance.do_POST()

            response = json.loads(instance.wfile.body.decode("utf-8"))
            self.assertEqual(instance.status, 200)
            self.assertTrue(response["ok"])
            self.assertRegex(response["run_id"], r"^[0-9a-f]{32}$")
            self.assertEqual(response["status"], "completed")
            self.assertGreaterEqual(len(response["events"]), 3)
            self.assertEqual(response["events"][0]["type"], "run_started")
            self.assertEqual(response["events"][-1]["type"], "run_completed")
            self.assertEqual(base64.b64decode(response["docx_base64"]), b"docx")

            status_instance = object.__new__(handler)
            status_instance.path = f"/api/runs/{response['run_id']}"
            status_instance.wfile = _Writable()
            status_instance.status = 0
            status_instance.headers_sent = {}
            status_instance.send_response = lambda status: setattr(status_instance, "status", status)
            status_instance.send_header = lambda key, value: status_instance.headers_sent.__setitem__(key, value)
            status_instance.end_headers = lambda: None

            status_instance.do_GET()

            status_response = json.loads(status_instance.wfile.body.decode("utf-8"))
            self.assertTrue(status_response["ok"])
            self.assertEqual(status_response["run_id"], response["run_id"])
            self.assertEqual(status_response["status"], "completed")
            self.assertEqual(status_response["result"]["docx_name"], response["docx_name"])


if __name__ == "__main__":
    unittest.main()
