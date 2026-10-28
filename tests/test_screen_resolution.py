"""
tests/test_screen_resolution.py — Tests for screen resolution detection and parsing.
"""

import unittest
from unittest.mock import MagicMock, patch
from wayland_automation.utils.screen_resolution import (
    DEFAULT_RESOLUTION,
    get_resolution,
)


class TestScreenResolution(unittest.TestCase):
    @patch("shutil.which")
    @patch("subprocess.run")
    def test_wayland_info_parsing(self, mock_run, mock_which):
        mock_which.side_effect = lambda cmd: "/usr/bin/wayland-info" if cmd == "wayland-info" else None
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="interface: 'wl_output'\n  mode: width: 2560 px, height: 1440 px, refresh: 144 Hz\n",
        )
        res = get_resolution()
        self.assertEqual(res, (2560, 1440))

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_hyprctl_monitors_parsing(self, mock_run, mock_which):
        def fake_which(cmd):
            if cmd == "hyprctl":
                return "/usr/bin/hyprctl"
            return None

        mock_which.side_effect = fake_which
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Monitor DP-1 (ID 0):\n\t3840x2160@120.00Hz at 0x0\n",
        )
        res = get_resolution()
        self.assertEqual(res, (3840, 2160))

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_swaymsg_parsing(self, mock_run, mock_which):
        def fake_which(cmd):
            if cmd == "swaymsg":
                return "/usr/bin/swaymsg"
            return None

        mock_which.side_effect = fake_which
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"name": "eDP-1", "rect": {"x": 0, "y": 0, "width": 1920, "height": 1200}}]',
        )
        res = get_resolution()
        self.assertEqual(res, (1920, 1200))

    @patch("shutil.which")
    def test_default_fallback(self, mock_which):
        mock_which.return_value = None
        res = get_resolution()
        self.assertEqual(res, DEFAULT_RESOLUTION)
        self.assertIsInstance(res[0], int)
        self.assertIsInstance(res[1], int)


if __name__ == "__main__":
    unittest.main()

