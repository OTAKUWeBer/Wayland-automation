# Wayland Automation

A powerful, modular Python library for Wayland automation, supporting mouse and keyboard control across various compositors (Hyprland, wlroots, etc.).

## Features

- **Mouse Control**: Move, click, and drag with compositor-aware positioning.
- **Keyboard Control**: Type text, press keys, and handle complex hotkeys via `wtype`.
- **Compositor Support**: Multiple backends for cursor tracking (Hyprland, wl-find-cursor, XWayland, and evdev fallback).
- **Resilient Connections**: Built-in reconnection logic for Wayland sockets to handle session resets.

## Installation

### 1. Python Package

```bash
pip install wayland-automation
```

### 2. System Dependencies

Wayland Automation requires specific system tools depending on your environment and compositor.

#### Core Wayland Tools
- **Arch Linux**: `sudo pacman -S wayland-utils`
- **Ubuntu/Debian**: `sudo apt install wayland-utils`

#### Keyboard Support (Required)
You must install `wtype` for keyboard automation:
- **Arch Linux**: `sudo pacman -S wtype`
- **Ubuntu/Debian**: `sudo apt install wtype`
- **Fedora**: `sudo dnf install wtype`

#### Mouse Tracking Backends
The library automatically picks the best available backend for your compositor:

1. **Hyprland**: Requires `hyprctl` (pre-installed with Hyprland).
2. **wlroots (Sway, River, etc.)**: Requires `wl-find-cursor`.
   - **Arch Linux**: `sudo pacman -S wl-find-cursor` (if available in AUR/Repo)
   - **Ubuntu/Debian**: `sudo apt install wl-find-cursor`
   - **From Source**:
     ```bash
     git clone https://github.com/cjacker/wl-find-cursor.git
     cd wl-find-cursor
     make
     sudo cp wl-find-cursor /usr/local/bin/
     ```
3. **XWayland**: Requires `xdotool` if you are automating XWayland applications.
4. **Generic Fallback**: Uses `evdev`. Requires your user to be in the `input` group:
   ```bash
   sudo usermod -aG input $USER
   ```
   *Note: Log out and back in for group changes to take effect.*

## Quick Start

### Keyboard Control

```python
from wayland_automation.keyboard_controller import Keyboard

kb = Keyboard()
kb.typewrite("Hello Wayland!", interval=0.1)
kb.hotkey("ctrl", "s")
```

### Mouse Control

```python
from wayland_automation.mouse_controller import Mouse

mouse = Mouse()
mouse.move_to(500, 500)
mouse.click()
```

### Cursor Tracking

```python
from wayland_automation.mouse_position import mouse_position_generator

for x, y in mouse_position_generator(interval=0.1):
    print(f"Mouse is at: {x}, {y}")
```

## Architecture

The project is structured into modular components:
- `mouse_controller.py`: Low-level Wayland socket communication for virtual pointer events.
- `keyboard_controller.py`: Wrapper around `wtype` for keyboard input.
- `mouse_position.py`: Multi-backend orchestrator for retrieving current cursor coordinates.

## Contributing

We welcome contributions! Please see `CONTRIBUTING.md` for guidelines on submitting pull requests and code style.

## License

This project is licensed under the [MIT License](LICENCE) - see the LICENSE file for details.
