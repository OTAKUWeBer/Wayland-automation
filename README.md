# Wayland Automation

A lightweight Python tool for automating pointer actions on Wayland. This project allows you to perform basic clicks, swipes, and auto-clicks using a virtual pointer in your Wayland environment.

## Features

- **Basic Click:** Move the pointer to a specified (x, y) coordinate and optionally perform a click (left or right).
- **Swipe:** Simulate a drag gesture by swiping from one coordinate to another, with customizable speed.
- **Auto-Click:** Wait for a configurable delay, then repeatedly click at the current pointer position for a set duration at defined intervals.

## Requirements

- **Python 3.x**
- **Wayland Environment:** Ensure you are running a Wayland session.
- **wayland-info:** This binary is required to obtain your screen resolution.
  - **Download/Installation:**  
    - You can download or build `wayland-info` from its GitHub repository: [rtbo/wayland-info](https://github.com/rtbo/wayland-info).  
    - **Debian/Ubuntu:**  
      Install via apt (if available):  
      ```bash
      sudo apt install wayland-info
      ```
    - **Arch Linux:**  
      Install from the AUR using your preferred AUR helper (e.g., with yay/paru):  
      ```bash
      yay/paru -S wayland-info
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

3. **Ensure `wayland-info` is Installed:**

   Verify that `wayland-info` is installed and accessible in your system's PATH. Refer to the instructions above for Debian/Ubuntu or Arch Linux.

## Usage

Run the script using Python in one of the following modes:

### Basic Click

Move the pointer to `(x, y)` and optionally perform a click.

#### Default Mode (Implicit Click):

```bash
python click.py <x> <y> [<button>]
```

#### Explicit Click Mode:

```bash
python click.py click <x> <y> [<button>]
```

- `<x>`: X-coordinate.
- `<y>`: Y-coordinate.
- `[<button>]`: Optional. Specify `left` or `right` (case-insensitive) or a numeric code for the mouse button.

_Example:_

```bash
python click.py 100 200 left
```

### Swipe

Simulate a swipe (drag) gesture from one coordinate to another.

```bash
python click.py swipe <start_x> <start_y> <end_x> <end_y> [<speed>]
```

- `<start_x>`, `<start_y>`: Starting coordinates.
- `<end_x>`, `<end_y>`: Ending coordinates.
- `[<speed>]`: Optional duration (in seconds) for the swipe. Defaults to `1.0` second if omitted or set to `"normal"`.

_Example:_

```bash
python click.py swipe 100 200 400 500 1.5
```

### Auto-Click

Automatically click at the current pointer position repeatedly.

```bash
python click.py autoclick [<initial_delay> <interval> <duration> <button>]
```

- `<initial_delay>`: Seconds to wait before starting auto-clicking (default: `3.0` seconds).
- `<interval>`: Seconds between each click (default: `0.1` seconds).
- `<duration>`: Total duration in seconds to perform auto-clicking (default: `10.0` seconds).
- `<button>`: Optional. Specify `left` or `right` (case-insensitive) or a numeric button code (default: `left`).

_Example:_

```bash
python click.py autoclick 2 0.2 15 right
```

## How It Works

1. **Virtual Pointer Initialization:**  
   The script connects to the Wayland server via a Unix socket and initializes a virtual pointer through the Wayland protocol.

2. **Message Protocol:**  
   It sends low-level Wayland messages to move the pointer and simulate button press and release events.

3. **Screen Resolution:**  
   The helper script uses the `wayland-info` binary to retrieve your current screen resolution, ensuring accurate pointer positioning.

4. **Modes Implementation:**  
   - **Click Mode:** Moves the pointer and triggers a press/release sequence.
   - **Swipe Mode:** Gradually moves the pointer across a series of calculated steps to simulate a smooth drag.
   - **Auto-Click Mode:** After a delay, clicks repeatedly at a set interval until the specified duration elapses.

## Contributing

Contributions, bug reports, and feature requests are welcome. Please open an issue or submit a pull request on the [GitHub repository](https://github.com/OTAKUWeBer/Wayland-automation).

## Acknowledgements

The main connecting pipe and Wayland communication mechanism used in this project is based on work by [Zai-Kun](https://github.com/Zai-Kun). Special thanks for providing the foundational components that make this automation possible.