#!/usr/bin/env python3
# This script toggles the system touchpad state (enabled/disabled).
# It dynamically detects the touchpad device ID using xinput and regular expressions.
# Designed to be mapped to a keyboard shortcut for quick hardware control.

import re
import subprocess
import sys


def run_command(cmd: list[str]) -> str:
    """Run a system command and return its stdout cleaned up."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def main():
    try:
        # 1. Get the full xinput architecture list
        list_output = run_command(["xinput", "list"])

        # 2. Parse the list directly in Python to extract the numeric ID
        # Matches lines containing our keywords and captures the id=XX part
        match = re.search(
            r"(?:DELL\w+|DLL\w+|touchpad|glidepoint).*id=(\d+)",
            list_output,
            re.IGNORECASE,
        )

        if not match:
            print(
                "Error: No touchpad device detected via xinput.",
                file=sys.stderr,
            )
            sys.exit(1)

        # We now have a pure integer string (e.g., "10")
        device_id = match.group(1)

        # 3. Get current state (1 = enabled, 0 = disabled)
        props_output = run_command(["xinput", "list-props", device_id])
        state_match = re.search(
            r"Device Enabled.*\s([01])$", props_output, re.MULTILINE
        )

        if not state_match:
            print(
                f"Error: Could not parse state for device ID {device_id}",
                file=sys.stderr,
            )
            sys.exit(1)

        current_state = state_match.group(1)

        # 4. Toggle the state safely using the pure integer ID
        if current_state == "1":
            subprocess.run(["xinput", "--disable", device_id], check=True)
        else:
            subprocess.run(["xinput", "--enable", device_id], check=True)

    except subprocess.CalledProcessError as e:
        print(f"System error occurred: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
