"""
tests/test_keyboard_controller.py — Tests for keyboard automation and command building.
"""

import unittest
from unittest.mock import MagicMock, call, patch
from wayland_automation.keyboard_controller import Keyboard, KeyboardError


class TestKeyboardController(unittest.TestCase):
    def setUp(self):
        self.kb = Keyboard()

    @patch("shutil.which")
    def test_ensure_wtype_raises_if_missing(self, mock_which):
        mock_which.return_value = None
        with self.assertRaises(KeyboardError):
            self.kb._ensure_wtype()

    @patch.object(Keyboard, "is_available", return_value=True)
    @patch("subprocess.run")
    def test_typewrite_instant(self, mock_run, mock_avail):
        self.kb.typewrite("Hello Wayland!", interval=0)
        mock_run.assert_called_once_with(["wtype", "--", "Hello Wayland!"], check=True)

    @patch.object(Keyboard, "is_available", return_value=True)
    @patch("subprocess.run")
    def test_typewrite_with_interval(self, mock_run, mock_avail):
        self.kb.typewrite("test", interval=0.05)
        # 50ms delay
        mock_run.assert_called_once_with(["wtype", "-d", "50", "--", "test"], check=True)

    @patch.object(Keyboard, "is_available", return_value=True)
    @patch("subprocess.run")
    def test_press_named_key(self, mock_run, mock_avail):
        self.kb.press("enter")
        mock_run.assert_called_once_with(["wtype", "-k", "Return"], check=True)

    @patch.object(Keyboard, "is_available", return_value=True)
    @patch("subprocess.run")
    def test_press_modifier(self, mock_run, mock_avail):
        self.kb.press("ctrl")
        mock_run.assert_called_once_with(["wtype", "-M", "ctrl", "-m", "ctrl"], check=True)

    @patch.object(Keyboard, "is_available", return_value=True)
    @patch("subprocess.run")
    def test_key_down_and_up(self, mock_run, mock_avail):
        self.kb.keyDown("shift")
        mock_run.assert_called_with(["wtype", "-M", "shift"], check=True)

        self.kb.keyUp("shift")
        mock_run.assert_called_with(["wtype", "-m", "shift"], check=True)

        self.kb.keyDown("a")
        mock_run.assert_called_with(["wtype", "-P", "a"], check=True)

        self.kb.keyUp("a")
        mock_run.assert_called_with(["wtype", "-p", "a"], check=True)

    @patch.object(Keyboard, "is_available", return_value=True)
    @patch("subprocess.run")
    def test_hotkey_ordering(self, mock_run, mock_avail):
        self.kb.hotkey("ctrl", "alt", "t")
        expected_cmd = [
            "wtype",
            "-M",
            "ctrl",
            "-M",
            "alt",
            "-k",
            "t",
            "-m",
            "alt",
            "-m",
            "ctrl",
        ]
        mock_run.assert_called_once_with(expected_cmd, check=True)


if __name__ == "__main__":
    unittest.main()

