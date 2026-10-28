"""
tests/test_package.py — Tests for package metadata and public API.
"""

import unittest
import wayland_automation as wa


class TestPackage(unittest.TestCase):
    def test_version_present(self):
        self.assertTrue(hasattr(wa, "__version__"))
        parts = wa.__version__.split(".")
        self.assertGreaterEqual(len(parts), 2)

    def test_all_exports(self):
        for name in wa.__all__:
            self.assertTrue(
                hasattr(wa, name), f"Export '{name}' in __all__ not found in package"
            )

    def test_convenience_functions_exist(self):
        expected = [
            "click",
            "swipe",
            "auto_click",
            "typewrite",
            "press",
            "keyDown",
            "keyUp",
            "hotkey",
            "get_position",
            "position",
            "mouse_position_generator",
            "cleanup",
        ]
        for func in expected:
            self.assertTrue(callable(getattr(wa, func)), f"{func} should be callable")


if __name__ == "__main__":
    unittest.main()

