from __future__ import annotations

import json
import os
import unittest
from unittest.mock import Mock, patch

from legal_doc_agent.config import ConfigurationError, NvidiaConfig
from legal_doc_agent.nvidia import NvidiaClient, ProviderError


class NvidiaClientTests(unittest.TestCase):
    def test_requires_api_key(self) -> None:
        client = NvidiaClient(NvidiaConfig(api_key=None))

        with self.assertRaises(ConfigurationError):
            client.complete([{"role": "user", "content": "hello"}])

    def test_from_env_reads_project_dotenv_without_mutating_environment(self) -> None:
        dotenv_values = {
            "NVIDIA_API_KEY": "dotenv-key",
            "NVIDIA_BASE_URL": "https://example.test/v1",
            "NVIDIA_MODEL": "dotenv-model",
            "NVIDIA_TEMPERATURE": "0.4",
            "NVIDIA_TOP_P": "0.8",
            "NVIDIA_MAX_TOKENS": "1234",
            "NVIDIA_STREAM": "true",
        }

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("legal_doc_agent.config._load_dotenv_values", return_value=dotenv_values),
        ):
            config = NvidiaConfig.from_env()

        self.assertEqual(config.api_key, "dotenv-key")
        self.assertEqual(config.base_url, "https://example.test/v1")
        self.assertEqual(config.model, "dotenv-model")
        self.assertEqual(config.temperature, 0.4)
        self.assertEqual(config.top_p, 0.8)
        self.assertEqual(config.max_tokens, 1234)
        self.assertTrue(config.stream)
        self.assertNotIn("NVIDIA_API_KEY", os.environ)

    def test_process_environment_overrides_dotenv_values(self) -> None:
        with (
            patch.dict(os.environ, {"NVIDIA_API_KEY": "env-key"}, clear=True),
            patch(
                "legal_doc_agent.config._load_dotenv_values",
                return_value={"NVIDIA_API_KEY": "dotenv-key"},
            ),
        ):
            config = NvidiaConfig.from_env()

        self.assertEqual(config.api_key, "env-key")

    @patch("urllib.request.urlopen")
    def test_posts_openai_compatible_payload(self, urlopen: Mock) -> None:
        response = Mock()
        response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "draft"}}]}
        ).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        urlopen.return_value = response
        config = NvidiaConfig(
            api_key="key",
            model="minimaxai/minimax-m2.7",
            max_tokens=4096,
        )
        client = NvidiaClient(config)

        content = client.complete([{"role": "user", "content": "hello"}])

        self.assertEqual(content, "draft")
        request = urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://integrate.api.nvidia.com/v1/chat/completions",
        )
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "minimaxai/minimax-m2.7")
        self.assertEqual(payload["messages"][0]["content"], "hello")
        self.assertEqual(payload["temperature"], 1.0)
        self.assertEqual(payload["top_p"], 1.0)
        self.assertEqual(payload["max_tokens"], 4096)
        self.assertNotIn("chat_template_kwargs", payload)
        self.assertFalse(payload["stream"])

    @patch("urllib.request.urlopen")
    def test_can_send_thinking_flag_for_models_that_need_it(self, urlopen: Mock) -> None:
        response = Mock()
        response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "draft"}}]}
        ).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        urlopen.return_value = response
        client = NvidiaClient(NvidiaConfig(api_key="key", thinking=False))

        client.complete([{"role": "user", "content": "hello"}])

        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["chat_template_kwargs"], {"thinking": False})

    @patch("urllib.request.urlopen")
    def test_reports_truncated_reasoning_only_response(self, urlopen: Mock) -> None:
        response = Mock()
        response.read.return_value = json.dumps(
            {
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {
                            "content": "",
                            "reasoning_content": "thinking without final content",
                        },
                    }
                ]
            }
        ).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        urlopen.return_value = response
        client = NvidiaClient(NvidiaConfig(api_key="key", max_tokens=32))

        with self.assertRaisesRegex(ProviderError, "Increase max_tokens"):
            client.complete([{"role": "user", "content": "hello"}])

    @patch("urllib.request.urlopen")
    def test_can_parse_streaming_content_with_reasoning_options(
        self,
        urlopen: Mock,
    ) -> None:
        response = Mock()
        response.read.return_value = (
            'data: {"choices":[{"delta":{"reasoning_content":"thinking"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"draft "}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"done"}}]}\n\n'
            "data: [DONE]\n\n"
        ).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        urlopen.return_value = response
        client = NvidiaClient(
            NvidiaConfig(
                api_key="key",
                model="nvidia/nemotron-3-super-120b-a12b",
                max_tokens=16384,
                top_p=0.95,
                enable_thinking=True,
                reasoning_budget=16384,
                stream=True,
            )
        )

        content = client.complete([{"role": "user", "content": "hello"}])

        self.assertEqual(content, "draft done")
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "nvidia/nemotron-3-super-120b-a12b")
        self.assertTrue(payload["stream"])
        self.assertEqual(payload["top_p"], 0.95)
        self.assertEqual(payload["max_tokens"], 16384)
        self.assertEqual(payload["chat_template_kwargs"], {"enable_thinking": True})
        self.assertEqual(payload["reasoning_budget"], 16384)
        self.assertEqual(request.headers["Accept"], "text/event-stream")


if __name__ == "__main__":
    unittest.main()
