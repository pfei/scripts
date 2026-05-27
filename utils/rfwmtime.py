#!/usr/bin/env python3
"""
rfwmtime – Rename Files With Modification Time prefix.

Renames files in a directory (and its subdirectories) by adding
their last modification date as a YYYY-MM-DD-- prefix.

Usage:
    python rfwmtime.py [options] <directory>

Options:
    --dry-run        Show renames without applying them
    --no-recurse     Process only the root directory (no subfolders)
    --yes            Automatically confirm without interactive prompt
    --log <file>     Also write the output to a log file
    --max-depth <n>  Maximum recursion depth (default: unlimited)
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Protected directories: neither the target nor any of its parents must match
# ---------------------------------------------------------------------------
PROTECTED_DIRS: frozenset[Path] = frozenset(
    {
        Path("/"),
        Path("/bin"),
        Path("/sbin"),
        Path("/usr"),
        Path("/etc"),
        Path("/lib"),
        Path("/lib64"),
        Path("/boot"),
        Path("/dev"),
        Path("/proc"),
        Path("/sys"),
        Path("/run"),
        Path("/tmp"),
        Path("/var"),
        Path("/opt"),
        Path("/root"),
        Path("/srv"),
        Path.home() / ".local",
        Path.home() / ".config",
        Path.home() / ".ssh",
        Path.home() / "src",
        Path.home() / "Documents",
        Path.home() / "Desktop",
        Path.home() / "Pictures",
        Path.home() / "Music",
        Path.home() / "Videos",
        Path.home() / "Library",  # macOS
    }
)

# Regex: filename already prefixed by YYYY-MM-DD--
_ALREADY_PREFIXED = re.compile(r"^\d{4}-\d{2}-\d{2}--")


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


def _resolve_safe(path: Path) -> Path | None:
    """Resolves the absolute path; returns None if inaccessible."""
    try:
        return path.resolve(strict=False)
    except (OSError, RuntimeError):
        return None


def is_protected(path: Path) -> bool:
    """
    Returns True if *path* is a protected directory, is inside
    a protected directory, or contains a protected directory.
    """
    resolved = _resolve_safe(path)
    if resolved is None:
        return True  # Cannot resolve -> deny access as a precaution

    # Base safety: explicit match or targeting an ancestor of a protected dir
    for protected in PROTECTED_DIRS:
        p = _resolve_safe(protected)
        if p is None:
            return True
        if resolved == p:
            return True
        # path contains a protected directory (e.g. targeting /home/pierre blocks if Documents is inside)
        if p.is_relative_to(resolved):
            return True
        # path is inside a protected directory (e.g. targeting /etc/subdir blocks because of /etc)
        # We skip this check if the protected folder is the system root '/' to avoid locking the whole drive.
        if p != Path("/") and resolved.is_relative_to(p):
            return True

    return False


# ---------------------------------------------------------------------------
# Collision resolution
# ---------------------------------------------------------------------------


def _unique_path(candidate: Path) -> Path:
    """
    If *candidate* already exists, appends a numeric suffix (_1, _2...)
    before the extension until an available filename is found.
    """
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    parent = candidate.parent
    counter = 1
    while True:
        new_candidate = parent / f"{stem}_{counter}{suffix}"
        if not new_candidate.exists():
            return new_candidate
        counter += 1


# ---------------------------------------------------------------------------
# Directory processing
# ---------------------------------------------------------------------------


def process_directory(
    target_dir: Path,
    *,
    dry_run: bool,
    logger: logging.Logger,
) -> tuple[int, int, int]:
    """
    Renames regular files in *target_dir*.

    Returns (renamed, skipped, errors).
    """
    renamed = skipped = errors = 0

    if not target_dir.is_dir():
        logger.error("Directory not found or inaccessible: %s", target_dir)
        return 0, 0, 1

    logger.info("---")
    logger.info("📂 Processing: %s", target_dir)
    logger.info("---")

    try:
        entries = list(target_dir.iterdir())
    except PermissionError:
        logger.error("Permission denied: %s", target_dir)
        return 0, 0, 1

    files = sorted(f for f in entries if f.is_file() and not f.name.startswith("."))

    if not files:
        logger.info("   No files to rename in: %s", target_dir)
        return 0, 0, 0

    for file_path in files:
        name = file_path.name

        if _ALREADY_PREFIXED.match(name):
            logger.info("   ⏭ Already prefixed, skipped: %s", name)
            skipped += 1
            continue

        try:
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            date_str = mtime.strftime("%Y-%m-%d")
        except OSError as exc:
            logger.error("   ✗ Failed to read mtime for '%s': %s", name, exc)
            errors += 1
            continue

        new_name = f"{date_str}--{name}"
        new_path = _unique_path(target_dir / new_name)

        # Warning if collision resolved by numeric suffix
        if new_path.name != new_name:
            logger.warning(
                "   ⚠ Collision detected for '%s' → renamed to '%s'",
                new_name,
                new_path.name,
            )

        if dry_run:
            logger.info("   [DRY-RUN] '%s'  →  '%s'", name, new_path.name)
            renamed += 1
            continue

        logger.info("   ✓ '%s'  →  '%s'", name, new_path.name)
        try:
            file_path.rename(new_path)
            renamed += 1
        except OSError as exc:
            logger.error("   ✗ Failed to rename '%s': %s", name, exc)
            errors += 1

    logger.info("---")
    logger.info("✅ Finished: %s", target_dir)
    return renamed, skipped, errors


# ---------------------------------------------------------------------------
# Directory collection
# ---------------------------------------------------------------------------


def collect_directories(base: Path, *, max_depth: int | None) -> list[Path]:
    """
    Returns the sorted list of directories to process (including base),
    respecting max_depth and ignoring hidden folders.

    Uses os.walk with pruning (topdown=True) to avoid descending beyond
    max_depth — unlike rglob which scans the entire tree before filtering.
    """
    import os

    logger = logging.getLogger("rfwmtime")
    dirs: list[Path] = [base]

    try:
        for root, subdirs, _ in os.walk(base, topdown=True, onerror=None):
            root_path = Path(root)
            current_depth = len(root_path.relative_to(base).parts)

            # Prune hidden directories (in-place modification for os.walk)
            subdirs[:] = [d for d in subdirs if not d.startswith(".")]

            # If max depth is reached, do not descend any further
            if max_depth is not None and current_depth >= max_depth:
                subdirs.clear()
                continue

            for d in subdirs:
                dirs.append(root_path / d)

    except PermissionError:
        logger.error("Permission denied while scanning: %s", base)

    return sorted(dirs)


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------


def setup_logging(log_file: str | None) -> logging.Logger:
    logger = logging.getLogger("rfwmtime")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(message)s")

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler (optional)
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s  %(message)s"))
        logger.addHandler(fh)

    return logger


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="rfwmtime",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "directory",
        nargs="?",
        help="Root directory to process.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate renames without modifying files.",
    )
    parser.add_argument(
        "--no-recurse",
        action="store_true",
        help="Process only the root directory.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Bypass interactive confirmation prompt.",
    )
    parser.add_argument(
        "--log",
        metavar="FILE",
        help="Log file where output will be written.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        metavar="N",
        help="Maximum recursion depth.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logger = setup_logging(args.log)

    # --- Mandatory argument validation ---
    if not args.directory:
        logger.error(
            "Error: please provide the path to the directory to process.\n"
            "Example: rfwmtime /path/to/my/folder"
        )
        sys.exit(1)

    base_dir = Path(args.directory).expanduser().resolve()

    if not base_dir.exists():
        logger.error("Error: directory '%s' does not exist.", base_dir)
        sys.exit(1)

    if not base_dir.is_dir():
        logger.error("Error: '%s' is not a directory.", base_dir)
        sys.exit(1)

    # --- Security check ---
    if is_protected(base_dir):
        logger.error(
            "❌ Protected or system directory: '%s'. Operation aborted.", base_dir
        )
        sys.exit(2)

    # --- Directory collection ---
    if args.no_recurse:
        all_dirs = [base_dir]
    else:
        all_dirs = collect_directories(base_dir, max_depth=args.max_depth)

    # --- Summary before action ---
    mode_label = "[DRY-RUN] " if args.dry_run else ""
    logger.info(
        "🚀 %sStarting from: %s (%d directory(ies) to process)",
        mode_label,
        base_dir,
        len(all_dirs),
    )
    logger.info("=" * 60)

    # --- Interactive confirmation ---
    if not args.dry_run and not args.yes:
        try:
            answer = (
                input(f"⚠️  Rename files in {len(all_dirs)} directory(ies)? [y/N] ")
                .strip()
                .lower()
            )
        except (EOFError, KeyboardInterrupt):
            logger.info("\nCancelled.")
            sys.exit(0)
        if answer not in {"y", "yes"}:
            logger.info("Cancelled.")
            sys.exit(0)

    # --- Processing ---
    total_renamed = total_skipped = total_errors = 0

    for subdir in all_dirs:
        r, s, e = process_directory(subdir, dry_run=args.dry_run, logger=logger)
        total_renamed += r
        total_skipped += s
        total_errors += e

    # --- Final summary ---
    bytes_label = f"{total_renamed} file(s)" + (" (simulation)" if args.dry_run else "")
    logger.info("=" * 60)
    logger.info(
        "✨ Finished — %s renamed, %d skipped, %d error(s).",
        bytes_label,
        total_skipped,
        total_errors,
    )

    if total_errors:
        sys.exit(3)


if __name__ == "__main__":
    main()
