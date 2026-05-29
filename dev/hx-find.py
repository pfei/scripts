#!/usr/bin/env python3
import shutil
import subprocess
import sys


def main():
    # Verify argument presence
    if len(sys.argv) < 2:
        print("Usage: hxfind <pattern>")
        sys.exit(1)

    pattern = sys.argv[1]

    # Ensure required dependencies are in the PATH
    for cmd in ["rg", "fzf", "hx-jump"]:
        if not shutil.which(cmd):
            print(f"Error: {cmd} is not installed or not in PATH.")
            sys.exit(1)

    try:
        # 1. Run ripgrep search
        rg = subprocess.Popen(
            ["rg", "--line-number", "--no-heading", "--color=always", pattern],
            stdout=subprocess.PIPE,
            text=True,
        )

        # 2. Pipe to fzf for selection
        fzf = subprocess.Popen(
            ["fzf", "--ansi"], stdin=rg.stdout, stdout=subprocess.PIPE, text=True
        )

        # Close rg output to allow proper process termination
        rg.stdout.close()

        # 3. Retrieve the selected line
        selection = fzf.communicate()[0].strip()

        if selection:
            # Extract "file:line" part from the result (ignoring the rest)
            parts = selection.split(":")
            target = f"{parts[0]}:{parts[1]}"

            # 4. Call the bridge script
            subprocess.run(["hx-jump", target], check=True)

    except Exception as e:
        print(f"Error during search: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
