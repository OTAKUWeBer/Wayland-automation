"""
keyboard_controller.py — Keyboard automation for Wayland via ``wtype``.

Provides the ``Keyboard`` class for typing text, pressing keys, and
triggering hotkey combinations on any Wayland compositor that supports wtype.

Usage::

    from wayland_automation import Keyboard

    kb = Keyboard()
    kb.typewrite("Hello Wayland!", interval=0.05)
    kb.press("enter")
    kb.hotkey("ctrl", "s")

Requires ``wtype`` to be installed (see README for install instructions).
"""

import shutil
import subprocess
import time
from typing import Dict, List, Optional


class KeyboardError(RuntimeError):
    """Raised when keyboard automation encounters an error or missing dependency."""
    pass


class Keyboard:
    """
    Keyboard automation module for Wayland compositors using `wtype`.

    Methods:
      - typewrite(text, interval=0): Types text with optional delay between keystrokes.
      - press(key): Types (presses and releases) a single key.
      - keyDown(key): Simulates holding a key down.
      - keyUp(key): Simulates releasing a held key.
      - hotkey(*keys): Simulates a key combination (e.g. hotkey('ctrl', 's')).
    """

    # Modifier mapping to wtype modifier arguments (-M / -m)
    MODIFIER_MAP: Dict[str, str] = {
        "ctrl": "ctrl",
        "control": "ctrl",
        "alt": "alt",
        "shift": "shift",
        "super": "super",
        "win": "super",
        "windows": "super",
        "meta": "super",
    }

    # Named keys mapped to standard XKB keysym names for wtype (-k / -P / -p)
    KEY_MAP: Dict[str, str] = {
        "enter": "Return",
        "return": "Return",
        "\n": "Return",
        "backspace": "BackSpace",
        "\b": "BackSpace",
        "tab": "Tab",
        "\t": "Tab",
        "space": "space",
        " ": "space",
        "esc": "Escape",
        "escape": "Escape",
        "up": "Up",
        "down": "Down",
        "left": "Left",
        "right": "Right",
        "home": "Home",
        "end": "End",
        "pageup": "Page_Up",
        "pagedown": "Page_Down",
        "page_up": "Page_Up",
        "page_down": "Page_Down",
        "delete": "Delete",
        "del": "Delete",
        "insert": "Insert",
        "caps_lock": "Caps_Lock",
        "capslock": "Caps_Lock",
        "num_lock": "Num_Lock",
        "numlock": "Num_Lock",
        "f1": "F1",
        "f2": "F2",
        "f3": "F3",
        "f4": "F4",
        "f5": "F5",
        "f6": "F6",
        "f7": "F7",
        "f8": "F8",
        "f9": "F9",
        "f10": "F10",
        "f11": "F11",
        "f12": "F12",
    }

    def __init__(self, verify_wtype: bool = False):
        """
        Initialize Keyboard controller.
        
        Args:
            verify_wtype: If True, immediately verify wtype is installed.
        """
        if verify_wtype:
            self._ensure_wtype()

    @staticmethod
    def is_available() -> bool:
        """Check if wtype binary is available in PATH."""
        return shutil.which("wtype") is not None

    def _ensure_wtype(self) -> None:
        """Verify wtype is available, raising KeyboardError if not."""
        if not self.is_available():
            raise KeyboardError(
                "'wtype' is not installed or not in PATH. "
                "Please install it: 'sudo pacman -S wtype' (Arch) / "
                "'sudo apt install wtype' (Debian/Ubuntu) / "
                "'sudo dnf install wtype' (Fedora)."
            )

    def _run_wtype(self, args: List[str]) -> None:
        """Run a wtype command line."""
        self._ensure_wtype()
        try:
            subprocess.run(["wtype"] + args, check=True)
        except subprocess.CalledProcessError as e:
            raise KeyboardError(f"wtype execution failed with returncode {e.returncode}: {args}") from e
        except FileNotFoundError as e:
            raise KeyboardError("'wtype' binary not found.") from e

    def typewrite(self, text: str, interval: float = 0.0) -> None:
        """
        Types the given text with an optional delay between keystrokes.

        Optimized to use wtype's native '-d <delay_ms>' option where possible,
        drastically reducing process spawning overhead.

        Args:
            text: String to type.
            interval: Delay in seconds between keystrokes (default 0.0).
        """
        if not text:
            return

        text = str(text)

        # Fast path: instant typing in a single process invocation
        if interval <= 0.0:
            self._run_wtype(["--", text])
            return

        # Native wtype delay option: -d TIME (in milliseconds)
        delay_ms = max(1, int(interval * 1000))
        try:
            self._run_wtype(["-d", str(delay_ms), "--", text])
        except Exception:
            # Fallback: type character by character with Python sleep
            for char in text:
                self._run_wtype(["--", char])
                time.sleep(interval)

    def press(self, key: str) -> None:
        """
        Presses and releases a single key in one operation.

        Args:
            key: Key name (e.g. 'enter', 'esc', 'a', 'F5').
        """
        lower = key.lower()
        if lower in self.MODIFIER_MAP:
            mod = self.MODIFIER_MAP[lower]
            self._run_wtype(["-M", mod, "-m", mod])
        elif lower in self.KEY_MAP:
            self._run_wtype(["-k", self.KEY_MAP[lower]])
        else:
            self._run_wtype(["-k", key])

    def keyDown(self, key: str) -> None:
        """
        Simulates holding a key down.

        Args:
            key: Key name or modifier (e.g. 'ctrl', 'shift', 'a').
        """
        lower = key.lower()
        if lower in self.MODIFIER_MAP:
            self._run_wtype(["-M", self.MODIFIER_MAP[lower]])
        elif lower in self.KEY_MAP:
            self._run_wtype(["-P", self.KEY_MAP[lower]])
        else:
            self._run_wtype(["-P", key])

    def keyUp(self, key: str) -> None:
        """
        Simulates releasing a held key.

        Args:
            key: Key name or modifier (e.g. 'ctrl', 'shift', 'a').
        """
        lower = key.lower()
        if lower in self.MODIFIER_MAP:
            self._run_wtype(["-m", self.MODIFIER_MAP[lower]])
        elif lower in self.KEY_MAP:
            self._run_wtype(["-p", self.KEY_MAP[lower]])
        else:
            self._run_wtype(["-p", key])

    def hotkey(self, *keys: str) -> None:
        """
        Simulates a key combination in a single wtype invocation:
          1. Press modifiers down in order (-M)
          2. Tap non-modifier keys (-k)
          3. Release modifiers in reverse order (-m)

        Example:
            kb.hotkey('ctrl', 'alt', 't')
            kb.hotkey('ctrl', 's')
        """
        if not keys:
            return

        modifiers: List[str] = []
        non_modifiers: List[str] = []

        for key in keys:
            lower = str(key).lower()
            if lower in self.MODIFIER_MAP:
                modifiers.append(self.MODIFIER_MAP[lower])
            elif lower in self.KEY_MAP:
                non_modifiers.append(self.KEY_MAP[lower])
            else:
                non_modifiers.append(str(key))

        cmd: List[str] = []
        for mod in modifiers:
            cmd.extend(["-M", mod])
        for non_mod in non_modifiers:
            cmd.extend(["-k", non_mod])
        for mod in reversed(modifiers):
            cmd.extend(["-m", mod])

        try:
            self._run_wtype(cmd)
        except Exception:
            # Safety recovery: release modifiers if command errored to prevent stuck keys
            for mod in reversed(modifiers):
                try:
                    subprocess.run(["wtype", "-m", mod], timeout=0.5, capture_output=True)
                except Exception:
                    pass
            raise


if __name__ == "__main__":
    kb = Keyboard()
    print("wtype available:", kb.is_available())
