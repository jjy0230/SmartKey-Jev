"""
Unit Tests for Plugin System (Timestamp, Base64, PluginManager).
"""

import unittest
from smartkey_jev.core.models import SelectionContext
from smartkey_jev.plugins.builtin_timestamp import TimestampPlugin
from smartkey_jev.plugins.builtin_base64 import Base64Plugin
from smartkey_jev.plugins.plugin_manager import PluginManager


class TestPlugins(unittest.TestCase):
    def test_timestamp_plugin(self):
        plugin = TimestampPlugin()
        ctx = SelectionContext(text="1700000000", raw_text="1700000000", process_name="code.exe")
        score = plugin.match(ctx)
        self.assertGreater(score, 0.9)

        res = plugin.execute(ctx)
        self.assertEqual(res["status"], "success")
        self.assertIn("2023", res["result"])

    def test_base64_plugin(self):
        plugin = Base64Plugin()
        # "Hello, SmartKey!" in base64: SGVsbG8sIFNtYXJ0S2V5IQ==
        ctx = SelectionContext(text="SGVsbG8sIFNtYXJ0S2V5IQ==", raw_text="SGVsbG8sIFNtYXJ0S2V5IQ==", process_name="chrome.exe")
        score = plugin.match(ctx)
        self.assertGreater(score, 0.9)

        res = plugin.execute(ctx)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["result"], "Hello, SmartKey!")

    def test_plugin_manager(self):
        pm = PluginManager()
        plugins = pm.list_plugins()
        self.assertGreaterEqual(len(plugins), 2)


if __name__ == "__main__":
    unittest.main()
