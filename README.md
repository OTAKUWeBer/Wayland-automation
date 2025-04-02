# **Wayland Automation**  

A lightweight Python tool for automating pointer and keyboard actions on Wayland. This project allows you to perform basic clicks, swipes, auto-clicks, and keyboard actions using virtual devices in your Wayland environment.

---

## **Features**

### **Pointer Automation (Mouse)**
- **Basic Click:**  
  Move the pointer to a specified `(x, y)` coordinate and optionally perform a click (left or right).

- **Swipe:**  
  Simulate a drag gesture by swiping from one coordinate to another, with a customizable speed.

- **Auto-Click:**  
  Wait for a configurable delay, then repeatedly click at the current pointer position for a set duration at defined intervals.

### **Keyboard Automation**
- **Typewrite:**  
  Type out a string with an optional delay between each character.

- **Press:**  
  Simulate a single key press (key down then key up).

- **Hotkey:**  
  Simulate key combinations (e.g., `Ctrl+A`).

---

## **Requirements**

- **Python 3.x**
- **Wayland Environment:**  
  Ensure you are running a Wayland session.

- **System Dependencies:**  
  This project relies on the following system-level utilities, which are not available via PyPI:

  - **wayland-info:** Used to obtain your screen resolution.
    - **Installation:**
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

  - **wtype:** Used for simulating keyboard actions.
    - **Installation (Arch Linux):**
      ```bash
      yay -S wtype
      ```
      or
      ```bash
      paru -S wtype
      ```

---

## **Installation**

### **Install via PyPI**
The package is available on PyPI and can be installed using:

```bash
pip install wayland-automation
```

### **Install from Source**
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

3. **Install System Dependencies:**  
   Ensure that both `wayland-info` and `wtype` are installed and available in your system's PATH as described above.

4. **Install the Python Package:**

   ```bash
   pip install .
   ```

   For development, consider using an editable install:

   ```bash
   pip install -e .
   ```

---

## **Usage**

### **Pointer Automation (Mouse)**

The pointer automation is handled by `mouse_controller.py`.

#### **Basic Click (Python API)**
Move the pointer to `(x, y)` and optionally perform a click.

```python
from wayland_automation.mouse_controller import Mouse

mouse = Mouse()
mouse.move(100, 200)  # Move to coordinates (100, 200)
mouse.click("left")  # Perform a left click
```

#### **Swipe (Drag)**
Simulate a swipe (drag) gesture from one coordinate to another.

```python
mouse.swipe(100, 200, 400, 500, speed=1.5)
```

#### **Auto-Click**
Automatically click at the current pointer position repeatedly.

```python
mouse.auto_click(initial_delay=2, interval=0.2, duration=15, button="right")
```

---

### **Keyboard Automation (Python API)**

```python
from wayland_automation.keyboard_controller import Keyboard
import time

kb = Keyboard()
time.sleep(2)  # Gives time to switch to another window

kb.typewrite("Hello, Wayland!", interval=0.05)
kb.press("enter")
kb.hotkey("ctrl", "a")
```

---

## **How It Works**

1. **Virtual Device Initialization:**  
   The scripts connect to the Wayland server via a Unix socket and initialize virtual devices (pointer and keyboard) using the Wayland protocol.

2. **Message Protocol:**  
   Low-level Wayland messages are sent to move the pointer, simulate button events, and emulate keyboard actions via `wtype`.

3. **Screen Resolution:**  
   A helper script in the `utils` directory uses `wayland-info` to retrieve your current screen resolution, ensuring accurate pointer positioning.

4. **Modes Implementation:**  
   - **Pointer Modes:**  
     Click, swipe, and auto-click actions are implemented by sending sequences of Wayland messages.
   - **Keyboard Mode:**  
     The keyboard module supports text entry, single key presses, and hotkey combinations.

---

## **Contributing**

Contributions, bug reports, and feature requests are welcome. Please open an issue or submit a pull request on the [GitHub repository](https://github.com/OTAKUWeBer/Wayland-automation).

---

## **Acknowledgements**

Special thanks to [Zai-Kun](https://github.com/Zai-Kun) for the foundational work on Wayland communication mechanisms that inspired this project.