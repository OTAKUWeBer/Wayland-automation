import os
import socket
import struct
import sys
import time
from wayland_automation.utils.screen_resolution import get_resolution

# Configure logging
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Define button constants
BUTTON_LEFT = 0x110
BUTTON_RIGHT = 0x111

class WaylandProtocolError(Exception):
    """Exception raised when a required Wayland protocol is not available."""
    pass

class WaylandConnectionError(Exception):
    """Exception raised when connection to Wayland fails."""
    pass

def encode_wayland_string(s: str) -> bytes:
    if s is None:
        return struct.pack("<I", 0)
    encoded = s.encode("utf-8") + b"\x00"
    length = len(encoded)
    padding_size = (4 - (length % 4)) % 4
    padding = b"\x00" * padding_size
    return struct.pack("<I", length) + encoded + padding

class Mouse:
    def __init__(self):
        try:
            self.socket_path = self.get_socket_path()
            self.sock = self.connect_to_wayland()
        except Exception as e:
            raise WaylandConnectionError(f"Failed to connect to Wayland: {e}")

        self.endianness = "<" if sys.byteorder == "little" else ">"
        self.wl_registry_id = 2
        self.callback_id = 3
        self.virtual_pointer_manager_id = 4
        self.next_id = 5  # Start assigning new IDs from here
        self.current_virtual_pointer_id = None
        
        self.protocols_found = []
        self.virtual_pointer_manager_bound = False

        # Perform initial setup
        try:
            self.send_registry_request()
            self.send_sync_request()
            self.handle_events()  # Binds the virtual pointer manager
            
            if not self.virtual_pointer_manager_bound:
                supported_compositors = "wlroots-based (Sway, Hyprland, etc.)"
                raise WaylandProtocolError(
                    f"Protocol 'zwlr_virtual_pointer_manager_v1' not found. "
                    f"This library currently requires {supported_compositors}. "
                    "KDE Plasma support is planned for version 6.5 via 'pointer-warp-v1'."
                )
                
            self.create_virtual_pointer()
        except Exception as e:
            if self.sock:
                self.sock.close()
            raise e

    def get_socket_path(self):
        wayland_display = os.getenv("WAYLAND_DISPLAY", "wayland-0")
        return f"/run/user/{os.getuid()}/{wayland_display}"

    def connect_to_wayland(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.socket_path)
        logger.info(f"Connected to Wayland server at {self.socket_path}")
        return sock

    def send_message(self, object_id, opcode, payload):
        if object_id is None:
            return
        message_size = 8 + len(payload)
        message = (
            struct.pack(f"{self.endianness}IHH", object_id, opcode, message_size)
            + payload
        )
        try:
            self.sock.sendall(message)
        except BrokenPipeError:
            logger.error("SIGPIPE detected: Wayland connection closed unexpectedly.")
            sys.exit(1)

    def send_registry_request(self):
        self.send_message(1, 1, struct.pack(f"{self.endianness}I", self.wl_registry_id))
        logger.debug("Sent wl_display.get_registry() request...")

    def send_sync_request(self):
        self.send_message(1, 0, struct.pack(f"{self.endianness}I", self.callback_id))
        logger.debug("Sent wl_display.sync() request...")

    def receive_message(self):
        header = self.sock.recv(8)
        if len(header) < 8:
            return None, None, None
        object_id, size_opcode = struct.unpack(f"{self.endianness}II", header)
        size = (size_opcode >> 16) & 0xFFFF
        opcode = size_opcode & 0xFFFF
        message_data = self.sock.recv(size - 8)
        return object_id, opcode, message_data

    def handle_events(self):
        # Set socket to non-blocking to drain all available messages
        self.sock.setblocking(False)
        callback_done = False
        
        try:
            while True:
                try:
                    result = self.receive_message()
                    if result is None or result[0] is None:
                        break
                    object_id, opcode, message_data = result

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
                    # No more messages available
                    if callback_done:
                        break
                    # If callback not done yet, wait a bit and retry
                    time.sleep(0.001)
                    
        finally:
            # Restore blocking mode
            self.sock.setblocking(True)

    def create_virtual_pointer(self):
        new_pointer_id = self.next_id
        self.next_id += 1
        self.send_message(
            self.virtual_pointer_manager_id,
            0,
            struct.pack(f"{self.endianness}II", 0, new_pointer_id),
        )
        self.current_virtual_pointer_id = new_pointer_id

    def send_motion_absolute(self, x, y, x_extent, y_extent):
        payload = struct.pack(f"{self.endianness}IIIII", 0, x, y, x_extent, y_extent)
        self.send_message(self.current_virtual_pointer_id, 1, payload)
        # Send frame event after motion
        self.send_message(self.current_virtual_pointer_id, 4, b'')
        
    def send_click(self, button):
        # Send press then release events for the given button, each followed by a frame.
        self.send_message(
            self.current_virtual_pointer_id, 
            2, 
            struct.pack(f"{self.endianness}III", 0, button, 1)
        )
        self.send_message(self.current_virtual_pointer_id, 4, b'')  # Frame after press
        self.send_message(
            self.current_virtual_pointer_id, 
            2, 
            struct.pack(f"{self.endianness}III", 0, button, 0)
        )
        self.send_message(self.current_virtual_pointer_id, 4, b'')  # Frame after release

    def click(self, x, y, button=None):
        """
        Moves the pointer to (x, y) and, if button is specified, performs a click.
        """
        height, width = get_resolution()
        self.send_motion_absolute(x, y, int(height), int(width))
        
        if button is not None:
            if isinstance(button, str):
                btn = button.lower()
                if btn == "left":
                    button_code = BUTTON_LEFT
                elif btn == "right":
                    button_code = BUTTON_RIGHT
                elif btn == "nothing":
                    return
                else:
                    print("Invalid button string. Use 'left', 'right', or 'nothing'.")
                    return
            else:
                button_code = int(button)
            self.send_click(button_code)

        self.send_sync_request()
        self.handle_events()

    def swipe(self, start_x, start_y, end_x, end_y, speed="normal"):
        """
        Simulates a swipe (drag) gesture from (start_x, start_y) to (end_x, end_y).

        The speed parameter controls the duration of the swipe.
        If speed is "normal", a default duration of 1.0 second is used;
        otherwise, speed is interpreted as a numeric duration in seconds.
        """
        try:
            duration = float(speed) if not isinstance(speed, str) or speed.lower() != "normal" else 1.0
        except ValueError:
            print("Invalid speed value. Using default speed of 1.0 second.")
            duration = 1.0

        height, width = get_resolution()

        # Move pointer to start position
        self.send_motion_absolute(start_x, start_y, int(height), int(width))
        # Send press (simulate left button down)
        self.send_message(
            self.current_virtual_pointer_id, 
            2, 
            struct.pack(f"{self.endianness}III", 0, BUTTON_LEFT, 1)
        )
        self.send_message(self.current_virtual_pointer_id, 4, b'')  # Frame after press

        steps = 20
        step_duration = duration / steps

        # Gradually move pointer from start to end
        for i in range(1, steps + 1):
            x = int(start_x + (end_x - start_x) * i / steps)
            y = int(start_y + (end_y - start_y) * i / steps)
            self.send_motion_absolute(x, y, int(height), int(width))
            time.sleep(step_duration)

        # Send release (simulate left button up)
        self.send_message(
            self.current_virtual_pointer_id, 
            2, 
            struct.pack(f"{self.endianness}III", 0, BUTTON_LEFT, 0)
        )
        self.send_message(self.current_virtual_pointer_id, 4, b'')  # Frame after release
        self.send_sync_request()
        self.handle_events()

    def auto_click(self, initial_delay=3.0, interval=0.1, duration=10.0, button="left"):
        """
        Waits for `initial_delay` seconds, then repeatedly clicks at the current pointer
        position every `interval` seconds for a total of `duration` seconds.
        The button can be specified as 'left', 'right', or a numeric code.
        """
        print(f"Waiting {initial_delay} seconds before starting auto-click...")
        time.sleep(initial_delay)
        start_time = time.time()
        # Determine the button code from the parameter
        if isinstance(button, str):
            btn = button.lower()
            if btn == "left":
                button_code = BUTTON_LEFT
            elif btn == "right":
                button_code = BUTTON_RIGHT
            else:
                print("Invalid button string. Use 'left' or 'right'. Defaulting to left.")
                button_code = BUTTON_LEFT
        else:
            button_code = int(button)

        while time.time() - start_time < duration:
            self.send_click(button_code)
            time.sleep(interval)
        # Final synchronization of events after auto-click
        self.send_sync_request()
        self.handle_events()

def print_usage():
    usage_text = """
Usage:
  For click (default mode): 
      python mouse_controller.py <x> <y> [<button>]
  For explicit click mode: 
      python mouse_controller.py click <x> <y> [<button>]
  For swipe: 
      python mouse_controller.py swipe <start_x> <start_y> <end_x> <end_y> [<speed>]
  For auto-click: 
      python mouse_controller.py autoclick [<initial_delay> <interval> <duration> <button>]
"""
    print(usage_text.strip())

if __name__ == "__main__":
    # Check if running in test mode (no arguments or "test" argument)
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1].lower() == "test"):
        print("Running in test mode...")
        print("Initializing Mouse controller...")
        
        try:
            ms = Mouse()
            print("✓ Mouse controller initialized successfully")
            
            # Test 1: Simple click at position (100, 100)
            print("\nTest 1: Clicking at position (100, 100) with left button")
            ms.click(100, 100, "left")
            print("✓ Click test completed")
            
            # Test 2: Move without clicking
            print("\nTest 2: Moving to position (200, 200) without clicking")
            ms.click(200, 200, "nothing")
            print("✓ Move test completed")
            
            # Test 3: Right click
            print("\nTest 3: Right clicking at position (150, 150)")
            ms.click(150, 150, "right")
            print("✓ Right click test completed")
            
            print("\n✓ All tests passed!")
            
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        sys.exit(0)
    
    # Original command-line interface
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    # Determine the mode. If the first argument is a digit, assume click mode.
    first_arg = sys.argv[1].lower()
    if first_arg in ["swipe", "autoclick", "click"]:
        mode = first_arg
        args = sys.argv[2:]
    else:
        # Default to click mode if not explicitly specified
        mode = "click"
        args = sys.argv[1:]

    ms = Mouse()

    if mode == "swipe":
        if len(args) not in [4, 5]:
            print("Usage: python mouse_controller.py swipe <start_x> <start_y> <end_x> <end_y> [<speed>]")
            sys.exit(1)
        try:
            start_x = int(args[0])
            start_y = int(args[1])
            end_x = int(args[2])
            end_y = int(args[3])
        except ValueError:
            print("start_x, start_y, end_x, and end_y must be integers.")
            sys.exit(1)
        speed = args[4] if len(args) == 5 else "normal"
        ms.swipe(start_x, start_y, end_x, end_y, speed)

    elif mode == "autoclick":
        # Default parameters for auto-click
        initial_delay = 3.0
        interval = 0.1
        duration = 10.0
        button = "left"
        if len(args) >= 1:
            try:
                initial_delay = float(args[0])
            except ValueError:
                print("Initial delay must be a number. Using default of 3 seconds.")
        if len(args) >= 2:
            try:
                interval = float(args[1])
            except ValueError:
                print("Interval must be a number. Using default of 0.1 seconds.")
        if len(args) >= 3:
            try:
                duration = float(args[2])
            except ValueError:
                print("Duration must be a number. Using default of 10 seconds.")
        if len(args) == 4:
            button = args[3]
        ms.auto_click(initial_delay, interval, duration, button)

    elif mode == "click":
        if len(args) not in [2, 3]:
            print("Usage: python mouse_controller.py click <x> <y> [<button>]")
            sys.exit(1)
        try:
            x = int(args[0])
            y = int(args[1])
        except ValueError:
            print("x and y must be integers.")
            sys.exit(1)
        button = args[2] if len(args) == 3 else None
        ms.click(x, y, button)
