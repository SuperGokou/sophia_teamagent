from __future__ import annotations

import json
import os
import unittest
from unittest.mock import Mock, patch

from legal_doc_agent.agents import (
    ANALYST_ROLE,
    DRAFTER_ROLE,
    PLANNER_ROLE,
    REASONER_ROLE,
    NvidiaAgentRouter,
    load_agent_profiles_from_env,
)
from legal_doc_agent.config import NvidiaConfig


class AgentRouterTests(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_routes_roles_to_different_models(self, urlopen: Mock) -> None:
        response = _mock_response(
            {"choices": [{"message": {"content": "draft"}}]}
        )
        stream_response = _mock_stream_response("reasoned draft")
        urlopen.side_effect = [response, response, response, stream_response, response]
        router = NvidiaAgentRouter(base_config=NvidiaConfig(api_key="key"))
        messages = [{"role": "user", "content": "hello"}]

        router.complete(messages, role=PLANNER_ROLE)
        first_request = urlopen.call_args.args[0]
        first_payload = json.loads(first_request.data.decode("utf-8"))
        router.complete(messages, role=DRAFTER_ROLE)
        second_request = urlopen.call_args.args[0]
        second_payload = json.loads(second_request.data.decode("utf-8"))
        router.complete(messages, role=ANALYST_ROLE)
        third_request = urlopen.call_args.args[0]
        third_payload = json.loads(third_request.data.decode("utf-8"))
        router.complete(messages, role=REASONER_ROLE)
        fourth_request = urlopen.call_args.args[0]
        fourth_payload = json.loads(fourth_request.data.decode("utf-8"))

        self.assertEqual(first_payload["model"], "google/gemma-3n-e4b-it")
        self.assertEqual(first_payload["temperature"], 0.2)
        self.assertEqual(first_payload["top_p"], 0.7)
        self.assertEqual(first_payload["max_tokens"], 2048)
        self.assertNotIn("chat_template_kwargs", first_payload)
        self.assertEqual(second_payload["model"], "deepseek-ai/deepseek-v4-pro")
        self.assertEqual(second_payload["top_p"], 0.95)
        self.assertEqual(second_payload["max_tokens"], 16384)
        self.assertEqual(second_payload["chat_template_kwargs"], {"thinking": False})
        self.assertEqual(third_payload["model"], "minimaxai/minimax-m2.7")
        self.assertEqual(third_payload["temperature"], 1.0)
        self.assertEqual(third_payload["top_p"], 0.95)
        self.assertEqual(third_payload["max_tokens"], 8192)
        self.assertNotIn("chat_template_kwargs", third_payload)
        self.assertEqual(fourth_payload["model"], "nvidia/nemotron-3-super-120b-a12b")
        self.assertEqual(fourth_payload["temperature"], 1.0)
        self.assertEqual(fourth_payload["top_p"], 0.95)
        self.assertEqual(fourth_payload["max_tokens"], 16384)
        self.assertTrue(fourth_payload["stream"])
        self.assertEqual(
            fourth_payload["chat_template_kwargs"],
            {"enable_thinking": True},
        )
        self.assertEqual(fourth_payload["reasoning_budget"], 16384)

        router.complete(messages, role="reviewer")
        fifth_request = urlopen.call_args.args[0]
        fifth_payload = json.loads(fifth_request.data.decode("utf-8"))
        self.assertEqual(fifth_payload["model"], "google/gemma-3n-e4b-it")
        self.assertEqual(fifth_payload["temperature"], 0.2)
        self.assertEqual(fifth_payload["top_p"], 0.7)
        self.assertEqual(fifth_payload["max_tokens"], 2048)
        self.assertFalse(fifth_payload["stream"])
        self.assertNotIn("chat_template_kwargs", fifth_payload)
        self.assertNotIn("reasoning_budget", fifth_payload)

    def test_role_profiles_read_project_dotenv_values(self) -> None:
        dotenv_values = {
            "NVIDIA_DRAFTER_MODEL": "dotenv-drafter",
            "NVIDIA_DRAFTER_TEMPERATURE": "0.3",
            "NVIDIA_DRAFTER_TOP_P": "0.7",
            "NVIDIA_DRAFTER_MAX_TOKENS": "2048",
            "NVIDIA_DRAFTER_THINKING": "false",
        }

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("legal_doc_agent.config._load_dotenv_values", return_value=dotenv_values),
        ):
            profiles = load_agent_profiles_from_env()

        drafter = profiles[DRAFTER_ROLE]
        self.assertEqual(drafter.model, "dotenv-drafter")
        self.assertEqual(drafter.temperature, 0.3)
        self.assertEqual(drafter.top_p, 0.7)
        self.assertEqual(drafter.max_tokens, 2048)
        self.assertFalse(drafter.thinking)


def _mock_response(payload: dict[str, object]) -> Mock:
    response = Mock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    return response


def _mock_stream_response(content: str) -> Mock:
    response = Mock()
    response.read.return_value = (
        f'data: {{"choices":[{{"delta":{{"content":"{content}"}}}}]}}\n\n'
        "data: [DONE]\n\n"
    ).encode("utf-8")
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    return response


if __name__ == "__main__":
    unittest.main()
