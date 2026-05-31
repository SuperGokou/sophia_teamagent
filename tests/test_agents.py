from __future__ import annotations

import json
import unittest
from unittest.mock import Mock, patch

from legal_doc_agent.agents import DRAFTER_ROLE, PLANNER_ROLE, NvidiaAgentRouter
from legal_doc_agent.config import NvidiaConfig


class AgentRouterTests(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_routes_planner_and_drafter_to_different_models(self, urlopen: Mock) -> None:
        response = Mock()
        response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "draft"}}]}
        ).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        urlopen.return_value = response
        router = NvidiaAgentRouter(base_config=NvidiaConfig(api_key="key"))
        messages = [{"role": "user", "content": "hello"}]

        router.complete(messages, role=PLANNER_ROLE)
        first_request = urlopen.call_args.args[0]
        first_payload = json.loads(first_request.data.decode("utf-8"))
        router.complete(messages, role=DRAFTER_ROLE)
        second_request = urlopen.call_args.args[0]
        second_payload = json.loads(second_request.data.decode("utf-8"))

        self.assertEqual(first_payload["model"], "openai/gpt-oss-120b")
        self.assertEqual(first_payload["temperature"], 1.0)
        self.assertNotIn("chat_template_kwargs", first_payload)
        self.assertEqual(second_payload["model"], "deepseek-ai/deepseek-v4-pro")
        self.assertEqual(second_payload["top_p"], 0.95)
        self.assertEqual(second_payload["max_tokens"], 16384)
        self.assertEqual(second_payload["chat_template_kwargs"], {"thinking": False})


if __name__ == "__main__":
    unittest.main()
