import shutil
import sys

def check_system_dependencies():
    for cmd in ['wtype', 'wayland-info']:
        if shutil.which(cmd) is None:
            sys.stderr.write(
                f"WARNING: '{cmd}' is not installed. Please install it to use all features of Wayland Automation.\n"
            )

def main():
    check_system_dependencies()
    # Your existing main logic goes here
    print("Starting Wayland Automation...")
    # Possibly route to mouse_controller, keyboard_controller, etc.

if __name__ == "__main__":
    main()
