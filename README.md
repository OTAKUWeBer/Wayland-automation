# Wayland Automation

A powerful, modular Python library for Wayland automation, supporting mouse and keyboard control across various compositors (Hyprland, wlroots, etc.).

## Compatibility

This library currently relies on the **wlroots**-specific protocol `zwlr_virtual_pointer_manager_v1` for mouse positioning.

| Compositor | Mouse Support | Notes |
|------------|---------------|-------|
| Hyprland   | ✅ Full       | Wlroots-based |
| Sway       | ✅ Full       | Wlroots-based |
| KDE Plasma | ❌ Limited    | Keyboard works via `wtype`. Mouse support expected in KDE 6.5 via `pointer-warp-v1`. |
| GNOME      | ❌ Limited    | Keyboard works via `wtype`. Mouse support requires specific GNOME shell extensions or future protocols. |

## Troubleshooting

### SIGPIPE / Broken Pipe
If you encounter a `BrokenPipeError` or SIGPIPE, it often means the Wayland compositor disconnected the client because it attempted to use an unsupported protocol or performed an invalid operation.

### Protocol Not Found
If the library raises a `WaylandProtocolError`, your compositor does not support the required virtual pointer protocol. 

## Roadmap
- [ ] Support for KDE 6.5+ `pointer-warp-v1` protocol.
- [ ] Improved error handling for unsupported compositors.


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
kb.press("enter")
kb.hotkey("ctrl", "s")
```

### Mouse Control

```python
from wayland_automation.mouse_controller import Mouse

mouse = Mouse()
mouse.click(250, 300, "left")
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

This project is licensed under the [MIT Licence](LICENCE) - see the LICENSE file for details.
