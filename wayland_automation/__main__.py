"""
__main__.py — Command Line Interface for Wayland Automation.

Allows executing mouse, keyboard, and diagnostics commands directly from the terminal.
"""

import argparse
import os
import shutil
import sys
from typing import List

import wayland_automation as wa


def check_environment() -> int:
    """Run comprehensive diagnostics on environment, compositor, and tools."""
    # Use ascii-safe characters for compatibility across all terminals
    ok_sym = "[OK]"
    err_sym = "[FAIL]"
    opt_sym = "[-]"
    warn_sym = "[WARN]"

    print("==================================================")
    print(f"Wayland Automation v{wa.__version__} -- Diagnostics")
    print("==================================================")

    # 1. Environment variables
    print("\n[Environment]")
    w_display = os.getenv("WAYLAND_DISPLAY")
    x_desktop = os.getenv("XDG_CURRENT_DESKTOP")
    x_runtime = os.getenv("XDG_RUNTIME_DIR")
    x_display = os.getenv("DISPLAY")

    print(f"  WAYLAND_DISPLAY     : {w_display or 'Not set'}")
    print(f"  XDG_CURRENT_DESKTOP : {x_desktop or 'Not set'}")
    print(f"  XDG_RUNTIME_DIR     : {x_runtime or 'Not set'}")
    print(f"  DISPLAY (XWayland)  : {x_display or 'Not set'}")

    # 2. Required/Optional System Binaries
    print("\n[System Binaries]")
    tools = [
        ("wtype", "Keyboard automation", True),
        ("wayland-info", "Screen resolution detection", False),
        ("hyprctl", "Hyprland cursor tracking", False),
        ("wl-find-cursor", "wlroots / Sway cursor tracking", False),
        ("qdbus", "KDE Plasma / KWin D-Bus bridge", False),
        ("qdbus6", "KDE Plasma 6 D-Bus bridge", False),
        ("xdotool", "XWayland cursor tracking", False),
    ]

    all_ok = True
    for cmd, desc, required in tools:
        path = shutil.which(cmd)
        status = f"{ok_sym} Found ({path})" if path else (f"{err_sym} Missing (Required)" if required else f"{opt_sym} Missing (Optional)")
        if required and not path:
            all_ok = False
        print(f"  {cmd:<16} : {status} - {desc}")

    # 3. Python Packages
    print("\n[Python Packages]")
    pkgs = [
        ("evdev", "Hardware input fallback", False),
        ("dbus_next", "KDE Plasma native tracking", False),
    ]
    for pkg, desc, req in pkgs:
        try:
            __import__(pkg)
            status = f"{ok_sym} Installed"
        except ImportError:
            status = f"{opt_sym} Not installed (Optional)"
        print(f"  {pkg:<16} : {status} - {desc}")

    print("\n==================================================")
    if not w_display:
        print(f"{warn_sym} WARNING: WAYLAND_DISPLAY is not set. Are you in a Wayland session?")
    elif all_ok:
        print(f"{ok_sym} All essential dependencies are satisfied.")
    else:
        print(f"{warn_sym} Some required dependencies are missing. Check instructions above.")
    print("==================================================")
    return 0 if all_ok else 1


def main(argv: List[str] = None) -> int:
    """Main CLI entrypoint."""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="wayland-automation",
        description="Mouse, keyboard, and cursor tracking automation for Wayland.",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"wayland-automation {wa.__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: check
    subparsers.add_parser("check", help="Check system dependencies and environment")

    # Command: click
    p_click = subparsers.add_parser("click", help="Move cursor and click")
    p_click.add_argument("x", type=int, help="X coordinate")
    p_click.add_argument("y", type=int, help="Y coordinate")
    p_click.add_argument(
        "button",
        nargs="?",
        default="left",
        choices=["left", "right", "middle", "nothing"],
        help="Mouse button to click (default: left)",
    )

    # Command: swipe
    p_swipe = subparsers.add_parser("swipe", help="Simulate mouse drag / swipe")
    p_swipe.add_argument("start_x", type=int, help="Starting X")
    p_swipe.add_argument("start_y", type=int, help="Starting Y")
    p_swipe.add_argument("end_x", type=int, help="Ending X")
    p_swipe.add_argument("end_y", type=int, help="Ending Y")
    p_swipe.add_argument("--speed", default="normal", help="Duration in seconds (default: 1.0)")

    # Command: autoclick
    p_auto = subparsers.add_parser("autoclick", help="Repeated clicking")
    p_auto.add_argument("--delay", type=float, default=3.0, help="Initial delay in seconds")
    p_auto.add_argument("--interval", type=float, default=0.1, help="Interval between clicks")
    p_auto.add_argument("--duration", type=float, default=10.0, help="Total duration in seconds")
    p_auto.add_argument("--button", default="left", choices=["left", "right", "middle"])

    # Command: type
    p_type = subparsers.add_parser("type", help="Type text on keyboard")
    p_type.add_argument("text", help="Text to type")
    p_type.add_argument(
        "--interval", type=float, default=0.0, help="Interval between keystrokes in seconds"
    )

    # Command: press
    p_press = subparsers.add_parser("press", help="Press and release a key")
    p_press.add_argument("key", help="Key name (e.g. enter, esc, F5, a)")

    # Command: hotkey
    p_hotkey = subparsers.add_parser("hotkey", help="Trigger a key combination")
    p_hotkey.add_argument("keys", nargs="+", help="Keys to combine (e.g. ctrl shift t)")

    # Command: pos
    p_pos = subparsers.add_parser("pos", help="Monitor or get cursor position")
    p_pos.add_argument(
        "--interval", type=float, default=0.2, help="Polling interval in seconds"
    )
    p_pos.add_argument(
        "--once", action="store_true", help="Print cursor position once and exit"
    )

    if not argv:
        parser.print_help()
        return 0

    args = parser.parse_args(argv)

    if args.command == "check":
        return check_environment()

    elif args.command == "click":
        wa.click(args.x, args.y, args.button)
        return 0

    elif args.command == "swipe":
        wa.swipe(args.start_x, args.start_y, args.end_x, args.end_y, args.speed)
        return 0

    elif args.command == "autoclick":
        wa.auto_click(args.delay, args.interval, args.duration, args.button)
        return 0

    elif args.command == "type":
        wa.typewrite(args.text, args.interval)
        return 0

    elif args.command == "press":
        wa.press(args.key)
        return 0

    elif args.command == "hotkey":
        wa.hotkey(*args.keys)
        return 0

    elif args.command == "pos":
        if args.once:
            p = wa.get_position()
            if p:
                print(f"{p[0]} {p[1]}")
            else:
                print("Could not retrieve cursor position.")
                return 1
            return 0
        else:
            try:
                for _ in wa.mouse_position_generator(interval=args.interval, print_output=True):
                    pass
            except KeyboardInterrupt:
                print("\nStopped.")
            return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
