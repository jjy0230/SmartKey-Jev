"""
Unit Tests for Two-Tier Context Bucketing Engine.
"""

import unittest
from smartkey_jev.core.models import SelectionContext
from smartkey_jev.actions.registry import DEFAULT_REGISTRY
from smartkey_jev.intent.two_tier_rule import TwoTierRulePredictor, ProcessArchetype


class TestTwoTierRulePredictor(unittest.TestCase):
    def setUp(self):
        self.predictor = TwoTierRulePredictor()
        self.candidates = DEFAULT_REGISTRY.list_all()

    def test_process_archetype_mapping(self):
        self.assertEqual(self.predictor.get_process_archetype("code.exe"), ProcessArchetype.IDE)
        self.assertEqual(self.predictor.get_process_archetype("chrome.exe"), ProcessArchetype.BROWSER)
        self.assertEqual(self.predictor.get_process_archetype("wechat.exe"), ProcessArchetype.CHAT)
        self.assertEqual(self.predictor.get_process_archetype("windowsterminal.exe"), ProcessArchetype.TERMINAL)
        self.assertEqual(self.predictor.get_process_archetype("random_app.exe"), ProcessArchetype.GENERAL)

    def test_url_detection(self):
        ctx = SelectionContext(
            text="https://github.com/jjy0230/SmartKey-Jev",
            raw_text="https://github.com/jjy0230/SmartKey-Jev",
            process_name="notepad.exe",
        )
        preds = self.predictor.predict(ctx, self.candidates, top_k=3)
        self.assertTrue(len(preds) > 0)
        self.assertEqual(preds[0].macro.id, "open_url")
        self.assertGreater(preds[0].confidence, 0.90)

    def test_json_formatting_detection(self):
        ctx = SelectionContext(
            text='{"name": "jev", "active": true, "ports": [80, 443]}',
            raw_text='{"name": "jev", "active": true, "ports": [80, 443]}',
            process_name="code.exe",
        )
        preds = self.predictor.predict(ctx, self.candidates, top_k=3)
        self.assertEqual(preds[0].macro.id, "format_json")

    def test_code_stacktrace_detection(self):
        ctx = SelectionContext(
            text="Traceback (most recent call last):\n  File 'test.py', line 12, in <module>\nTypeError: unsupported operand",
            raw_text="...",
            process_name="code.exe",
        )
        preds = self.predictor.predict(ctx, self.candidates, top_k=3)
        self.assertEqual(preds[0].macro.id, "fix_code")

    def test_schedule_todo_detection(self):
        ctx = SelectionContext(
            text="明天下午 14:00 参加系统架构评审会议",
            raw_text="...",
            process_name="wechat.exe",
        )
        preds = self.predictor.predict(ctx, self.candidates, top_k=3)
        self.assertEqual(preds[0].macro.id, "create_todo")

    def test_single_word_dictionary(self):
        ctx = SelectionContext(
            text="serendipity",
            raw_text="serendipity",
            process_name="chrome.exe",
        )
        preds = self.predictor.predict(ctx, self.candidates, top_k=3)
        self.assertEqual(preds[0].macro.id, "dictionary")


if __name__ == "__main__":
    unittest.main()
