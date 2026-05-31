from __future__ import annotations

import json
import unittest
from unittest.mock import Mock, patch

from legal_doc_agent.config import ConfigurationError, NvidiaConfig
from legal_doc_agent.nvidia import NvidiaClient


class NvidiaClientTests(unittest.TestCase):
    def test_requires_api_key(self) -> None:
        client = NvidiaClient(NvidiaConfig(api_key=None))

        with self.assertRaises(ConfigurationError):
            client.complete([{"role": "user", "content": "hello"}])

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
            model="openai/gpt-oss-120b",
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
        self.assertEqual(payload["model"], "openai/gpt-oss-120b")
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


if __name__ == "__main__":
    unittest.main()
