#!/usr/bin/env python3
"""
mouse_position.py

Minimal evdev-based mouse position generator for Linux (works under Wayland).
Yields (x, y) continuously as a generator. Does not print by default.

Public API:
- mouse_position_generator(...)
- mouse_position_with_callback(...)
- show_help()
- cli(argv=None)
"""
from __future__ import annotations

import os
import time
import argparse
from select import select
from collections import namedtuple
from wayland_automation.utils.screen_resolution import get_resolution

try:
    import evdev
    from evdev import ecodes
except ImportError:
    raise SystemExit(
        "Missing dependency: python-evdev. Install with:\n\n"
        "  sudo pacman -S python-evdev\n"
        "or\n"
        "  pip3 install evdev\n"
    )

# fallback for older Pythons
import fcntl

DeviceInfo = namedtuple("DeviceInfo", ["dev", "is_relative", "abs_info"])

__all__ = [
    "mouse_position_generator",
    "mouse_position_with_callback",
    "show_help",
    "cli",
]


def normalize_resolution(res):
    if res is None:
        return 1080, 1920
    if isinstance(res, (tuple, list)) and len(res) >= 2:
        try:
            return int(res[0]), int(res[1])
        except Exception:
            pass
    if isinstance(res, str):
        for sep in ("x", "X", " ", ","):
            if sep in res:
                parts = [p.strip() for p in res.split(sep) if p.strip()]
                if len(parts) >= 2:
                    try:
                        return int(parts[0]), int(parts[1])
                    except Exception:
                        pass
        try:
            val = int(res)
            return val, val
        except Exception:
            pass
    try:
        val = int(res)
        return val, val
    except Exception:
        return 1080, 1920


def find_pointer_devices():
    devices = []
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
        except Exception:
            continue
        caps = dev.capabilities(verbose=False)
        is_rel = False
        abs_info = {}
        if ecodes.EV_REL in caps:
            rel_codes = [c for c in caps[ecodes.EV_REL]]
            if ecodes.REL_X in rel_codes or ecodes.REL_Y in rel_codes:
                is_rel = True
        if ecodes.EV_ABS in caps:
            abs_caps = dict(caps[ecodes.EV_ABS])
            for code in (ecodes.ABS_X, ecodes.ABS_Y,
                         ecodes.ABS_MT_POSITION_X, ecodes.ABS_MT_POSITION_Y):
                if code in abs_caps:
                    try:
                        abs_info[code] = dev.absinfo(code)
                    except Exception:
                        pass
        if is_rel or abs_info:
            devices.append(DeviceInfo(dev=dev, is_relative=is_rel, abs_info=abs_info))
    return devices


def scale_abs(value, absinfo, screen_size):
    if absinfo is None:
        return None
    amin = getattr(absinfo, "min", getattr(absinfo, "minimum", 0))
    amax = getattr(absinfo, "max", getattr(absinfo, "maximum", 1))
    try:
        amin, amax = int(amin), int(amax)
    except Exception:
        return None
    if amax == amin:
        return 0
    return int((value - amin) * (screen_size - 1) / (amax - amin))


def _set_nonblocking(fd):
    try:
        os.set_blocking(fd, False)
    except AttributeError:
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    except Exception:
        pass


def mouse_position_generator(poll_interval=0.05, print_output=False, print_interval=0.25):
    """
    Yields (x, y) continuously.
    - poll_interval: select() timeout
    - print_output: if True, prints positions in-place
    - print_interval: interval for printing
    """
    raw_res = get_resolution()
    height, width = normalize_resolution(raw_res)
    height = int(height); width = int(width)

    devices = find_pointer_devices()
    if not devices:
        raise RuntimeError("No pointer-like input devices found. Check /dev/input permissions.")

    for d in devices:
        try:
            _set_nonblocking(d.dev.fd)
        except Exception:
            pass

    cur_x = width // 2
    cur_y = height // 2
    fd_map = {d.dev.fd: d for d in devices}
    last_print_time = 0.0

    try:
        while True:
            if not fd_map:
                devices = find_pointer_devices()
                for d in devices:
                    try: _set_nonblocking(d.dev.fd)
                    except Exception: pass
                fd_map = {d.dev.fd: d for d in devices}
                if not fd_map:
                    time.sleep(poll_interval)
                    continue

            fds = list(fd_map.keys())
            r, _, _ = select(fds, [], [], poll_interval)
            changed = False

            for fd in r:
                dinfo = fd_map.get(fd)
                if not dinfo:
                    continue
                try:
                    for event in dinfo.dev.read():
                        if event.type == ecodes.EV_REL and dinfo.is_relative:
                            if event.code == ecodes.REL_X:
                                cur_x += event.value; changed = True
                            elif event.code == ecodes.REL_Y:
                                cur_y += event.value; changed = True
                        elif event.type == ecodes.EV_ABS and dinfo.abs_info:
                            if event.code in (ecodes.ABS_X, ecodes.ABS_MT_POSITION_X):
                                scaled = scale_abs(event.value, dinfo.abs_info.get(event.code), width)
                                if scaled is not None:
                                    cur_x = scaled; changed = True
                            elif event.code in (ecodes.ABS_Y, ecodes.ABS_MT_POSITION_Y):
                                scaled = scale_abs(event.value, dinfo.abs_info.get(event.code), height)
                                if scaled is not None:
                                    cur_y = scaled; changed = True
                except BlockingIOError:
                    pass
                except OSError:
                    fd_map.pop(fd, None)

            cur_x = max(0, min(cur_x, width - 1))
            cur_y = max(0, min(cur_y, height - 1))

            now = time.time()
            if print_output and (changed or (now - last_print_time) > print_interval):
                print(f"\rX: {cur_x:4d}  Y: {cur_y:4d}", end="", flush=True)
                last_print_time = now

            # always yield latest position each loop
            yield cur_x, cur_y

    except GeneratorExit:
        pass
    except KeyboardInterrupt:
        return
    finally:
        for d in devices:
            try: d.dev.close()
            except Exception: pass


def mouse_position_with_callback(callback, poll_interval=0.05, print_output=False, print_interval=0.25):
    """Simple wrapper that calls `callback(x, y)` for each yielded position."""
    for x, y in mouse_position_generator(poll_interval=poll_interval,
                                         print_output=print_output,
                                         print_interval=print_interval):
        try:
            callback(x, y)
        except Exception:
            # ignore callback errors
            pass


def show_help():
    """Print minimal help and examples."""
    print(__doc__)
    print("Examples:")
    print("  from mouse_position import mouse_position_generator")
    print("  for x,y in mouse_position_generator():")
    print("      print(x, y)")
    print("\nCLI:")
    print("  python -m mouse_position    # prints x,y lines until Ctrl+C")


def cli(argv=None):
    """Small CLI used for console_scripts entrypoint."""
    parser = argparse.ArgumentParser(prog="mousepos", description="Print continuous mouse positions.")
    parser.add_argument("--poll", type=float, default=0.02, help="select() poll interval (s)")
    parser.add_argument("--inplace", action="store_true", help="print single updating line")
    parser.add_argument("--no-header", action="store_true", help="suppress header")
    args = parser.parse_args(argv)

    if not args.no_header:
        print("mousepos — printing (x, y) until Ctrl+C")

    try:
        for x, y in mouse_position_generator(poll_interval=args.poll, print_output=args.inplace):
            if not args.inplace:
                print(f"{x}, {y}")
    except KeyboardInterrupt:
        print("\nStopped by user.")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
