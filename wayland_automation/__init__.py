"""
Wayland Automation — A Python library for automating mouse and keyboard
input on Wayland compositors (Hyprland, Sway, and other wlroots-based).

Quick start::

    import wayland_automation as wa

    # Mouse
    wa.click(250, 300, "left")            # click at coordinates
    x, y = wa.get_position()               # get current cursor position
    wa.swipe(100, 200, 800, 200)          # drag gesture

    # Keyboard
    wa.typewrite("Hello!", interval=0.05) # type text
    wa.press("enter")                     # press key
    wa.hotkey("ctrl", "s")                # keyboard shortcut
"""

import atexit
from typing import Any, Generator, Optional, Tuple, Union

__version__ = "0.3.0"

# Button constants (re-exported for convenience)
BUTTON_LEFT = 0x110
BUTTON_RIGHT = 0x111
BUTTON_MIDDLE = 0x112

__all__ = [
    "__version__",
    "Mouse",
    "Keyboard",
    "BUTTON_LEFT",
    "BUTTON_RIGHT",
    "BUTTON_MIDDLE",
    "WaylandConnectionError",
    "WaylandProtocolError",
    "KeyboardError",
    "click",
    "swipe",
    "auto_click",
    "get_position",
    "position",
    "mouse_position_generator",
    "typewrite",
    "press",
    "keyDown",
    "keyUp",
    "hotkey",
    "print_usage",
    "cleanup",
]

# Internal cached instances for top-level convenience functions
_default_mouse = None
_default_keyboard = None


def _get_default_mouse():
    global _default_mouse
    if _default_mouse is None or not _default_mouse.is_connected():
        from .mouse_controller import Mouse
        _default_mouse = Mouse()
    return _default_mouse


def _get_default_keyboard():
    global _default_keyboard
    if _default_keyboard is None:
        from .keyboard_controller import Keyboard
        _default_keyboard = Keyboard()
    return _default_keyboard


def click(x: int, y: int, button: Optional[Union[str, int]] = "left") -> None:
    """Move cursor to (x, y) and perform a click."""
    _get_default_mouse().click(x, y, button)


def swipe(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    speed: Union[str, float] = "normal",
) -> None:
    """Drag cursor from (start_x, start_y) to (end_x, end_y)."""
    _get_default_mouse().swipe(start_x, start_y, end_x, end_y, speed)


def auto_click(
    initial_delay: float = 3.0,
    interval: float = 0.1,
    duration: float = 10.0,
    button: Union[str, int] = "left",
) -> None:
    """Repeatedly click at current cursor position."""
    _get_default_mouse().auto_click(initial_delay, interval, duration, button)


def get_position() -> Optional[Tuple[int, int]]:
    """Retrieve current (x, y) cursor coordinates as a single snapshot."""
    from .mouse_position import get_position as _get_pos
    return _get_pos()


def position() -> Optional[Tuple[int, int]]:
    """Alias for get_position()."""
    return get_position()


def mouse_position_generator(
    interval: Optional[float] = None, print_output: bool = False
) -> Generator[Tuple[int, int], None, None]:
    """Continuous generator yielding (x, y) coordinates."""
    from .mouse_position import mouse_position_generator as _gen
    return _gen(interval=interval, print_output=print_output)


def typewrite(text: str, interval: float = 0.0) -> None:
    """Type text on keyboard."""
    _get_default_keyboard().typewrite(text, interval)


def press(key: str) -> None:
    """Press and release a key."""
    _get_default_keyboard().press(key)


def keyDown(key: str) -> None:
    """Press and hold a key or modifier."""
    _get_default_keyboard().keyDown(key)


def keyUp(key: str) -> None:
    """Release a held key or modifier."""
    _get_default_keyboard().keyUp(key)


def hotkey(*keys: str) -> None:
    """Trigger a hotkey combination (e.g. hotkey('ctrl', 's'))."""
    _get_default_keyboard().hotkey(*keys)


def cleanup() -> None:
    """Close any open connections and release cached resources."""
    global _default_mouse, _default_keyboard
    if _default_mouse is not None:
        _default_mouse.close()
        _default_mouse = None
    _default_keyboard = None


atexit.register(cleanup)


def __getattr__(name: str) -> Any:
    """PEP 562 lazy loading of module classes and exceptions to avoid double-import warnings."""
    if name in (
        "Mouse",
        "WaylandConnectionError",
        "WaylandProtocolError",
        "print_usage",
    ):
        from . import mouse_controller
        return getattr(mouse_controller, name)
    elif name in ("Keyboard", "KeyboardError"):
        from . import keyboard_controller
        return getattr(keyboard_controller, name)
    elif name in ("get_position", "mouse_position_generator"):
        from . import mouse_position
        return getattr(mouse_position, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
