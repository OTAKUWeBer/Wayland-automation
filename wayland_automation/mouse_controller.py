"""
mouse_controller.py — Low-level Wayland virtual pointer control.

Provides the ``Mouse`` class for moving, clicking, swiping, auto-clicking, scrolling,
and pressing or releasing buttons at absolute screen coordinates via the ``zwlr_virtual_pointer_manager_v1``
protocol (wlroots-based compositors: Hyprland, Sway, …).

Usage::

    from wayland_automation import Mouse

    with Mouse() as mouse:
        mouse.click(250, 300, "left")                  # left-click
        mouse.click(600, 400, "nothing")               # move only
        mouse.swipe(100, 200, 800, 200)                # drag gesture
        mouse.auto_click(initial_delay=2, interval=0.1, duration=5)
        mouse.scroll(-5)                               # scroll down
        mouse.scroll(2, 500, 800)                      # move and scroll up
        mouse.mouse_down()                             # press the left mouse button
        mouse.mouse_up()                               # release the left mouse button
        mouse.mouse_down(500, 200, "right")            # move and press the right mouse button
        mouse.mouse_up(300, 100, "right")              # move and release the right mouse button

CLI::

    python -m wayland_automation.mouse_controller click 250 300 left
    python -m wayland_automation.mouse_controller swipe 100 200 800 200
    python -m wayland_automation.mouse_controller autoclick 3 0.1 10 left
    python -m wayland_automation.mouse_controller scroll 2 500 800
    python -m wayland_automation.mouse_controller test
"""

import logging
import os
import socket
import struct
import sys
import time
from typing import Optional, Tuple, Union
from wayland_automation.utils.screen_resolution import get_resolution

logger = logging.getLogger(__name__)

# Button constants (Linux input event codes)
BUTTON_LEFT = 0x110
BUTTON_RIGHT = 0x111
BUTTON_MIDDLE = 0x112

# Degrees of rotation corresponding to one mouse wheel click (libinput convention)
WHEEL_CLICK_ANGLE = 15.0

# Mouse wheel axes constants
AXIS_VERTICAL = 0
AXIS_HORIZONTAL = 1

# Mouse button states
BUTTON_STATE_RELEASED = 0
BUTTON_STATE_PRESSED = 1


class WaylandProtocolError(Exception):
    """Exception raised when a required Wayland protocol is not available."""
    pass


class WaylandConnectionError(Exception):
    """Exception raised when connection to Wayland fails."""
    pass


def encode_wayland_string(s: Optional[str]) -> bytes:
    """Encode string according to the Wayland wire protocol."""
    if s is None:
        return struct.pack("<I", 0)
    encoded = s.encode("utf-8") + b"\x00"
    length = len(encoded)
    padding_size = (4 - (length % 4)) % 4
    padding = b"\x00" * padding_size
    return struct.pack("<I", length) + encoded + padding


def convert_float_to_wl_fixed_t(x: float) -> int:
    """Convert a float to wl_fixed_t: a 24.8 fixed-point integer"""
    # multiply by 2^8 because wl_fixed_t has 8 fractional bits
    return int(x * 256)


class Mouse:
    """
    Wayland virtual pointer controller.

    Supports absolute cursor positioning, button clicks (left, right, middle), scrolling,
    swipe gestures, auto-clicking, and pressing/releasing mouse buttons on wlroots-based compositors
    (Hyprland, Sway, etc.).
    """

    def __init__(self):
        self.sock: Optional[socket.socket] = None
        self.endianness = "<" if sys.byteorder == "little" else ">"
        self.wl_registry_id = 2
        self.callback_id = 3
        self.virtual_pointer_manager_id = 4
        self.next_id = 5
        self.current_virtual_pointer_id: Optional[int] = None
        self.protocols_found = []
        self.virtual_pointer_manager_bound = False
        self._held_buttons: set[int] = set()

        try:
            self.socket_path = self.get_socket_path()
            self.sock = self.connect_to_wayland()
        except Exception as e:
            raise WaylandConnectionError(f"Failed to connect to Wayland: {e}") from e

        # Initialize connection and bind protocols
        try:
            self.send_registry_request()
            self.send_sync_request()
            self.handle_events()

            if not self.virtual_pointer_manager_bound:
                supported = "wlroots-based (Sway, Hyprland, etc.)"
                raise WaylandProtocolError(
                    f"Protocol 'zwlr_virtual_pointer_manager_v1' not found. "
                    f"Virtual pointer clicking currently requires {supported}."
                )

            self.create_virtual_pointer()
        except Exception as e:
            self.close()
            raise e

    def __enter__(self) -> "Mouse":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()

    def is_connected(self) -> bool:
        """Check if the Wayland socket is active."""
        sock = getattr(self, "sock", None)
        return sock is not None and sock.fileno() != -1

    def close(self) -> None:
        """Release any held buttons, then safely close the Wayland socket."""
        held_buttons = getattr(self, "_held_buttons", set())
        self._held_buttons = set()

        for button_code in held_buttons:
            try:
                self._send_button_state_change(button_code, BUTTON_STATE_RELEASED)
            except WaylandConnectionError as e:
                logger.debug(f"Could not release button {hex(button_code)} on close: {e}")

        # Close socket
        sock = getattr(self, "sock", None)
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass
            finally:
                self.sock = None

    def get_socket_path(self) -> str:
        """
        Get absolute path to Wayland display socket adhering to XDG runtime directory specification.
        """
        xdg_runtime = os.getenv("XDG_RUNTIME_DIR")
        if not xdg_runtime:
            xdg_runtime = f"/run/user/{os.getuid()}"
        wayland_display = os.getenv("WAYLAND_DISPLAY", "wayland-0")
        return os.path.join(xdg_runtime, wayland_display)

    def connect_to_wayland(self) -> socket.socket:
        """Establish UNIX domain socket connection to Wayland server."""
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.socket_path)
        logger.info(f"Connected to Wayland server at {self.socket_path}")
        return sock

    def send_message(self, object_id: Optional[int], opcode: int, payload: bytes) -> None:
        """Send a Wayland wire protocol message."""
        if object_id is None or self.sock is None:
            return
        message_size = 8 + len(payload)
        message = (
            struct.pack(f"{self.endianness}IHH", object_id, opcode, message_size)
            + payload
        )
        try:
            self.sock.sendall(message)
        except (BrokenPipeError, OSError) as e:
            self.close()
            raise WaylandConnectionError(f"Wayland socket error: {e}") from e

    def send_registry_request(self) -> None:
        """Send wl_display.get_registry() request."""
        self.send_message(1, 1, struct.pack(f"{self.endianness}I", self.wl_registry_id))
        logger.debug("Sent wl_display.get_registry() request...")

    def send_sync_request(self) -> None:
        """Send wl_display.sync() request."""
        self.send_message(1, 0, struct.pack(f"{self.endianness}I", self.callback_id))
        logger.debug("Sent wl_display.sync() request...")

    def _recv_exact(self, num_bytes: int) -> Optional[bytes]:
        """Read exactly num_bytes from the socket."""
        if self.sock is None:
            return None
        buf = bytearray()
        while len(buf) < num_bytes:
            try:
                chunk = self.sock.recv(num_bytes - len(buf))
            except BlockingIOError:
                time.sleep(0.001)
                continue
            if not chunk:
                return None
            buf.extend(chunk)
        return bytes(buf)

    def receive_message(self) -> Tuple[Optional[int], Optional[int], Optional[bytes]]:
        """Receive and unpack a single Wayland wire message."""
        if self.sock is None:
            return None, None, None

        header = self.sock.recv(8)
        if not header or len(header) < 8:
            return None, None, None

        object_id, size_opcode = struct.unpack(f"{self.endianness}II", header)
        size = (size_opcode >> 16) & 0xFFFF
        opcode = size_opcode & 0xFFFF

        payload_len = size - 8
        if payload_len <= 0:
            return object_id, opcode, b""

        message_data = self._recv_exact(payload_len)
        return object_id, opcode, message_data

    def handle_events(self) -> None:
        """Process pending Wayland events until sync callback completes."""
        if self.sock is None:
            return

        self.sock.setblocking(False)
        callback_done = False

        try:
            while True:
                try:
                    result = self.receive_message()
                    if result is None or result[0] is None:
                        break

                    object_id, opcode, message_data = result
                    if message_data is None:
                        continue

                    if object_id == 1:
                        logger.debug(f"Received event from wl_display: {opcode}")

                    if object_id == self.wl_registry_id and opcode == 0:
                        global_name = struct.unpack(f"{self.endianness}I", message_data[:4])[0]
                        name_offset = 4
                        string_size = struct.unpack(
                            f"{self.endianness}I", message_data[name_offset : name_offset + 4]
                        )[0]
                        interface_name = message_data[
                            name_offset + 4 : name_offset + 4 + string_size - 1
                        ].decode("utf-8")
                        version = struct.unpack(f"{self.endianness}I", message_data[-4:])[0]

                        self.protocols_found.append(interface_name)
                        logger.debug(
                            f"Discovered global: {interface_name} (name {global_name}, version {version})"
                        )
                        if interface_name == "zwlr_virtual_pointer_manager_v1":
                            payload = (
                                struct.pack(f"{self.endianness}I", global_name)
                                + encode_wayland_string(interface_name)
                                + struct.pack(
                                    f"{self.endianness}II",
                                    version,
                                    self.virtual_pointer_manager_id,
                                )
                            )
                            self.send_message(self.wl_registry_id, 0, payload)
                            self.virtual_pointer_manager_bound = True
                            logger.info("Bound to zwlr_virtual_pointer_manager_v1")

                    elif object_id == self.callback_id and opcode == 0:
                        logger.debug("Received wl_callback.done event.")
                        callback_done = True

                except BlockingIOError:
                    if callback_done:
                        break
                    time.sleep(0.001)

        finally:
            if self.sock:
                self.sock.setblocking(True)

    def create_virtual_pointer(self) -> None:
        """Request creation of a virtual pointer object."""
        new_pointer_id = self.next_id
        self.next_id += 1
        self.send_message(
            self.virtual_pointer_manager_id,
            0,
            struct.pack(f"{self.endianness}II", 0, new_pointer_id),
        )
        self.current_virtual_pointer_id = new_pointer_id

    def send_motion_absolute(self, x: int, y: int, x_extent: int, y_extent: int) -> None:
        """
        Send motion_absolute event to virtual pointer.

        Args:
            x_extent: Total screen width.
            y_extent: Total screen height.
        """
        payload = struct.pack(f"{self.endianness}IIIII", 0, int(x), int(y), int(x_extent), int(y_extent))
        self.send_message(self.current_virtual_pointer_id, 1, payload)
        # Frame event after motion
        self.send_message(self.current_virtual_pointer_id, 4, b"")

    def _handle_optional_pointer_movement(self, x: Optional[int], y: Optional[int]) -> None:
        """
        Moves pointer to (x, y) if user provided both coordinates.
        Assumes it's only correct to provide both or neither of the coordinates.

        Args:
            x: X coordinate.
            y: Y coordinate.
        """
        if (x is None) != (y is None):
            raise ValueError("x and y must be given together")

        if x is not None:
            self.send_motion_absolute(int(x), int(y), *get_resolution())

    def _send_button_state_change(self, button_code: int, button_state: int) -> None:
        """
        Send button and frame event to virtual pointer.

        Args:
            button_code: One of the button code constants.
            button_state: 0 for released state, 1 for pressed state.
        """
        self.send_message(
            self.current_virtual_pointer_id, 2,  # button event
            struct.pack(f"{self.endianness}III",
                0,
                button_code,
                button_state
        ))
        self.send_message(self.current_virtual_pointer_id, 4, b"")  # frame

    def send_click(self, button: int) -> None:
        """
        Send button press followed by release to simulate a click

        Args:
            button: Button code constant.
        """
        self._send_button_state_change(button, BUTTON_STATE_PRESSED)
        self._send_button_state_change(button, BUTTON_STATE_RELEASED)

    @staticmethod
    def _parse_button(button: Optional[Union[str, int]]) -> Optional[int]:
        """Convert button representation to Linux evdev button code."""
        if button is None:
            return BUTTON_LEFT
        if isinstance(button, str):
            btn = button.strip().lower()
            if btn in ("left", "l"):
                return BUTTON_LEFT
            elif btn in ("right", "r"):
                return BUTTON_RIGHT
            elif btn in ("middle", "m"):
                return BUTTON_MIDDLE
            elif btn in ("nothing", "none", "move"):
                return None
            else:
                raise ValueError(
                    f"Invalid button: {button!r}. Choose 'left', 'right', 'middle', or 'nothing'."
                )
        return int(button)

    def click(self, x: int, y: int, button: Optional[Union[str, int]] = "left") -> None:
        """
        Moves the pointer to (x, y) and optionally performs a click.

        Args:
            x: X screen coordinate.
            y: Y screen coordinate.
            button: 'left', 'right', 'middle', 'nothing' (move only), or numeric button code.
        """
        width, height = get_resolution()
        self.send_motion_absolute(int(x), int(y), width, height)

        button_code = self._parse_button(button)
        if button_code is not None:
            self.send_click(button_code)

        self.send_sync_request()
        self.handle_events()

    def mouse_down(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: Optional[Union[str, int]] = "left"
    ) -> None:
        """
        Presses a button without releasing it. Optionally moves the pointer to (x, y) before pressing.
        Buttons still held when this Mouse is closed get automatically released. A process killed
        with SIGKILL skips this.

        Args:
            x, y: Absolute screen coordinates, supply both or neither.
            button: 'left', 'right', 'middle', or numeric button code.
        """
        self._handle_optional_pointer_movement(x, y)

        button_code = self._parse_button(button)

        if button_code is not None and button_code not in self._held_buttons:
            self._send_button_state_change(button_code, BUTTON_STATE_PRESSED)
            self._held_buttons.add(button_code)

        self.send_sync_request()
        self.handle_events()

    def mouse_up(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: Optional[Union[str, int]] = "left"
    ) -> None:
        """
        Releases a button. Optionally moves the pointer to (x, y) before releasing.

        Args:
            x, y: Absolute screen coordinates, supply both or neither.
            button: 'left', 'right', 'middle', or numeric button code.
        """
        self._handle_optional_pointer_movement(x, y)

        button_code = self._parse_button(button)

        if button_code is not None and button_code in self._held_buttons:
            self._send_button_state_change(button_code, BUTTON_STATE_RELEASED)
            self._held_buttons.remove(button_code)

        self.send_sync_request()
        self.handle_events()

    def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        speed: Union[str, float] = "normal",
    ) -> None:
        """
        Simulates a drag gesture from (start_x, start_y) to (end_x, end_y).

        Args:
            start_x, start_y: Beginning coordinates.
            end_x, end_y: Ending coordinates.
            speed: 'normal' (1.0s) or duration in seconds.
        """
        if isinstance(speed, str) and speed.lower() == "normal":
            duration = 1.0
        else:
            try:
                duration = float(speed)
            except (ValueError, TypeError):
                duration = 1.0

        width, height = get_resolution()

        # Move to start position
        self.send_motion_absolute(int(start_x), int(start_y), width, height)

        # Mouse down (left button)
        self._send_button_state_change(BUTTON_LEFT, BUTTON_STATE_PRESSED)

        steps = 20
        step_duration = max(0.001, duration / steps)

        for i in range(1, steps + 1):
            cur_x = int(start_x + (end_x - start_x) * i / steps)
            cur_y = int(start_y + (end_y - start_y) * i / steps)
            self.send_motion_absolute(cur_x, cur_y, width, height)
            time.sleep(step_duration)

        # Mouse up
        self._send_button_state_change(BUTTON_LEFT, BUTTON_STATE_RELEASED)

        self.send_sync_request()
        self.handle_events()

    def auto_click(
        self,
        initial_delay: float = 3.0,
        interval: float = 0.1,
        duration: float = 10.0,
        button: Union[str, int] = "left",
    ) -> None:
        """
        Repeatedly clicks at the current pointer position.

        Args:
            initial_delay: Seconds to wait before starting.
            interval: Seconds between clicks.
            duration: Total duration in seconds.
            button: 'left', 'right', 'middle', or button code.
        """
        button_code = self._parse_button(button)
        if button_code is None:
            button_code = BUTTON_LEFT

        time.sleep(max(0.0, float(initial_delay)))
        start_time = time.time()

        while time.time() - start_time < duration:
            self.send_click(button_code)
            time.sleep(max(0.001, float(interval)))

        self.send_sync_request()
        self.handle_events()

    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """
        Scrolls the mouse wheel. Optionally moves the pointer to (x, y) before scrolling.

        Args:
            clicks: The amount of scrolling to perform. Positive for up, negative for down.
            x, y: Absolute screen coordinates, supply both or neither.
        """
        clicks = -int(clicks)  # Whole wheel clicks, fractional part is truncated
                               # Change clicks sign to match PyAutoGUI's api

        self._handle_optional_pointer_movement(x, y)

        if clicks == 0:
            if x is not None:
                self.send_sync_request()
                self.handle_events()
            return

        click_to_send = 1 if clicks > 0 else -1
        value = convert_float_to_wl_fixed_t(click_to_send * WHEEL_CLICK_ANGLE)
        axis_source_payload = struct.pack(f"{self.endianness}I", 0)
        steps = abs(clicks)

        # send one discrete click per frame
        for step in range(steps):
            self.send_message(self.current_virtual_pointer_id, 5, axis_source_payload)

            # Convert time since startup to ms, mask so that it fits into a u32
            time_ms = int(time.monotonic() * 1000) & 0xFFFFFFFF

            self.send_message(self.current_virtual_pointer_id, 7,  # axis_discrete
                struct.pack(f"{self.endianness}IIii",
                time_ms,
                AXIS_VERTICAL,
                value,
                click_to_send
            ))

            self.send_message(self.current_virtual_pointer_id, 4, b"")  # frame

            if step < steps - 1:
                time.sleep(0.015)  # Add a small delay between frames

        self.send_sync_request()
        self.handle_events()


def print_usage() -> None:
    usage_text = """
Wayland Automation — Mouse Controller

Usage:
  Click (move + click):
      python -m wayland_automation.mouse_controller click <x> <y> [<button>]
      python -m wayland_automation.mouse_controller <x> <y> [<button>]

  Move only (no click):
      python -m wayland_automation.mouse_controller <x> <y> nothing

  Swipe (drag gesture):
      python -m wayland_automation.mouse_controller swipe <start_x> <start_y> <end_x> <end_y> [<speed>]

  Auto-click:
      python -m wayland_automation.mouse_controller autoclick [<delay> <interval> <duration> <button>]

  Scroll:
      python -m wayland_automation.mouse_controller scroll <clicks> [<x> <y>]

  Run built-in test:
      python -m wayland_automation.mouse_controller test

Buttons:
  left, right, middle, nothing (default: left)
"""
    print(usage_text.strip())


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1].lower() in ("-h", "--help", "help"):
        print_usage()
        sys.exit(0)

    first_arg = sys.argv[1].lower()

    if first_arg == "test":
        print("Testing Mouse controller initialization...")
        try:
            with Mouse() as ms:
                print("✓ Wayland virtual pointer initialized successfully")
                print("Testing click(100, 100, 'nothing')...")
                ms.click(100, 100, "nothing")
                print("✓ Motion test passed")
        except Exception as e:
            print(f"✗ Test failed: {e}")
            sys.exit(1)
        sys.exit(0)

    if first_arg in ("swipe", "autoclick", "click", "scroll"):
        mode = first_arg
        args = sys.argv[2:]
    elif first_arg.isdigit():
        mode = "click"
        args = sys.argv[1:]
    else:
        print_usage()
        sys.exit(1)

    with Mouse() as ms:
        if mode == "swipe":
            if len(args) not in (4, 5):
                print("Usage: python -m wayland_automation.mouse_controller swipe <x1> <y1> <x2> <y2> [<speed>]")
                sys.exit(1)
            spd = args[4] if len(args) == 5 else "normal"
            ms.swipe(int(args[0]), int(args[1]), int(args[2]), int(args[3]), spd)

        elif mode == "autoclick":
            dly = float(args[0]) if len(args) >= 1 else 3.0
            itv = float(args[1]) if len(args) >= 2 else 0.1
            dur = float(args[2]) if len(args) >= 3 else 10.0
            btn = args[3] if len(args) >= 4 else "left"
            ms.auto_click(dly, itv, dur, btn)

        elif mode == "click":
            if len(args) not in (2, 3):
                print("Usage: python -m wayland_automation.mouse_controller click <x> <y> [<button>]")
                sys.exit(1)
            btn = args[2] if len(args) == 3 else "left"
            ms.click(int(args[0]), int(args[1]), btn)

        elif mode == "scroll":
            if len(args) not in (1, 3):
                print("Usage: python -m wayland_automation.mouse_controller scroll <clicks> [<x> <y>]")
                sys.exit(1)
            clicks = int(args[0])
            x, y = map(int, args[1:]) if len(args) == 3 else (None, None)
            ms.scroll(clicks, x, y)
