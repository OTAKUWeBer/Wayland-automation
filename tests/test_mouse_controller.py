"""
tests/test_mouse_controller.py — Tests for mouse controller protocol and helpers.
"""

import os
import struct
import unittest
from unittest.mock import MagicMock, patch
from wayland_automation.mouse_controller import (
    BUTTON_LEFT,
    BUTTON_MIDDLE,
    BUTTON_RIGHT,
    Mouse,
    encode_wayland_string,
)


class TestMouseController(unittest.TestCase):
    def test_encode_wayland_string_padding(self):
        # 4 bytes string length + content + null byte + padding to 4-byte boundary
        res = encode_wayland_string("abc")
        # "abc\0" is 4 bytes -> length is 4, padding is 0 -> total 8 bytes
        length = struct.unpack("<I", res[:4])[0]
        self.assertEqual(length, 4)
        self.assertEqual(len(res), 8)

        # "a\0" is 2 bytes -> length is 2, padding is 2 -> total 8 bytes
        res2 = encode_wayland_string("a")
        length2 = struct.unpack("<I", res2[:4])[0]
        self.assertEqual(length2, 2)
        self.assertEqual(len(res2), 8)

        # None input
        res_none = encode_wayland_string(None)
        self.assertEqual(res_none, struct.pack("<I", 0))

    def test_parse_button(self):
        self.assertEqual(Mouse._parse_button("left"), BUTTON_LEFT)
        self.assertEqual(Mouse._parse_button("L"), BUTTON_LEFT)
        self.assertEqual(Mouse._parse_button("right"), BUTTON_RIGHT)
        self.assertEqual(Mouse._parse_button("R"), BUTTON_RIGHT)
        self.assertEqual(Mouse._parse_button("middle"), BUTTON_MIDDLE)
        self.assertEqual(Mouse._parse_button("m"), BUTTON_MIDDLE)
        self.assertIsNone(Mouse._parse_button("nothing"))
        self.assertIsNone(Mouse._parse_button("none"))
        self.assertEqual(Mouse._parse_button(0x110), 0x110)

        with self.assertRaises(ValueError):
            Mouse._parse_button("invalid_button_name")

    @patch.dict(os.environ, {"XDG_RUNTIME_DIR": "/custom/runtime", "WAYLAND_DISPLAY": "wayland-1"})
    def test_get_socket_path_custom_runtime(self):
        # Create a mock Mouse instance without __init__
        ms = object.__new__(Mouse)
        path = ms.get_socket_path()
        self.assertEqual(path, os.path.join("/custom/runtime", "wayland-1"))


if __name__ == "__main__":
    unittest.main()

