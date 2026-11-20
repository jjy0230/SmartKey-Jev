"""
Unit Tests for Smart Tri-State Action Delivery.
"""

import unittest
from smartkey_jev.core.models import SelectionContext, MacroDeliveryMode
from smartkey_jev.actions.registry import DEFAULT_REGISTRY
from smartkey_jev.actions.executor import ActionExecutor


class TestActionDeliveryModes(unittest.TestCase):
    def setUp(self):
        self.drawer_results = []
        self.executor = ActionExecutor(
            drawer_callback=lambda title, icon, content: self.drawer_results.append((title, icon, content))
        )

    def test_category_a_json_format_logic(self):
        macro = DEFAULT_REGISTRY.get("format_json")
        self.assertIsNotNone(macro)
        self.assertEqual(macro.delivery_mode, MacroDeliveryMode.IN_PLACE_REPLACE)

        ctx = SelectionContext(
            text='{"a":1,"b":2}',
            raw_text='{"a":1,"b":2}',
            process_name="code.exe",
        )
        res = self.executor.execute(macro, ctx)
        self.assertEqual(res["status"], "success")
        # In non-interactive test environment without active caret, it safely falls back to drawer
        self.assertIn(res["mode"], ("in_place_replace", "fallback_to_drawer"))

    def test_category_b_drawer_translate(self):
        macro = DEFAULT_REGISTRY.get("translate")
        self.assertIsNotNone(macro)
        self.assertEqual(macro.delivery_mode, MacroDeliveryMode.DRAWER_PANEL)

        ctx = SelectionContext(
            text="latency",
            raw_text="latency",
            process_name="chrome.exe",
        )
        res = self.executor.execute(macro, ctx)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["mode"], "drawer_panel")
        self.assertTrue(len(self.drawer_results) > 0)
        self.assertIn("时延", self.drawer_results[0][2])

    def test_category_c_external_open_url(self):
        macro = DEFAULT_REGISTRY.get("open_url")
        self.assertIsNotNone(macro)
        self.assertEqual(macro.delivery_mode, MacroDeliveryMode.EXTERNAL_DISPATCH)


if __name__ == "__main__":
    unittest.main()
