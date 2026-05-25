#!/usr/bin/env python3
# Description: Installs symlinks for public scripts into local bin path
# Usage: python3 install-symlinks.py
# Dependencies: Python 3.11+

import os
from pathlib import Path
import sys


def create_symlink(src: Path, target: Path):
    """Ensure the source is executable, then create or overwrite the symlink."""
    if not src.exists():
        print(f"⚠️ Warning: Source file missing: {src}", file=sys.stderr)
        return

    # Ensure source file is executable (chmod +x)
    current_mode = src.stat().st_mode
    src.chmod(current_mode | 0o111)

    if target.exists() or target.is_symlink():
        target.unlink()

    target.symlink_to(src)
    print(f"✅ Symlink: {target.name} -> {src.relative_to(src.parents[1])}")


def main():
    repo_root = Path(__file__).resolve().parent
    bin_dir = Path.home() / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    symlinks_to_create = {
        bin_dir / "toggle-touchpad": repo_root / "desktop" / "toggle-touchpad.py",
        bin_dir / "toggle-touchpad-click": repo_root
        / "desktop"
        / "toggle-touchpad-wrapper.py",
    }

    for target, src in symlinks_to_create.items():
        create_symlink(src, target)


if __name__ == "__main__":
    main()
