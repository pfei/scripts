#!/usr/bin/env python3
# Description: Automated installer. Detects pyenv/system python,
#              bootstraps a conditional local virtual environment,
#              updates dependencies and maps binaries via crisp shell wrappers.
# Usage: ./setup.py

import subprocess
from pathlib import Path
import sys
import os
import shutil


def get_project_python() -> str:
    """Detects if pyenv is active or falls back to the current active Python executable."""
    return sys.executable


def setup_virtualenv(repo_root: Path) -> Path:
    """Conditionally creates a local .venv and updates packages only if needed."""
    venv_dir = repo_root / ".venv"
    venv_python = venv_dir / "bin" / "python"
    requirements_file = repo_root / "requirements.txt"

    # 1. Conditional creation of the virtual environment
    if not venv_dir.exists():
        print("📦 Local virtual environment not found. Bootstrapping '.venv'...")
        project_python = get_project_python()
        subprocess.run([project_python, "-m", "venv", str(venv_dir)], check=True)
        print("✅ Virtual environment initialized successfully.")
    else:
        print("✨ Existing local '.venv' detected. Skipping creation.")

    # 2. Installation and update of dependencies
    if requirements_file.exists():
        print("⚡ Checking and syncing dependencies from requirements.txt...")
        # Upgrade pip first inside the isolated environment safely
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        # Install or update required packages
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", str(requirements_file)],
            check=True,
        )

    return venv_python


def create_executable_wrapper(src_script: Path, target_link: Path, venv_python: Path):
    """Generates a zero-overhead shell wrapper pointing directly to the project's venv."""
    if not src_script.exists():
        print(f"⚠️ Warning: Source file missing: {src_script}", file=sys.stderr)
        return

    # Ensure the script itself is executable
    src_script.chmod(src_script.stat().st_mode | 0o111)

    # Wrapper strategy: transparent execution via the strict venv interpreter
    wrapper_content = f'#!/bin/sh\nexec "{venv_python}" "{src_script}" "$@"\n'

    try:
        if target_link.exists() or target_link.is_symlink():
            target_link.unlink()

        target_link.write_text(wrapper_content)
        target_link.chmod(0o755)  # Executable wrapper
        print(
            f"🔹 Command mapped: {target_link.name} -> {src_script.relative_to(src_script.parents[1])}"
        )
    except Exception as e:
        print(f"❌ Failed to map command {target_link.name}: {e}", file=sys.stderr)


def setup_systemd_services(repo_root: Path, is_headless: bool):
    """Manages systemd user services for desktop environments (like laptop battery monitoring)."""
    if is_headless:
        print("\n⏭️  Headless environment: Skipping desktop systemd user services.")
        return

    service_src = repo_root / "services" / "battery-monitor.service"
    if not service_src.exists():
        return

    print("\n⚙️  Deploying systemd user services...")
    systemd_user_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_user_dir.mkdir(parents=True, exist_ok=True)

    target_service = systemd_user_dir / service_src.name

    try:
        if target_service.exists() or target_service.is_symlink():
            target_service.unlink()

        shutil.copy(str(service_src), str(target_service))
        print(f"✅ Service file installed: ~/.config/systemd/user/{service_src.name}")

        # Reload systemd user manager and enable the service
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "--user", "enable", service_src.name], check=True)
        print(
            f"🔔 Service '{service_src.name}' successfully enabled for this user session."
        )
    except Exception as e:
        print(f"❌ Failed to configure systemd service: {e}", file=sys.stderr)


def main():
    repo_root = Path(__file__).resolve().parent
    bin_dir = Path.home() / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    # Detect headless environment (Server without graphical display server)
    is_headless = not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    print("🚀 Starting repository synchronization process...")

    # Run the robust isolation setup
    venv_python = setup_virtualenv(repo_root)

    # Centralized configuration mapping
    commands_to_install = {
        bin_dir / "toggle-touchpad": repo_root / "desktop" / "toggle-touchpad.py",
        bin_dir / "toggle-touchpad-click": repo_root
        / "desktop"
        / "toggle-touchpad-wrapper.py",
        bin_dir / "bv360": repo_root / "multimedia" / "yt-download-360p.py",
        bin_dir / "yta": repo_root / "multimedia" / "yt-extract-audio.py",
        bin_dir / "battery_monitor": repo_root / "services" / "battery-monitor.py",
    }

    print("\n⚙️  Deploying binary wrappers to target bin path...")
    for target, src in commands_to_install.items():
        create_executable_wrapper(src, target, venv_python)

    # Conditional systemd configurations based on host environment properties
    setup_systemd_services(repo_root, is_headless)

    print("\n🎉 Setup complete. All tools are isolated and ready to use globally!")


if __name__ == "__main__":
    main()
