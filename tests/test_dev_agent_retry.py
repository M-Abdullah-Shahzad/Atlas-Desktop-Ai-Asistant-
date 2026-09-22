import sys
import types
import unittest
from unittest.mock import patch

import actions.dev_agent as dev_agent


class _Transient503(Exception):
    status_code = 503


class DevAgentRetryTests(unittest.TestCase):
    def test_model_falls_back_after_transient_503(self):
        calls = []

        class FakeCompletions:
            def create(self, **kwargs):
                calls.append(kwargs)
                if len(calls) < 3:
                    raise _Transient503("503 UNAVAILABLE: high demand")
                return types.SimpleNamespace(
                    choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="generated"))]
                )

        fake_groq = types.SimpleNamespace(
            Groq=lambda **kwargs: types.SimpleNamespace(
                chat=types.SimpleNamespace(completions=FakeCompletions())
            )
        )

        with patch.dict(sys.modules, {"groq": fake_groq}), patch.object(
            dev_agent, "_get_api_key", return_value="test-key"
        ), patch.object(dev_agent.time, "sleep") as sleep, patch(
            "builtins.print"
        ) as output:
            result = dev_agent._get_model("test-model").generate_content("prompt")

        self.assertEqual(result.text, "generated")
        self.assertEqual(len(calls), 3)
        self.assertEqual(
            [call["model"] for call in calls],
            list(dev_agent.GROQ_FALLBACK_MODELS),
        )
        sleep.assert_not_called()
        self.assertTrue(
            any("trying fallback model" in call.args[0] for call in output.call_args_list)
        )

    def test_model_falls_back_for_decommissioned_model(self):
        calls = []

        class _DeprecatedModel(Exception):
            status_code = 400

        class FakeCompletions:
            def create(self, **kwargs):
                calls.append(kwargs)
                if len(calls) == 1:
                    raise _DeprecatedModel("model has been decommissioned")
                return types.SimpleNamespace(
                    choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="generated"))]
                )

        fake_groq = types.SimpleNamespace(
            Groq=lambda **kwargs: types.SimpleNamespace(
                chat=types.SimpleNamespace(completions=FakeCompletions())
            )
        )

        with patch.dict(sys.modules, {"groq": fake_groq}), patch.object(
            dev_agent, "_get_api_key", return_value="test-key"
        ):
            result = dev_agent._get_model("test-model").generate_content("prompt")

        self.assertEqual(result.text, "generated")
        self.assertEqual(
            [call["model"] for call in calls],
            list(dev_agent.GROQ_FALLBACK_MODELS[:2]),
        )

    def test_non_transient_errors_are_not_retried(self):
        class FakeCompletions:
            def create(self, **kwargs):
                raise ValueError("invalid request")

        fake_groq = types.SimpleNamespace(
            Groq=lambda **kwargs: types.SimpleNamespace(
                chat=types.SimpleNamespace(completions=FakeCompletions())
            )
        )

        with patch.dict(sys.modules, {"groq": fake_groq}), patch.object(
            dev_agent, "_get_api_key", return_value="test-key"
        ), patch.object(dev_agent.time, "sleep") as sleep:
            with self.assertRaises(ValueError):
                dev_agent._get_model("test-model").generate_content("prompt")

        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
