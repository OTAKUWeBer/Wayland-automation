# Wayland Automation

A lightweight Python tool for automating pointer and keyboard actions on Wayland. This project allows you to perform basic clicks, swipes, auto-clicks, and keyboard actions using virtual devices in your Wayland environment.

## Features

- **Pointer Automation (Mouse):**
  - **Basic Click:** Move the pointer to a specified (x, y) coordinate and optionally perform a click (left or right).
  - **Swipe:** Simulate a drag gesture by swiping from one coordinate to another, with customizable speed.
  - **Auto-Click:** Wait for a configurable delay, then repeatedly click at the current pointer position for a set duration at defined intervals.

- **Keyboard Automation:**
  - **Typewrite:** Type out a string with an optional delay between each character.
  - **Press:** Simulate a single key press (key down then key up).
  - **Hotkey:** Simulate key combinations (e.g., Ctrl+A).

## Requirements

- **Python 3.x**
- **Wayland Environment:** Ensure you are running a Wayland session.
- **wayland-info:** This binary is required to obtain your screen resolution.
  - **Download/Installation:**
    - **GitHub:** [rtbo/wayland-info](https://github.com/rtbo/wayland-info)
    - **Debian/Ubuntu:**
      ```bash
      sudo apt install wayland-info
      ```
    - **Arch Linux:**
      ```bash
      yay -S wayland-info
      ```
      or
      ```bash
      paru -S wayland-info
      ```

- **wtype:** This binary is used for simulating keyboard actions.
  - **Installation (Arch Linux):**
    ```bash
    yay -S wtype
    ```
    or
    ```bash
    paru -S wtype
    ```

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/OTAKUWeBer/Wayland-automation.git
   cd Wayland-automation
   ```

2. **(Optional) Create a Virtual Environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Ensure `wayland-info` and `wtype` are Installed:**

   Verify that both binaries are installed and accessible in your system's PATH.

## Usage

This project provides two main modules: one for pointer automation (mouse) and one for keyboard automation.

### Pointer Automation

The pointer automation is handled by **mouse_controller.py**.

#### Basic Click

Move the pointer to `(x, y)` and optionally perform a click.

- **Default Mode (Implicit Click):**

  ```bash
  python mouse_controller.py <x> <y> [<button>]
  ```

- **Explicit Click Mode:**

  ```bash
  python mouse_controller.py click <x> <y> [<button>]
  ```

- **Parameters:**
  - `<x>`: X-coordinate.
  - `<y>`: Y-coordinate.
  - `[<button>]`: Optional. Specify `left` or `right` (case-insensitive) or a numeric code for the mouse button.

_Example:_

```bash
python mouse_controller.py 100 200 left
```

#### Swipe

Simulate a swipe (drag) gesture from one coordinate to another.

```bash
python mouse_controller.py swipe <start_x> <start_y> <end_x> <end_y> [<speed>]
```

- **Parameters:**
  - `<start_x>`, `<start_y>`: Starting coordinates.
  - `<end_x>`, `<end_y>`: Ending coordinates.
  - `[<speed>]`: Optional duration (in seconds) for the swipe (default: `1.0`).

_Example:_

```bash
python mouse_controller.py swipe 100 200 400 500 1.5
```

#### Auto-Click

Automatically click at the current pointer position repeatedly.

```bash
python mouse_controller.py autoclick [<initial_delay> <interval> <duration> <button>]
```

- **Parameters:**
  - `<initial_delay>`: Seconds to wait before starting auto-clicking (default: `3.0`).
  - `<interval>`: Seconds between each click (default: `0.1`).
  - `<duration>`: Total duration in seconds for auto-clicking (default: `10.0`).
  - `<button>`: Optional. Specify `left` or `right` (default: `left`).

_Example:_

```bash
python mouse_controller.py autoclick 2 0.2 15 right
```

### Keyboard Automation

The keyboard automation is provided by **keyboard_controller.py**. You can use this module within your own Python code. For example:

```python
from keyboard_controller import Keyboard
import time

kb = Keyboard()
time.sleep(2)  # Gives time to switch to another window
kb.typewrite("Hello, Wayland!", interval=0.05)
kb.press("enter")
kb.hotkey("ctrl", "a")
```

## How It Works

1. **Virtual Device Initialization:**  
   The scripts connect to the Wayland server via a Unix socket and initialize virtual devices (pointer and keyboard) using the Wayland protocol.

2. **Message Protocol:**  
   Low-level Wayland messages are sent to move the pointer, simulate button events, and emulate keyboard actions via `wtype`.

3. **Screen Resolution:**  
   A helper script (in the `utils` directory) uses `wayland-info` to retrieve your current screen resolution, ensuring accurate pointer positioning.

4. **Modes Implementation:**  
   - **Pointer Modes:**  
     Click, swipe, and auto-click actions are implemented by sending sequences of Wayland messages.
   - **Keyboard Mode:**  
     The keyboard module supports text entry, single key presses, and hotkey combinations.

## Contributing

Contributions, bug reports, and feature requests are welcome. Please open an issue or submit a pull request on the [GitHub repository](https://github.com/OTAKUWeBer/Wayland-automation).

## Acknowledgements

The main connecting pipe and Wayland communication mechanism used in this project is based on work by [Zai-Kun](https://github.com/Zai-Kun). Special thanks for providing the foundational components that make this automation possible.