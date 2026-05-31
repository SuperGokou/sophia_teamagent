from __future__ import annotations

import json
import unittest
from unittest.mock import Mock, patch

from legal_doc_agent.config import ConfigurationError, DeepSeekConfig
from legal_doc_agent.deepseek import DeepSeekClient


class DeepSeekClientTests(unittest.TestCase):
    def test_requires_api_key(self) -> None:
        client = DeepSeekClient(DeepSeekConfig(api_key=None))

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
        config = DeepSeekConfig(api_key="key", model="deepseek-v4-pro", max_tokens=100)
        client = DeepSeekClient(config)

        content = client.complete([{"role": "user", "content": "hello"}])

        self.assertEqual(content, "draft")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.deepseek.com/chat/completions")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "deepseek-v4-pro")
        self.assertEqual(payload["messages"][0]["content"], "hello")


if __name__ == "__main__":
    unittest.main()
