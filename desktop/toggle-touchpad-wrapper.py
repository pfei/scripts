#!/usr/bin/env python3
# Description: Wrapper to enforce DISPLAY env variable for desktop shortcuts
# Usage: python3 toggle-touchpad-wrapper.py
# Dependencies: Python 3.11+

import os
import subprocess
import sys
from pathlib import Path


def main():
    # Enforce the display environment variable for X11/MATE shortcuts
    os.environ["DISPLAY"] = ":0"

    # Target the execution script inside the user's local bin
    script_path = Path.home() / ".local" / "bin" / "toggle-touchpad"

    if not script_path.exists():
        print(f"Error: {script_path} not found.", file=sys.stderr)
        sys.exit(1)

    subprocess.run([str(script_path)], check=True)


if __name__ == "__main__":
    main()
