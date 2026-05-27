#!/usr/bin/env python3
import mimetypes
import os
import sys
from pathlib import Path


def get_ignore_rules():
    # Core directories and Python development caches to always skip
    ignore_rules = {
        ".git",
        ".venv",
        "venv",
        "env",
        ".pytest_cache",
        ".mypy_cache",
        "__pycache__",
        "data",
    }

    # Read .gitignore rules
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("!"):
                    continue
                ignore_rules.add(line.strip("/"))

    # Read .gitmodules to exclude submodules
    if os.path.exists(".gitmodules"):
        with open(".gitmodules", "r") as f:
            for line in f:
                if "path =" in line:
                    sub_path = line.split("=")[1].strip()
                    ignore_rules.add(sub_path.strip("/"))

    return ignore_rules


def should_ignore(target_path, ignore_rules):
    try:
        rel_path = target_path.relative_to(Path(".")).as_posix()
    except ValueError:
        rel_path = target_path.as_posix()

    if rel_path == ".":
        return False

    for rule in ignore_rules:
        if rel_path == rule or rel_path.startswith(rule + "/"):
            return True
    return False


def is_text_file(file_path):
    # 1. Prioritize dotfiles and specific config files often ignored by MIME systems
    if file_path.name in [
        ".zshrc",
        ".tmux.conf",
        ".bashrc",
        ".vimrc",
        "aliases.zsh",
        "functions.zsh",
    ] or file_path.suffix.lower() in [".conf", ".sh", ".zsh"]:
        return True

    # 2. Explicitly exclude data assets, notebook structures, and database dumps
    if file_path.suffix.lower() in [
        ".svg",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".woff",
        ".woff2",
        ".ipynb",
        ".csv",
        ".tsv",
        ".sqlite",
        ".db",
    ]:
        return False

    # 3. Guard clause: avoid reading massive text/json data dumps (> 1 MB)
    try:
        stats = file_path.stat()
        if stats.st_size > 1024 * 1024:
            return False
        if stats.st_size == 0:
            return True
    except (FileNotFoundError, PermissionError):
        return False

    # 4. Standard MIME type check
    mime, _ = mimetypes.guess_type(str(file_path))
    if mime:
        if mime.startswith("text/") or mime in [
            "application/json",
            "application/javascript",
            "application/x-sh",
        ]:
            return True

    # 5. Robust fallback: read as binary to check for null bytes (indicates binary)
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            # If null byte found, it's definitely binary
            if b"\x00" in chunk:
                return False
            return True
    except Exception:
        return False


def main():
    out_file_str = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.path.expanduser("~/Downloads/full-codebase.txt")
    )
    out_path = Path(out_file_str).resolve()
    ignore_rules = get_ignore_rules()

    with open(out_path, "w", encoding="utf-8") as out:
        for root, dirs, files in os.walk("."):
            root_path = Path(root)

            # Prune directories in-place to optimize traversal speed
            dirs[:] = [
                d
                for d in dirs
                if not should_ignore(root_path / d, ignore_rules)
                and (root_path / d).resolve() != out_path.parent
            ]

            for file in files:
                current_file_path = root_path / file
                if current_file_path.resolve() == out_path or file in [
                    "poetry.lock",
                    "package-lock.json",
                ]:
                    continue

                display_path = f"./{current_file_path.relative_to(Path('.'))}"

                if is_text_file(current_file_path):
                    out.write(f"\n\n--- FILE: {display_path} ---\n")
                    try:
                        with open(
                            current_file_path,
                            "r",
                            errors="replace",
                            encoding="utf-8",
                        ) as f:
                            out.write(f.read())
                    except Exception:
                        out.write("[error reading file]\n")
                else:
                    out.write(
                        f"\n\n--- FILE: {display_path} ---\n[binary or skipped]\n"
                    )

    print(f"Dumped to {out_path}")


if __name__ == "__main__":
    main()
