#!/usr/bin/env python3
"""
mouse_position.py — Multi-backend cursor position tracker for Wayland.

Automatically selects the best available backend for your compositor:

  1. Hyprland   — via ``hyprctl cursorpos``
  2. wlroots    — via ``wl-find-cursor`` (Sway, River, etc.)
  3. KDE Plasma — via KWin scripting and D-Bus (net.mousePosition)
  4. XWayland   — via ``xdotool`` (if DISPLAY is set)
  5. evdev      — relative-motion integration fallback (needs /dev/input access)

Usage::

    from wayland_automation import mouse_position_generator, get_position

    # Single snapshot:
    x, y = get_position()

    # Stream:
    for x, y in mouse_position_generator(interval=0.1):
        print(f"Cursor at: ({x}, {y})")

CLI::

    python -m wayland_automation.mouse_position          # default 0.2s interval
    python -m wayland_automation.mouse_position 0.5      # custom interval

Dependencies:
  - Python: ``evdev`` (for evdev fallback), ``dbus-next`` (for KDE Plasma)
  - System: ``hyprctl`` | ``wl-find-cursor`` | ``qdbus`` | ``xdotool`` (auto-detected)
"""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Generator, Optional, Tuple

INTERVAL = 0.2
NUM_RE = re.compile(r"-?\d+")


# -------------------- Hyprland backend --------------------
class HyprlandBackend:
    name = "hyprctl"

    @staticmethod
    def available() -> bool:
        return shutil.which("hyprctl") is not None

    @staticmethod
    def read_once() -> Optional[Tuple[int, int]]:
        try:
            p = subprocess.run(
                ["hyprctl", "cursorpos"],
                capture_output=True,
                text=True,
                timeout=0.5,
            )
            txt = (p.stdout or "") + " " + (p.stderr or "")
            nums = NUM_RE.findall(txt)
            if len(nums) >= 2:
                return int(nums[0]), int(nums[1])
        except Exception:
            return None
        return None


# -------------------- wl-find-cursor backend (Sway / wlroots) --------------------
class WlFindCursorBackend:
    name = "wl-find-cursor"

    @staticmethod
    def available() -> bool:
        return shutil.which("wl-find-cursor") is not None

    def __init__(self):
        self.proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._last: Optional[Tuple[int, int]] = None
        self._running = False
        self._thr: Optional[threading.Thread] = None

    def start(self) -> bool:
        cmd = shutil.which("wl-find-cursor")
        if not cmd:
            return False

        try:
            self.proc = subprocess.Popen(
                [cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self._running = True
            self._thr = threading.Thread(target=self._reader, daemon=True)
            self._thr.start()
            return True
        except Exception:
            return False

    def _reader(self) -> None:
        if not self.proc or not self.proc.stdout:
            return
        try:
            for line in self.proc.stdout:
                if not self._running:
                    break
                nums = NUM_RE.findall(line)
                if len(nums) >= 2:
                    with self._lock:
                        self._last = (int(nums[0]), int(nums[1]))
        except Exception:
            pass

    def get_position(self) -> Optional[Tuple[int, int]]:
        with self._lock:
            return self._last

    def stop(self) -> None:
        self._running = False
        try:
            if self.proc:
                self.proc.terminate()
                self.proc.wait(timeout=0.5)
        except Exception:
            pass


# -------------------- KDE Plasma / KWin backend --------------------
def _find_qdbus() -> Optional[str]:
    """Find the qdbus binary (handles Qt5 and Qt6 naming across distributions)."""
    for cmd in ("qdbus", "qdbus6", "qdbus-qt6", "qdbus-qt5"):
        path = shutil.which(cmd)
        if path:
            return path
    return None


class KWinBackend:
    name = "kwin"

    @staticmethod
    def available() -> bool:
        """Check if qdbus, dbus-next, and KWin's scripting interface are available."""
        qdbus_cmd = _find_qdbus()
        if not qdbus_cmd:
            return False
        try:
            import dbus_next  # noqa: F401
        except ImportError:
            return False

        try:
            res = subprocess.run(
                [qdbus_cmd, "org.kde.KWin", "/Scripting"],
                capture_output=True,
                text=True,
                timeout=1.0,
            )
            return res.returncode == 0
        except Exception:
            return False

    def __init__(self):
        self.mouse_position: Optional[Tuple[int, int]] = None
        self._lock = threading.Lock()
        self._running = False
        self._bus = None
        self._loop = None
        self._thread: Optional[threading.Thread] = None
        self._ready_event = threading.Event()
        self._temp_js_path: Optional[str] = None
        self._script_id: Optional[str] = None

    def _set_mouse_position(self, pos) -> None:
        if pos and len(pos) >= 2:
            with self._lock:
                self.mouse_position = (int(pos[0]), int(pos[1]))

    def _get_script_path(self) -> Optional[str]:
        pkg_script = Path(__file__).resolve().parent / "kwin_cursor_pos.js"
        if pkg_script.exists():
            return str(pkg_script)

        import tempfile

        js_code = (
            "var lastCallTime = 0;\n"
            "function sendPos() {\n"
            "  callDBus(\n"
            "    'net.mousePosition',\n"
            "    '/commands',\n"
            "    'net.mousePosition',\n"
            "    'ReceiveMousePosition',\n"
            "    '[' + workspace.cursorPos.x + ', ' + workspace.cursorPos.y + ']'\n"
            "  );\n"
            "}\n"
            "sendPos();\n"
            "workspace.cursorPosChanged.connect(function() {\n"
            "  var currentTime = Date.now();\n"
            "  if (currentTime - lastCallTime > 16) {\n"
            "    sendPos();\n"
            "    lastCallTime = currentTime;\n"
            "  }\n"
            "});\n"
        )
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
                f.write(js_code)
                self._temp_js_path = f.name
                return self._temp_js_path
        except Exception:
            return None

    def _run_event_loop(self) -> None:
        import asyncio
        from dbus_next.aio import MessageBus
        from dbus_next.service import ServiceInterface, method

        class DbusInterface(ServiceInterface):
            def __init__(self, callback):
                super().__init__("net.mousePosition")
                self.callback = callback

            @method()
            def ReceiveMousePosition(self, val: "s"):  # type: ignore
                try:
                    pos = json.loads(val)
                    self.callback(pos)
                except Exception:
                    pass

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def _serve():
            try:
                self._bus = await MessageBus().connect()
                interface = DbusInterface(self._set_mouse_position)
                self._bus.export("/commands", interface)
                await self._bus.request_name("net.mousePosition")
                self._ready_event.set()
                await self._bus.wait_for_disconnect()
            except Exception:
                self._ready_event.set()

        try:
            self._loop.run_until_complete(_serve())
        except Exception:
            pass
        finally:
            self._ready_event.set()

    def start(self) -> bool:
        qdbus_cmd = _find_qdbus()
        if not qdbus_cmd:
            return False

        self._running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

        if not self._ready_event.wait(timeout=3.0) or not self._bus:
            self.stop()
            return False

        # Unload any previously loaded instance of our script
        subprocess.call(
            [qdbus_cmd, "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.unloadScript", "kwin_cursor_pos"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1.0,
        )

        script_path = self._get_script_path()
        if not script_path or not os.path.exists(script_path):
            self.stop()
            return False

        result = subprocess.run(
            [qdbus_cmd, "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.loadScript", str(script_path), "kwin_cursor_pos"],
            capture_output=True,
            text=True,
            timeout=2.0,
        )
        script_id = result.stdout.strip()
        if not script_id or script_id == "-1" or "error" in script_id.lower():
            self.stop()
            return False

        self._script_id = script_id

        script_obj = script_id if script_id.startswith("/") else f"/Scripting/Script{script_id}"
        subprocess.call(
            [qdbus_cmd, "org.kde.KWin", script_obj, "org.kde.kwin.Script.run"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1.0,
        )
        return True

    def get_position(self) -> Optional[Tuple[int, int]]:
        with self._lock:
            return self.mouse_position

    def stop(self) -> None:
        self._running = False
        qdbus_cmd = _find_qdbus()
        if qdbus_cmd:
            try:
                subprocess.call(
                    [qdbus_cmd, "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.unloadScript", "kwin_cursor_pos"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=1.0,
                )
            except Exception:
                pass

        if self._bus:
            try:
                self._bus.disconnect()
            except Exception:
                pass

        if self._loop and self._loop.is_running():
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass

        if self._temp_js_path and os.path.exists(self._temp_js_path):
            try:
                os.remove(self._temp_js_path)
            except Exception:
                pass
            self._temp_js_path = None


# -------------------- X11 / XWayland backend (xdotool) --------------------
class XdotoolBackend:
    name = "xdotool"

    @staticmethod
    def available() -> bool:
        return ("DISPLAY" in os.environ) and (shutil.which("xdotool") is not None)

    @staticmethod
    def read_once() -> Optional[Tuple[int, int]]:
        try:
            p = subprocess.run(
                ["xdotool", "getmouselocation", "--shell"],
                capture_output=True,
                text=True,
                timeout=0.5,
            )
            data = {}
            for line in (p.stdout or "").splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip()
            if "X" in data and "Y" in data:
                return int(data["X"]), int(data["Y"])
        except Exception:
            return None
        return None


# -------------------- evdev fallback (relative -> absolute integration) --------------------
class EvdevFallback:
    name = "evdev"

    def __init__(self, seed: Tuple[Optional[int], Optional[int]] = (None, None)):
        try:
            from evdev import list_devices, InputDevice, ecodes
            self.evdev = True
            self.list_devices = list_devices
            self.InputDevice = InputDevice
            self.ecodes = ecodes
        except Exception:
            self.evdev = False

        self.device_path: Optional[str] = None
        self.dev = None
        self._running = False
        self._lock = threading.Lock()
        self.width = 1920
        self.height = 1080
        self.x: Optional[float] = seed[0]
        self.y: Optional[float] = seed[1]

    def available(self) -> bool:
        return self.evdev

    def find_device(self) -> Optional[str]:
        if not self.evdev:
            return None
        for path in self.list_devices():
            try:
                dev = self.InputDevice(path)
            except Exception:
                continue
            try:
                try:
                    caps = dev.capabilities(skip_missing=True)
                except TypeError:
                    caps = dev.capabilities()
            except Exception:
                try:
                    dev.close()
                except Exception:
                    pass
                continue

            rels = caps.get(self.ecodes.EV_REL)
            if rels:
                rels_list = list(rels.keys()) if isinstance(rels, dict) else list(rels)
                if self.ecodes.REL_X in rels_list and self.ecodes.REL_Y in rels_list:
                    try:
                        dev.close()
                    except Exception:
                        pass
                    return path
            try:
                dev.close()
            except Exception:
                pass
        return None

    def start(self) -> bool:
        if not self.evdev:
            return False
        self.device_path = self.find_device()
        if not self.device_path:
            return False

        try:
            self.dev = self.InputDevice(self.device_path)
        except Exception:
            return False

        # Get screen resolution
        try:
            from wayland_automation.utils.screen_resolution import get_resolution
            w, h = get_resolution()
            self.width, self.height = int(w), int(h)
        except Exception:
            self.width, self.height = 1920, 1080

        if self.x is None or self.y is None:
            self.x = self.width // 2
            self.y = self.height // 2

        self._running = True
        self._thr = threading.Thread(target=self._reader, daemon=True)
        self._thr.start()
        return True

    def _reader(self) -> None:
        try:
            for ev in self.dev.read_loop():
                if not self._running:
                    break
                if ev.type == self.ecodes.EV_REL:
                    with self._lock:
                        if ev.code == self.ecodes.REL_X:
                            self.x += ev.value
                        elif ev.code == self.ecodes.REL_Y:
                            self.y += ev.value
                        # Clamp to screen boundary
                        if self.x < 0:
                            self.x = 0
                        if self.y < 0:
                            self.y = 0
                        if self.x >= self.width:
                            self.x = self.width - 1
                        if self.y >= self.height:
                            self.y = self.height - 1
        except Exception:
            pass

    def get_position(self) -> Tuple[int, int]:
        with self._lock:
            return int(self.x), int(self.y)

    def stop(self) -> None:
        self._running = False
        try:
            if self.dev:
                self.dev.close()
        except Exception:
            pass


# -------------------- orchestrator --------------------
def pick_backend_and_start():
    """
    Detect the active compositor and start the best matching cursor tracking backend.

    Returns:
        tuple: (backend_name, getter_fn, controller_instance)
    """
    # 1) Hyprland
    if HyprlandBackend.available():
        pos = HyprlandBackend.read_once()
        if pos:
            return ("hyprctl", HyprlandBackend.read_once, None)

    # 2) wl-find-cursor (Sway / wlroots)
    if WlFindCursorBackend.available():
        w = WlFindCursorBackend()
        if w.start():
            return ("wl-find-cursor", w.get_position, w)

    # 3) KDE Plasma (KWin scripting + D-Bus)
    if KWinBackend.available():
        k = KWinBackend()
        if k.start():
            return ("kwin", k.get_position, k)

    # 4) xdotool if DISPLAY present (XWayland)
    if XdotoolBackend.available():
        pos = XdotoolBackend.read_once()
        if pos:
            return ("xdotool", XdotoolBackend.read_once, None)

    # 5) evdev fallback (seed from previous attempts if any)
    seed = None
    if HyprlandBackend.available():
        seed = HyprlandBackend.read_once()
    if seed is None and XdotoolBackend.available():
        seed = XdotoolBackend.read_once()

    ev = EvdevFallback(seed=seed or (None, None))
    if ev.available() and ev.start():
        return ("evdev", ev.get_position, ev)

    return (None, None, None)


def mouse_position_generator(
    interval: Optional[float] = None, print_output: bool = False
) -> Generator[Tuple[int, int], None, None]:
    """
    Generator that yields (x, y) mouse positions continuously.

    Args:
        interval: Polling interval in seconds (default: 0.2).
        print_output: If True, prints current position to stdout.

    Yields:
        tuple[int, int]: (x, y) coordinates.
    """
    if interval is None:
        interval = INTERVAL

    backend_name, getter, controller = pick_backend_and_start()
    if backend_name is None:
        raise RuntimeError(
            "No mouse tracking backend available: install hyprctl (Hyprland), "
            "wl-find-cursor (wlroots), dbus-next with qdbus (KDE Plasma), or xdotool, "
            "or install python-evdev and grant access to /dev/input/event*."
        )

    if print_output:
        print(f"Using backend: {backend_name}")

    last = None
    try:
        while True:
            pos = getter()
            if pos:
                if print_output and pos != last:
                    print(f"Cursor: x={pos[0]}  y={pos[1]}    ", end="\r", flush=True)
                    last = pos
                yield pos
            else:
                if print_output and last is None:
                    print("Waiting for cursor data...    ", end="\r", flush=True)
                if last:
                    yield last
            time.sleep(interval)
    except GeneratorExit:
        pass
    except KeyboardInterrupt:
        return
    finally:
        if controller:
            try:
                controller.stop()
            except Exception:
                pass


def get_position() -> Optional[Tuple[int, int]]:
    """
    Get a single snapshot of the current cursor position (x, y).

    Returns:
        tuple[int, int] or None: Current (x, y) coordinates.
    """
    for pos in mouse_position_generator(interval=0.01):
        return pos
    return None


def main() -> None:
    """CLI entry point for mouse position monitoring."""
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else INTERVAL
    print("Starting compositor-aware cursor watcher. (Ctrl+C to stop)")

    try:
        for _ in mouse_position_generator(interval=interval, print_output=True):
            pass
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
