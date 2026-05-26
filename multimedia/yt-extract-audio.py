#!/usr/bin/env python3
# This script extracts audio from a YouTube video at the highest possible quality.
# It automatically embeds metadata and the video thumbnail into the output file.
# The final audio asset is saved directly into the user's Downloads directory.

import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("❌ Error: Please provide a YouTube URL.", file=sys.stderr)
        print("Usage: yta <URL>", file=sys.stderr)
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
        "--extract-audio",
        "--audio-format",
        "best",
        "--audio-quality",
        "0",
        "--add-metadata",
        "--embed-thumbnail",
        "--output",
        output_template,
        url,
    ]

    print("🎵 Extracting audio at highest quality to ~/Downloads...")
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
