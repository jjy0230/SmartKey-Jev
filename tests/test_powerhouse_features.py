"""
Unit Tests for Killer Productivity Features:
- QR Code Generator (make_qrcode)
- Color Code Converter (color_converter)
- Natural Language Command Generator (nlp_to_cmd)
- Sticky Pin Scratchpad (pin_scratchpad)
"""

import unittest
from smartkey_jev.core.models import SelectionContext
from smartkey_jev.actions.registry import DEFAULT_REGISTRY
from smartkey_jev.actions.executor import ActionExecutor
from smartkey_jev.intent.two_tier_rule import TwoTierRulePredictor


class TestPowerhouseFeatures(unittest.TestCase):
    def setUp(self):
        self.predictor = TwoTierRulePredictor()
        self.candidates = DEFAULT_REGISTRY.list_all()
        self.drawer_output = []
        self.executor = ActionExecutor(
            drawer_callback=lambda title, icon, content: self.drawer_output.append((title, icon, content))
        )

    def test_color_converter_intent_and_execution(self):
        # 1. HEX intent
        ctx = SelectionContext(text="#4A90E2", raw_text="#4A90E2", process_name="code.exe")
        preds = self.predictor.predict(ctx, self.candidates, top_k=3)
        self.assertEqual(preds[0].macro.id, "color_converter")
        self.assertGreater(preds[0].confidence, 0.90)

        # 2. Execution (#4A90E2 -> rgb(74, 144, 226))
        res = self.executor.execute(preds[0].macro, ctx)
        self.assertEqual(res["status"], "success")

    def test_nlp_to_cmd_intent_and_execution(self):
        # 1. Intent
        ctx = SelectionContext(text="回退上一个commit", raw_text="回退上一个commit", process_name="windowsterminal.exe")
        preds = self.predictor.predict(ctx, self.candidates, top_k=3)
        self.assertEqual(preds[0].macro.id, "nlp_to_cmd")

        # 2. Execution
        res = self.executor.execute(preds[0].macro, ctx)
        self.assertEqual(res["status"], "success")

    def test_make_qrcode_execution(self):
        macro = DEFAULT_REGISTRY.get("make_qrcode")
        self.assertIsNotNone(macro)
        ctx = SelectionContext(
            text="https://github.com/jjy0230/SmartKey-Jev",
            raw_text="https://github.com/jjy0230/SmartKey-Jev",
            process_name="chrome.exe",
        )
        res = self.executor.execute(macro, ctx)
        self.assertEqual(res["status"], "success")
        self.assertTrue(len(self.drawer_output) > 0)
        self.assertIn("██", self.drawer_output[0][2])

    def test_pin_scratchpad_execution(self):
        macro = DEFAULT_REGISTRY.get("pin_scratchpad")
        self.assertIsNotNone(macro)
        ctx = SelectionContext(text="临时数据库密码: P@ssw0rd99!", raw_text="临时数据库密码: P@ssw0rd99!", process_name="notepad.exe")
        res = self.executor.execute(macro, ctx)
        self.assertEqual(res["status"], "success")


if __name__ == "__main__":
    unittest.main()
