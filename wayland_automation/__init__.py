from .mouse_controller import Mouse, print_usage
from .keyboard_controller import Keyboard

__all__ = ["swipe", "click", "auto_click", "print_usage", "typewrite", "press", "hotkey"]

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
