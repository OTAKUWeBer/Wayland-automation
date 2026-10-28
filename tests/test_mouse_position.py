"""
tests/test_mouse_position.py — Tests for mouse position backends.
"""

import unittest
from unittest.mock import MagicMock, patch
from wayland_automation.mouse_position import (
    NUM_RE,
    HyprlandBackend,
    KWinBackend,
    WlFindCursorBackend,
    XdotoolBackend,
    _find_qdbus,
)


class TestMousePosition(unittest.TestCase):
    def test_regex_number_extraction(self):
        txt = "Cursor pos: 512, 1024"
        nums = NUM_RE.findall(txt)
        self.assertEqual(nums, ["512", "1024"])

        txt_neg = "Coordinates -100 -250"
        nums_neg = NUM_RE.findall(txt_neg)
        self.assertEqual(nums_neg, ["-100", "-250"])

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_hyprland_read_once(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/hyprctl"
        mock_run.return_value = MagicMock(returncode=0, stdout="800, 600\n", stderr="")
        pos = HyprlandBackend.read_once()
        self.assertEqual(pos, (800, 600))

    @patch("shutil.which")
    def test_find_qdbus_variants(self, mock_which):
        def fake_which(cmd):
            if cmd == "qdbus6":
                return "/usr/bin/qdbus6"
            return None

        mock_which.side_effect = fake_which
        path = _find_qdbus()
        self.assertEqual(path, "/usr/bin/qdbus6")

    @patch("shutil.which")
    def test_backend_availability_when_missing(self, mock_which):
        mock_which.return_value = None
        self.assertFalse(HyprlandBackend.available())
        self.assertFalse(WlFindCursorBackend.available())
        self.assertFalse(KWinBackend.available())


if __name__ == "__main__":
    unittest.main()

