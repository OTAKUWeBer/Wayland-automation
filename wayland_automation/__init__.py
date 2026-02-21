"""
Wayland Automation — A Python library for automating mouse and keyboard
input on Wayland compositors (Hyprland, Sway, and other wlroots-based).

Quick start::

    import wayland_automation as wa

    wa.click(250, 300, "left")          # click at coordinates
    wa.typewrite("Hello!", interval=0.05)  # type text
    wa.hotkey("ctrl", "s")              # keyboard shortcut
"""

from .mouse_controller import Mouse, print_usage
from .mouse_position import mouse_position_generator
from .keyboard_controller import Keyboard

__version__ = "0.2.7"

__all__ = [
    "__version__",
    "swipe", 
    "click", 
    "auto_click", 
    "print_usage", 
    "typewrite", 
    "press", 
    "hotkey", 
    "mouse_position_generator"
]

def swipe(start_x, start_y, end_x, end_y, speed="normal"):
    Mouse().swipe(start_x, start_y, end_x, end_y, speed)

def click(x, y, button=None):
    Mouse().click(x, y, button)

def auto_click(initial_delay=3.0, interval=0.1, duration=10.0, button="left"):
    Mouse().auto_click(initial_delay, interval, duration, button)

def typewrite(text, interval=0):
    Keyboard().typewrite(text, interval)

def press(key):
    Keyboard().press(key)

def hotkey(*keys):
    Keyboard().hotkey(*keys)
