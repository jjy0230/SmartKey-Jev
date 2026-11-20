"""
Unit Tests for Custom User Macros Loader.
"""

import unittest
from smartkey_jev.actions.registry import MacroRegistry
from smartkey_jev.actions.custom_loader import load_custom_macros


class TestCustomMacrosLoader(unittest.TestCase):
    def test_load_custom_macros(self):
        reg = MacroRegistry()
        initial_count = len(reg.list_all())

        loaded = load_custom_macros(reg)
        self.assertTrue(len(loaded) > 0)
        self.assertGreater(len(reg.list_all()), initial_count)

        # Check git commit macro exists
        git_macro = reg.get("git_commit_gen")
        self.assertIsNotNone(git_macro)
        self.assertEqual(git_macro.title, "生成 Git Commit")


if __name__ == "__main__":
    unittest.main()
