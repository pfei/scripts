#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


def main():
    # Check if a file:line argument is provided
    if len(sys.argv) < 2:
        print("Usage: hx-jump <file:line>")
        sys.exit(1)

    target = sys.argv[1]
    # Split the file path and the line number
    file_path, line = target.split(":")

    # Get a list of all active tmux panes
    # Format: PANE_ID CURRENT_COMMAND
    try:
        panes = subprocess.check_output(
            ["tmux", "list-panes", "-a", "-F", "#{pane_id} #{pane_current_command}"],
            text=True,
        )
    except subprocess.CalledProcessError:
        print("Error: tmux is not active or unreachable.")
        sys.exit(1)

    # Search for the pane ID running 'hx'
    target_pane = None
    for line_pane in panes.splitlines():
        if "hx" in line_pane:
            target_pane = line_pane.split()[0]
            break

    if target_pane:
        # Send commands to the found Helix instance
        # :open opens the file, then jump to the requested line
        subprocess.run(
            ["tmux", "send-keys", "-t", target_pane, ":open " + file_path, "Enter"],
            check=True,
        )
        subprocess.run(
            ["tmux", "send-keys", "-t", target_pane, ":" + line, "Enter"], check=True
        )
        # Switch focus to that pane
        subprocess.run(["tmux", "select-pane", "-t", target_pane], check=True)
    else:
        # If Helix is not running in tmux, launch a standard instance
        print("Helix instance not found in tmux. Opening directly...")
        subprocess.run(["hx", f"{file_path}:{line}"])


if __name__ == "__main__":
    main()
