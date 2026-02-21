# Wayland Automation

[![PyPI version](https://img.shields.io/pypi/v/wayland-automation.svg)](https://pypi.org/project/wayland-automation/)
[![Python 3.6+](https://img.shields.io/badge/python-3.6%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENCE)

A Python library for **mouse and keyboard automation** on Wayland compositors.
Works out of the box on **Hyprland, Sway**, and other **wlroots-based** compositors.

## Features

- **Mouse** — click, move, swipe (drag), and auto-click at any screen coordinate
- **Keyboard** — type text, press individual keys, and trigger hotkeys (e.g. `Ctrl+S`)
- **Cursor Tracking** — real-time cursor position via multiple backends (Hyprland → wl-find-cursor → xdotool → evdev)
- **Convenience API** — top-level functions so you can `import wayland_automation as wa` and go
- **Resilient** — automatic reconnection logic for Wayland socket resets

---

## Installation

### 1. Install the package

```bash
pip install wayland-automation
```

### 2. Install system dependencies

| Dependency | What it does | Install command |
|---|---|---|
| `wtype` | **Required** — keyboard automation | `sudo pacman -S wtype` (Arch) / `sudo apt install wtype` (Debian) / `sudo dnf install wtype` (Fedora) |
| `wayland-utils` | Screen resolution detection | `sudo pacman -S wayland-utils` (Arch) / `sudo apt install wayland-utils` (Debian) |

#### Mouse-tracking backends (pick the one for your compositor)

The library auto-detects the best backend. You only need to install the one that matches your setup:

| Backend | Compositor | Install |
|---|---|---|
| `hyprctl` | Hyprland | Pre-installed with Hyprland |
| `wl-find-cursor` | Sway / wlroots | See [build from source](#building-wl-find-cursor-from-source) below |
| `xdotool` | XWayland apps | `sudo pacman -S xdotool` / `sudo apt install xdotool` |
| `evdev` (fallback) | Any | `pip install evdev` + add user to `input` group (see below) |

<details>
<summary><strong>Building wl-find-cursor from source</strong></summary>

```bash
git clone https://github.com/cjacker/wl-find-cursor.git
cd wl-find-cursor
make
sudo cp wl-find-cursor /usr/local/bin/
```

</details>

<details>
<summary><strong>Setting up evdev fallback</strong></summary>

```bash
sudo usermod -aG input $USER
# Log out and back in for the group change to take effect
```

</details>

---

## Quick Start

### Top-level convenience API

The simplest way to use the library — no class instantiation needed:

```python
import wayland_automation as wa

# Mouse
wa.click(250, 300, "left")                # left-click at (250, 300)
wa.click(400, 500, "right")               # right-click
wa.swipe(100, 200, 800, 200)              # drag from point A to B
wa.auto_click(initial_delay=2, interval=0.1, duration=5)  # auto-clicker

# Keyboard
wa.typewrite("Hello Wayland!", interval=0.05)  # type text character by character
wa.press("enter")                              # press a single key
wa.hotkey("ctrl", "s")                         # key combination
```

### Using the classes directly

For more control, instantiate `Mouse` or `Keyboard`:

```python
from wayland_automation import Mouse, Keyboard

mouse = Mouse()
mouse.click(250, 300, "left")       # left-click at (250, 300)
mouse.click(600, 400, "nothing")    # move cursor without clicking
mouse.swipe(0, 500, 1000, 500, speed=0.5)  # fast swipe (0.5 s)

kb = Keyboard()
kb.typewrite("Hello!", interval=0.05)
kb.press("enter")
kb.hotkey("ctrl", "a")              # select all
kb.keyDown("shift")                 # hold shift
kb.keyUp("shift")                   # release shift
```

### Cursor Tracking

Stream real-time cursor coordinates:

```python
from wayland_automation import mouse_position_generator

for x, y in mouse_position_generator(interval=0.1):
    print(f"Cursor at: ({x}, {y})")
    # break whenever you want to stop
```

---

## CLI Usage

After installing the package, a `wayland-automation` command is available:

```bash
wayland-automation          # prints status
```

You can also run the individual modules directly:

```bash
# Mouse — click at (x, y)
python -m wayland_automation.mouse_controller click 250 300 left

# Mouse — swipe
python -m wayland_automation.mouse_controller swipe 100 200 800 200

# Mouse — auto-click (delay interval duration button)
python -m wayland_automation.mouse_controller autoclick 3 0.1 10 left

# Mouse — run built-in test
python -m wayland_automation.mouse_controller test

# Cursor position watcher
python -m wayland_automation.mouse_position
```

---

## API Reference

### `wayland_automation.click(x, y, button=None)`
Move the pointer to **(x, y)**. If `button` is given (`"left"`, `"right"`, or `"nothing"`), perform a click.

### `wayland_automation.swipe(start_x, start_y, end_x, end_y, speed="normal")`
Drag from one point to another. `speed` is duration in seconds (`"normal"` = 1.0 s).

### `wayland_automation.auto_click(initial_delay, interval, duration, button)`
Wait `initial_delay` seconds, then click every `interval` seconds for `duration` seconds.

### `wayland_automation.typewrite(text, interval=0)`
Type `text` one character at a time with an optional delay between characters.

### `wayland_automation.press(key)`
Press and release a single key (e.g. `"enter"`, `"tab"`, `"backspace"`, `"space"`).

### `wayland_automation.hotkey(*keys)`
Press a key combination (e.g. `hotkey("ctrl", "shift", "t")`). Modifier keys: `ctrl`, `alt`, `shift`, `super`.

### `wayland_automation.mouse_position_generator(interval=0.2, print_output=False)`
Generator yielding `(x, y)` tuples of the current cursor position.

---

## Compositor Compatibility

| Compositor | Mouse | Keyboard | Cursor Tracking | Notes |
|---|---|---|---|---|
| **Hyprland** | ✅ | ✅ | ✅ `hyprctl` | Full support (wlroots-based) |
| **Sway** | ✅ | ✅ | ✅ `wl-find-cursor` | Full support (wlroots-based) |
| **KDE Plasma** | ❌ | ✅ via `wtype` | ❌ | Mouse planned for KDE 6.5 (`pointer-warp-v1`) |
| **GNOME** | ❌ | ✅ via `wtype` | ❌ | Requires future protocol support |

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `BrokenPipeError` / SIGPIPE | Compositor disconnected the client | Ensure you are on a supported compositor and the protocol is available |
| `WaylandProtocolError` | `zwlr_virtual_pointer_manager_v1` not supported | Switch to a wlroots-based compositor (Hyprland / Sway) |
| `wtype` not found | System dependency missing | Install `wtype` (see [Installation](#2-install-system-dependencies)) |
| Cursor tracking returns nothing | No backend available | Install the backend matching your compositor (see table above) |

---

## Architecture

```
wayland_automation/
├── __init__.py             # Public API & convenience functions
├── __main__.py             # CLI entry point, dependency checks
├── mouse_controller.py     # Wayland socket communication for virtual pointer
├── keyboard_controller.py  # Keyboard automation via wtype
├── mouse_position.py       # Multi-backend cursor position tracking
└── utils/
    └── screen_resolution.py  # Screen resolution detection
```

## Roadmap

- [ ] KDE Plasma 6.5+ `pointer-warp-v1` protocol support
- [ ] Improved error messages for unsupported compositors
- [ ] Scroll wheel support

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT License](LICENCE)
