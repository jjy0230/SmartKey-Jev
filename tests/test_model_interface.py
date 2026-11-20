"""
Unit Tests for Model Interface, Prompt Formatting, and Mock Client.
"""

import unittest
from smartkey_jev.core.models import SelectionContext
from smartkey_jev.actions.registry import DEFAULT_REGISTRY
from smartkey_jev.intent.model_interface import (
    ModelInferenceRequest,
    ModelInferenceResponse,
    ModelCandidateInput,
)
from smartkey_jev.intent.model_stub import MockJevModelClient, JevModelPredictor


class TestModelInterface(unittest.TestCase):
    def test_prompt_formatting(self):
        req = ModelInferenceRequest(
            process_name="code.exe",
            window_title="main.py",
            selected_text="def foo(): pass",
            candidates=[
                ModelCandidateInput(
                    id="explain_code",
                    title="代码解释",
                    category="code",
                    description="解释代码逻辑",
                )
            ],
        )
        prompt = req.format_prompt()
        self.assertIn("SmartKey-Jev", prompt)
        self.assertIn("def foo(): pass", prompt)
        self.assertIn("explain_code", prompt)

    def test_response_json_parsing(self):
        sample_json = """
        ```json
        {
            "predictions": [
                {"id": "fix_code", "probability": 0.88, "reason": "Syntax error"}
            ]
        }
        ```
        """
        resp = ModelInferenceResponse.from_json(sample_json, latency_ms=12.5)
        self.assertIsNone(resp.error)
        self.assertEqual(len(resp.predictions), 1)
        self.assertEqual(resp.predictions[0].id, "fix_code")
        self.assertEqual(resp.predictions[0].probability, 0.88)

    def test_mock_jev_predictor(self):
        predictor = JevModelPredictor(client=MockJevModelClient())
        candidates = DEFAULT_REGISTRY.list_all()
        ctx = SelectionContext(
            text="https://github.com/jjy0230",
            raw_text="https://github.com/jjy0230",
            process_name="chrome.exe",
        )
        preds = predictor.predict(ctx, candidates, top_k=3)
        self.assertEqual(len(preds), 3)
        self.assertEqual(preds[0].macro.id, "open_url")


if __name__ == "__main__":
    unittest.main()
