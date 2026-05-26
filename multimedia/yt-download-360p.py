#!/usr/bin/env python3
# This script downloads a YouTube video in a lightweight 360p resolution.
# It automatically retrieves authentication cookies from the Chrome browser.
# Ideal for saving bandwidth or local storage while archiving video content.

import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("❌ Error: Please provide a YouTube URL.", file=sys.stderr)
        print("Usage: bv360 <URL>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    output_template = str(Path.home() / "Downloads" / "%(title)s [%(id)s].%(ext)s")

    # Dynamically find the isolated yt-dlp binary within the current virtualenv
    ytdlp_bin = Path(sys.executable).parent / "yt-dlp"

    # Fallback to system-wide binary if running outside a venv
    if not ytdlp_bin.exists():
        ytdlp_bin = Path("yt-dlp")

    cmd = [
        os.fspath(ytdlp_bin),
        "--cookies-from-browser",
        "chrome",
        "-f",
        "bestvideo[height<=360]+bestaudio/best[height<=360]",
        "--output",
        output_template,
        url,
    ]

    print("🚀 Downloading video in light 360p format to ~/Downloads...")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(
            f"❌ Error: yt-dlp execution failed with exit code {e.returncode}.",
            file=sys.stderr,
        )
        sys.exit(1)
    except FileNotFoundError:
        print(
            "❌ Error: 'yt-dlp' dependency is missing. Please install it first.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    import os

    main()
