"""
screen_resolution.py — Screen resolution detection for Wayland compositors.
"""

import json
import re
import shutil
import subprocess
from typing import Tuple

DEFAULT_RESOLUTION: Tuple[int, int] = (1920, 1080)


def get_resolution() -> Tuple[int, int]:
    """
    Detect the active display resolution on Wayland.

    Tries the following detection strategies in order:
      1. wayland-info (standard Wayland utility)
      2. hyprctl monitors (Hyprland compositor)
      3. swaymsg -t get_outputs (Sway / wlroots)
      4. wlr-randr (generic wlroots output tool)
      5. Default fallback: (1920, 1080)

    Returns:
        tuple[int, int]: (width, height) in pixels.
    """
    # 1. Try wayland-info
    if shutil.which("wayland-info"):
        try:
            res = subprocess.run(
                ["wayland-info"],
                capture_output=True,
                text=True,
                timeout=1.0,
            )
            if res.returncode == 0 and res.stdout:
                # Matches e.g. "width: 1920 px, height: 1080 px"
                match = re.search(r"width:\s*(\d+)\s*px,\s*height:\s*(\d+)\s*px", res.stdout)
                if match:
                    return int(match.group(1)), int(match.group(2))
                # Alternate pattern: e.g. "1920x1080"
                match = re.search(r"\b(\d{3,5})x(\d{3,5})\b", res.stdout)
                if match:
                    return int(match.group(1)), int(match.group(2))
        except Exception:
            pass

    # 2. Try hyprctl monitors (Hyprland)
    if shutil.which("hyprctl"):
        try:
            res = subprocess.run(
                ["hyprctl", "monitors"],
                capture_output=True,
                text=True,
                timeout=1.0,
            )
            if res.returncode == 0 and res.stdout:
                match = re.search(r"(\d{3,5})x(\d{3,5})@\d+", res.stdout)
                if match:
                    return int(match.group(1)), int(match.group(2))
        except Exception:
            pass

    # 3. Try swaymsg (Sway / wlroots)
    if shutil.which("swaymsg"):
        try:
            res = subprocess.run(
                ["swaymsg", "-t", "get_outputs"],
                capture_output=True,
                text=True,
                timeout=1.0,
            )
            if res.returncode == 0 and res.stdout:
                data = json.loads(res.stdout)
                if isinstance(data, list) and len(data) > 0:
                    rect = data[0].get("rect", {})
                    w = rect.get("width")
                    h = rect.get("height")
                    if w and h:
                        return int(w), int(h)
        except Exception:
            pass

    # 4. Try wlr-randr (wlroots)
    if shutil.which("wlr-randr"):
        try:
            res = subprocess.run(
                ["wlr-randr"],
                capture_output=True,
                text=True,
                timeout=1.0,
            )
            if res.returncode == 0 and res.stdout:
                match = re.search(r"(\d{3,5})x(\d{3,5})\s+px", res.stdout)
                if match:
                    return int(match.group(1)), int(match.group(2))
        except Exception:
            pass

    # 5. Default fallback
    return DEFAULT_RESOLUTION


if __name__ == "__main__":
    w, h = get_resolution()
    print(f"Screen resolution: {w}x{h}")
