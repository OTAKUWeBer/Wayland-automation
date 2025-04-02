import subprocess
import re

def get_resolution():
    try:
        output = subprocess.run(["wayland-info"], capture_output=True, text=True, check=True)
        match = re.search(r"width: (\d+) px, height: (\d+) px", output.stdout)
        if match:
            return match.group(1), match.group(2)
        else:
            return "Resolution not found"
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"

if __name__ == "__main__":
    print(get_resolution())