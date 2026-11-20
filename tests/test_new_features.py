"""
Unit Tests for New Functional Features:
- Instant Math Calculation (calculate)
- Variable Naming Case Conversion (convert_case)
- Local Path Opener (open_path)
"""

import unittest
from smartkey_jev.core.models import SelectionContext
from smartkey_jev.actions.registry import DEFAULT_REGISTRY
from smartkey_jev.actions.executor import ActionExecutor
from smartkey_jev.intent.two_tier_rule import TwoTierRulePredictor


class TestNewFeatures(unittest.TestCase):
    def setUp(self):
        self.predictor = TwoTierRulePredictor()
        self.candidates = DEFAULT_REGISTRY.list_all()
        self.executor = ActionExecutor()

    def test_calculate_intent_and_execution(self):
        # 1. Intent scoring
        ctx = SelectionContext(
            text="1024 * 768 / 2",
            raw_text="1024 * 768 / 2",
            process_name="code.exe",
        )
        preds = self.predictor.predict(ctx, self.candidates, top_k=3)
        self.assertEqual(preds[0].macro.id, "calculate")
        self.assertGreater(preds[0].confidence, 0.90)

        # 2. Execution
        res = self.executor.execute(preds[0].macro, ctx)
        self.assertEqual(res["status"], "success")

    def test_convert_case_intent_and_execution(self):
        # 1. Intent scoring
        ctx = SelectionContext(
            text="user_profile_data",
            raw_text="user_profile_data",
            process_name="code.exe",
        )
        preds = self.predictor.predict(ctx, self.candidates, top_k=3)
        self.assertEqual(preds[0].macro.id, "convert_case")

        # 2. Execution (snake_case -> camelCase)
        res = self.executor.execute(preds[0].macro, ctx)
        self.assertEqual(res["status"], "success")

    def test_open_path_intent(self):
        ctx = SelectionContext(
            text="C:\\Windows\\System32\\notepad.exe",
            raw_text="C:\\Windows\\System32\\notepad.exe",
            process_name="windowsterminal.exe",
        )
        preds = self.predictor.predict(ctx, self.candidates, top_k=3)
        self.assertEqual(preds[0].macro.id, "open_path")


if __name__ == "__main__":
    unittest.main()
