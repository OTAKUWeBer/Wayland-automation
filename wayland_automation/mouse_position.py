#!/usr/bin/env python3
"""
wayland_cursor_watch.py

Multi-backend compositor-aware cursor watcher for Wayland systems.

Backends tried (in order):
 - Hyprland via `hyprctl cursorpos`
 - wlroots via `wl-find-cursor` (if installed)
 - XWayland via `xdotool getmouselocation --shell` (if DISPLAY present)
 - evdev relative-integration fallback (requires access to /dev/input/event*)

Usage:
    from wayland_cursor_watch import mouse_position_generator
    for x, y in mouse_position_generator():
        print(f"Mouse at: {x}, {y}")

Dependencies:
 - Python packages: evdev (only needed for the evdev fallback)
     pip install evdev
 - Optional binaries (used automatically if present):
     - hyprctl (Hyprland)
     - wl-find-cursor (wlroots tool)
     - xdotool (XWayland/X11)
"""

import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time

INTERVAL = 0.2
NUM_RE = re.compile(r"-?\d+")

# -------------------- Hyprland backend --------------------
class HyprlandBackend:
    name = "hyprctl"
    @staticmethod
    def available():
        return shutil.which("hyprctl") is not None

    @staticmethod
    def read_once():
        try:
            p = subprocess.run(["hyprctl", "cursorpos"], capture_output=True, text=True, timeout=0.5)
            txt = (p.stdout or "") + " " + (p.stderr or "")
            nums = NUM_RE.findall(txt)
            if len(nums) >= 2:
                x, y = int(nums[0]), int(nums[1])
                return x, y
        except Exception:
            return None
        return None

# -------------------- wl-find-cursor backend --------------------
class WlFindCursorBackend:
    name = "wl-find-cursor"

    @staticmethod
    def available():
        return shutil.which("wl-find-cursor") is not None

    def __init__(self):
        self.proc = None
        self._lock = threading.Lock()
        self._last = None
        self._running = False

    def start(self):
        cmd = shutil.which("wl-find-cursor")
        if not cmd:
            print(
                "[!] 'wl-find-cursor' not found.\n"
                "To install:\n"
                "  git clone https://github.com/cjacker/wl-find-cursor.git\n"
                "  cd wl-find-cursor\n"
                "  make\n"
                "  sudo cp wl-find-cursor /usr/local/bin/\n"
                "\nOnce installed, re-run this script."
            )
            return False

        # Launch wl-find-cursor process
        self.proc = subprocess.Popen(
            [cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self._running = True
        self._thr = threading.Thread(target=self._reader, daemon=True)
        self._thr.start()
        return True

    def _reader(self):
        if not self.proc or not self.proc.stdout:
            return
        try:
            for line in self.proc.stdout:
                if not self._running:
                    break
                nums = NUM_RE.findall(line)
                if len(nums) >= 2:
                    x, y = int(nums[0]), int(nums[1])
                    with self._lock:
                        self._last = (x, y)
        except Exception:
            pass

    def get_position(self):
        with self._lock:
            return self._last

    def stop(self):
        self._running = False
        try:
            if self.proc:
                self.proc.terminate()
        except Exception:
            pass

# -------------------- X11 / XWayland backend (xdotool) --------------------
class XdotoolBackend:
    name = "xdotool"
    @staticmethod
    def available():
        return ("DISPLAY" in os.environ) and (shutil.which("xdotool") is not None)

    @staticmethod
    def read_once():
        try:
            p = subprocess.run(["xdotool", "getmouselocation", "--shell"], capture_output=True, text=True, timeout=0.5)
            # example output:
            # X=880
            # Y=443
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
    def __init__(self, seed=(None, None)):
        try:
            from evdev import list_devices, InputDevice, ecodes
            self.evdev = True
            self.list_devices = list_devices
            self.InputDevice = InputDevice
            self.ecodes = ecodes
        except Exception:
            self.evdev = False
        self.device_path = None
        self.dev = None
        self._running = False
        self._lock = threading.Lock()
        self.width = None
        self.height = None
        self.x, self.y = seed
        if self.x is None or self.y is None:
            # default later when starting
            self.x = None
            self.y = None

    def available(self):
        return self.evdev

    def find_device(self):
        # find a REL_X/REL_Y device
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
                if isinstance(rels, dict):
                    rels_list = list(rels.keys())
                else:
                    rels_list = list(rels)
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

    def start(self):
        if not self.evdev:
            return False
        self.device_path = self.find_device()
        if not self.device_path:
            return False
        try:
            self.dev = self.InputDevice(self.device_path)
        except Exception:
            return False

        # get screen resolution if possible (try wayland util or fallback to 1920x1080)
        try:
            from wayland_automation.utils.screen_resolution import get_resolution
            h, w = get_resolution()
            self.width, self.height = int(w), int(h)
        except Exception:
            self.width, self.height = 1920, 1080

        # seed default if None
        if self.x is None or self.y is None:
            self.x = self.width // 2
            self.y = self.height // 2

        self._running = True
        self._thr = threading.Thread(target=self._reader, daemon=True)
        self._thr.start()
        return True

    def _reader(self):
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
                        # clamp
                        if self.x < 0: self.x = 0
                        if self.y < 0: self.y = 0
                        if self.x >= self.width: self.x = self.width - 1
                        if self.y >= self.height: self.y = self.height - 1
        except Exception as e:
            # device disconnect or permission error
            pass

    def get_position(self):
        with self._lock:
            return int(self.x), int(self.y)

    def stop(self):
        self._running = False
        try:
            if self.dev:
                self.dev.close()
        except Exception:
            pass

# -------------------- orchestrator --------------------
def pick_backend_and_start():
    # 1) Hyprland
    if HyprlandBackend.available():
        pos = HyprlandBackend.read_once()
        if pos:
            return ("hyprctl", lambda: HyprlandBackend.read_once(), None)

    # 2) wl-find-cursor (start streaming)
    if WlFindCursorBackend.available():
        w = WlFindCursorBackend()
        ok = w.start()
        if ok:
            return ("wl-find-cursor", w.get_position, w)

    # 3) xdotool if DISPLAY present (XWayland)
    if XdotoolBackend.available():
        pos = XdotoolBackend.read_once()
        if pos:
            return ("xdotool", lambda: XdotoolBackend.read_once(), None)

    # 4) evdev fallback (seed from previous attempts if any)
    # try to seed from hyprctl/xdotool outputs if available
    seed = None
    if HyprlandBackend.available():
        seed = HyprlandBackend.read_once()
    if seed is None and XdotoolBackend.available():
        seed = XdotoolBackend.read_once()

    ev = EvdevFallback(seed=seed or (None, None))
    if ev.available():
        started = ev.start()
        if started:
            return ("evdev", ev.get_position, ev)

    return (None, None, None)

def mouse_position_generator(interval=None, print_output=False):
    """
    Generator that yields (x, y) mouse positions continuously.
    
    Args:
        interval: Polling interval in seconds (default: 0.2)
        print_output: If True, prints positions to stdout
    
    Yields:
        tuple: (x, y) coordinates
    """
    if interval is None:
        interval = INTERVAL
    
    backend_name, getter, controller = pick_backend_and_start()
    if backend_name is None:
        raise RuntimeError("No backend available: install hyprctl (Hyprland) or wl-find-cursor (wlroots) or xdotool, or install python-evdev and grant access to /dev/input/event*.")

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
                # backend exists but returned no value yet
                if print_output:
                    print("Waiting for cursor data...    ", end="\r", flush=True)
                # Still yield something to keep the generator active
                if last:
                    yield last
            time.sleep(interval)
    except GeneratorExit:
        pass
    except KeyboardInterrupt:
        return
    finally:
        try:
            if controller:
                controller.stop()
        except Exception:
            pass

def main():
    """CLI interface - same as before for backward compatibility"""
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else INTERVAL
    print("Starting compositor-aware cursor watcher. (Ctrl+C to stop)")
    
    try:
        for x, y in mouse_position_generator(interval=interval, print_output=True):
            pass  # printing is handled inside the generator when print_output=True
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()