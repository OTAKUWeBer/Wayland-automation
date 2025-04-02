import subprocess
import time

class Keyboard:
    """
    A simple keyboard automation module for Wayland using `wtype`.

    Methods:
    - typewrite(text, interval=0): Types text with an optional delay between characters.
    - press(key): Presses and releases a key.
    - keyDown(key): Simulates pressing a key down.
    - keyUp(key): Simulates releasing a key.
    - hotkey(*keys): Simulates a key combination (e.g., hotkey('ctrl', 's')).
    """

    def __init__(self):
        # Mapping common modifier names to what wtype expects.
        self.modifier_map = {
            "ctrl": "ctrl",
            "control": "ctrl",
            "alt": "alt",
            "shift": "shift",
            "super": "super"
        }
        # A mapping for some common keys to their special characters.
        self.key_map = {
            "enter": "\n",
            "backspace": "\b",
            "tab": "\t",
            "space": " "
        }

    def typewrite(self, text: str, interval: float = 0):
        """Types the given text with an optional interval between characters."""
        for char in text:
            subprocess.run(["wtype", char])
            time.sleep(interval)

    def press(self, key: str):
        """Presses and releases a single key."""
        self.keyDown(key)
        self.keyUp(key)

    def keyDown(self, key: str):
        """Simulates holding a key down."""
        lower_key = key.lower()
        if lower_key in self.key_map:
            subprocess.run(["wtype", self.key_map[lower_key]])
        elif lower_key in self.modifier_map:
            # For modifiers, use -M (key down)
            subprocess.run(["wtype", "-M", self.modifier_map[lower_key]])
        else:
            # For other keys, assume regular key press down.
            subprocess.run(["wtype", "-k", lower_key])

    def keyUp(self, key: str):
        """Simulates releasing a held key."""
        lower_key = key.lower()
        if lower_key in self.modifier_map:
            # For modifiers, use -m (key up)
            subprocess.run(["wtype", "-m", self.modifier_map[lower_key]])
        # For non-modifiers, typically no separate release command is needed.

    def hotkey(self, *keys):
        """
        Simulates a key combination by constructing a single wtype command that:
          - Presses all modifier keys down
          - Presses non-modifier key(s)
          - Releases the modifier keys in reverse order.
        Example:
            hotkey('ctrl', 'b') will simulate Ctrl+B.
        """
        modifiers = []
        non_modifiers = []

        for key in keys:
            if key.lower() in self.modifier_map:
                modifiers.append(self.modifier_map[key.lower()])
            else:
                non_modifiers.append(key.lower())

        # Build the command list in one go.
        cmd = ["wtype"]
        # Press modifiers down
        for mod in modifiers:
            cmd.extend(["-M", mod])
        # Press non-modifiers
        for key in non_modifiers:
            cmd.extend(["-k", key])
        # Release modifiers (in reverse order)
        for mod in reversed(modifiers):
            cmd.extend(["-m", mod])

        subprocess.run(cmd)

# Example Usage
if __name__ == "__main__":
    kb = Keyboard()
    time.sleep(2)  # Gives time to switch to another window
    kb.typewrite("Hello, Wayland!", interval=0.05)
    kb.press("enter")
    kb.hotkey("ctrl", "a")
