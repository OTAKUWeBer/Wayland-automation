# Wayland Automation

[![CI](https://github.com/OTAKUWeBer/Wayland-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/OTAKUWeBer/Wayland-automation/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/wayland-automation.svg)](https://pypi.org/project/wayland-automation/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENCE)

A lightweight, robust Python library for **mouse, keyboard, and cursor automation** on Wayland compositors. Designed as a modern Wayland-native alternative to PyAutoGUI.

Works out of the box on **Hyprland, Sway**, and other **wlroots-based** compositors, with native cursor position tracking on **KDE Plasma (KWin)**.

---

## Features

- **Mouse Control** — Move, click (`left`, `right`, `middle`, `nothing`), swipe (drag), and auto-click at absolute coordinates.
- **Keyboard Automation** — Type text, tap keys, hold keys down/up, and execute complex hotkeys (`Ctrl+Alt+T`, `Ctrl+S`).
- **Cursor Tracking** — Real-time position generator or one-shot snapshot (`get_position()`) across multiple compositors:
  - Hyprland (`hyprctl`)
  - Sway / wlroots (`wl-find-cursor`)
  - KDE Plasma (`kwin` scripting via D-Bus)
  - XWayland (`xdotool`)
  - Kernel input fallback (`evdev`)
- **Fast & Efficient** — Optimized typing leveraging `wtype -d` batching and automatic socket connection pooling.
- **Clean Resource Management** — Context manager support (`with Mouse() as mouse:`), safe socket lifecycle, and no dangling file descriptors.
- **Full CLI & Diagnostics** — Built-in `wayland-automation check` to diagnose compositors, environment variables, and missing tools in seconds.

---

## Installation

### 1. Install via pip

```bash
# Standard install
pip install wayland-automation

# With KDE Plasma cursor tracking support
pip install "wayland-automation[kde]"
```

### 2. System Dependencies

Wayland's security architecture requires specific tools or protocols depending on what you want to automate:

| Dependency | Purpose | Install Command |
|---|---|---|
| `wtype` | **Required** for keyboard automation | `sudo pacman -S wtype` (Arch) <br> `sudo apt install wtype` (Debian/Ubuntu) <br> `sudo dnf install wtype` (Fedora) |
| `wayland-utils` | Screen resolution detection | `sudo pacman -S wayland-utils` (Arch) <br> `sudo apt install wayland-utils` (Debian/Ubuntu) <br> `sudo dnf install wayland-utils` (Fedora) |

#### Cursor Tracking Backends

The library automatically detects the best available backend:

| Backend | Compositor | Requirement / Install |
|---|---|---|
| `hyprctl` | Hyprland | Built into Hyprland (zero configuration) |
| `wl-find-cursor` | Sway / wlroots | Compile from [source](#building-wl-find-cursor-from-source) |
| `kwin` (D-Bus) | KDE Plasma | `pip install dbus-next` (`qdbus` is pre-installed) |
| `xdotool` | XWayland windows | `sudo pacman -S xdotool` / `sudo apt install xdotool` |
| `evdev` (fallback) | Generic Linux | `pip install evdev` + add user to `input` group |

<details>
<summary><strong>Building wl-find-cursor from source (Sway / wlroots)</strong></summary>

```bash
git clone https://github.com/cjacker/wl-find-cursor.git
cd wl-find-cursor
make
sudo cp wl-find-cursor /usr/local/bin/
```
</details>

<details>
<summary><strong>Setting up evdev fallback permission</strong></summary>

```bash
sudo usermod -aG input $USER
# Log out and log back in for group membership to take effect
```
</details>

---

## Quick Start

### Top-level Convenience API

The simplest way to automate tasks — no manual initialization needed:

```python
import wayland_automation as wa

# --- Mouse ---
wa.click(250, 300, "left")                 # Left click at (250, 300)
wa.click(400, 500, "right")                # Right click
wa.click(600, 700, "middle")               # Middle click
wa.click(100, 100, "nothing")              # Move pointer without clicking
wa.swipe(100, 200, 800, 200, speed=0.5)    # Drag from A to B in 0.5s
wa.auto_click(initial_delay=2, interval=0.1, duration=5) # Repeated clicks

# --- Cursor Position ---
x, y = wa.get_position()                   # Single snapshot
print(f"Current cursor position: ({x}, {y})")

# --- Keyboard ---
wa.typewrite("Hello Wayland!", interval=0.05) # Type text with delay
wa.press("enter")                             # Tap Enter key
wa.hotkey("ctrl", "shift", "t")               # Key combination
```

### Context Manager (Explicit Lifetime)

For fine-grained resource control or high-throughput mouse automation:

```python
from wayland_automation import Mouse, Keyboard

with Mouse() as mouse:
    for x in range(100, 500, 50):
        mouse.click(x, 200, "left")

kb = Keyboard()
kb.typewrite("Done!")
```

### Streaming Cursor Position

Monitor live mouse motion with an event generator:

```python
from wayland_automation import mouse_position_generator

for x, y in mouse_position_generator(interval=0.1):
    print(f"Cursor: ({x}, {y})")
    # Break loop whenever needed
```

---

## Command Line Interface (CLI)

The package provides a built-in `wayland-automation` CLI tool:

### Diagnostics

Verify your compositor setup, environment variables, and installed tools:

```bash
wayland-automation check
```

### Automation Commands

```bash
# Mouse click & move
wayland-automation click 500 300 left
wayland-automation click 500 300 nothing   # Move only

# Drag / swipe
wayland-automation swipe 100 100 600 600 --speed 1.5

# Auto-clicker
wayland-automation autoclick --delay 2.0 --interval 0.05 --duration 5.0 --button left

# Keyboard
wayland-automation type "Automating Wayland like a pro" --interval 0.02
wayland-automation press Return
wayland-automation hotkey ctrl alt t

# Cursor position
wayland-automation pos --once              # Print single (x, y)
wayland-automation pos --interval 0.1      # Live coordinate feed
```

---

## API Reference

### Mouse Functions

- `wa.click(x: int, y: int, button: str = "left")`  
  Moves pointer to `(x, y)` and optionally triggers a click. Options: `"left"`, `"right"`, `"middle"`, `"nothing"` (move only).
- `wa.swipe(start_x: int, start_y: int, end_x: int, end_y: int, speed: Union[str, float] = "normal")`  
  Drags from `(start_x, start_y)` to `(end_x, end_y)`. `speed` can be `"normal"` (1.0s) or seconds as a float.
- `wa.auto_click(initial_delay: float = 3.0, interval: float = 0.1, duration: float = 10.0, button: str = "left")`  
  Waits `initial_delay`, then clicks at the current cursor position repeatedly.
- `wa.cleanup()`  
  Releases cached sockets and connections (automatically invoked on interpreter exit).

### Keyboard Functions

- `wa.typewrite(text: str, interval: float = 0.0)`  
  Types text. If `interval > 0`, adds a delay between keystrokes.
- `wa.press(key: str)`  
  Taps (presses and releases) a single key (e.g. `"enter"`, `"escape"`, `"tab"`, `"backspace"`, `"f5"`, `"up"`, `"down"`).
- `wa.keyDown(key: str)`  
  Holds a key down.
- `wa.keyUp(key: str)`  
  Releases a held key.
- `wa.hotkey(*keys: str)`  
  Presses modifier keys, taps non-modifiers, and safely releases modifiers in reverse order.

### Cursor Tracking Functions

- `wa.get_position() -> tuple[int, int]`  
  Retrieves a single snapshot of the current cursor coordinate.
- `wa.position() -> tuple[int, int]`  
  Alias for `get_position()`.
- `wa.mouse_position_generator(interval: float = 0.2, print_output: bool = False)`  
  Yields `(x, y)` tuples continuously.

---

## Compositor Compatibility Matrix

| Compositor | Mouse Actions | Keyboard | Cursor Tracking | Protocol / Backend |
|---|:---:|:---:|:---:|---|
| **Hyprland** | ✅ | ✅ | ✅ | `zwlr_virtual_pointer_manager_v1` + `hyprctl` |
| **Sway** | ✅ | ✅ | ✅ | `zwlr_virtual_pointer_manager_v1` + `wl-find-cursor` |
| **Other wlroots** | ✅ | ✅ | ✅ | `zwlr_virtual_pointer_manager_v1` + `wl-find-cursor` |
| **KDE Plasma** | ⏳ Planned | ✅ | ✅ | Tracking via KWin Script + D-Bus (`dbus-next`); click planned via `pointer-warp-v1` |
| **GNOME** | ❌ | ✅ | ⚠️ | Keyboard via `wtype`; pointer restricted by Mutter security policy |

---

## Architecture

```
Wayland-automation/
├── wayland_automation/
│   ├── __init__.py           # Public API & connection lifecycle
│   ├── __main__.py           # CLI entry point & diagnostics engine
│   ├── mouse_controller.py   # Low-level Wayland socket client (zwlr_virtual_pointer)
│   ├── keyboard_controller.py# Keyboard automation via wtype
│   ├── mouse_position.py     # Multi-backend cursor position resolver
│   ├── kwin_cursor_pos.js    # KWin scripting companion for KDE Plasma
│   └── utils/
│       ├── __init__.py
│       └── screen_resolution.py # Display resolution detection across compositors
├── tests/                    # Automated test suite
├── .github/workflows/        # CI & PyPI deployment pipelines
├── pyproject.toml            # Modern PEP 517/621 build configuration
├── setup.py                  # Setuptools packaging metadata
└── MANIFEST.in               # Source distribution manifest
```

---

## Contributing

Contributions and bug reports are warmly welcome!
1. Fork the repository & clone locally.
2. Run unit tests before submitting changes:
   ```bash
   python -m unittest discover tests -v
   ```
3. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## License

Distributed under the [MIT License](LICENCE). Copyright (c) 2025–2026 OTAKUWeBer.
