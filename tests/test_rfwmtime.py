#!/usr/bin/env python3
"""
Unit tests for rfwmtime.py
Run with: python -m pytest test_rfwmtime.py -v
"""

import os
import sys
from pathlib import Path

import pytest

# Ensures rfwmtime.py is importable from the same directory
sys.path.insert(0, str(Path(__file__).parent))

from utils.rfwmtime import (
    _ALREADY_PREFIXED,
    _unique_path,
    collect_directories,
    is_protected,
    process_directory,
)
import logging

# Silent logger for testing purposes
_NULL_LOGGER = logging.getLogger("test_null")
_NULL_LOGGER.addHandler(logging.NullHandler())
_NULL_LOGGER.propagate = False


# ---------------------------------------------------------------------------
# is_protected
# ---------------------------------------------------------------------------


class TestIsProtected:
    def test_root_is_protected(self):
        assert is_protected(Path("/")) is True

    def test_etc_is_protected(self):
        assert is_protected(Path("/etc")) is True

    def test_etc_subdir_is_protected(self):
        """A subdirectory inside a protected system folder must also be blocked."""
        assert is_protected(Path("/etc/subdir")) is True

    def test_home_is_protected(self):
        """The home root contains protected elements (.ssh, .config), so targeting it directly is blocked."""
        assert is_protected(Path.home()) is True

    def test_home_documents_is_protected(self):
        assert is_protected(Path.home() / "Documents") is True

    def test_tmp_is_protected(self):
        assert is_protected(Path("/tmp")) is True

    def test_safe_directory(self):
        """A directory not listed in PROTECTED_DIRS should not be blocked."""
        from unittest.mock import patch

        fake_path = Path("/mnt/totally_safe_place/my_project")
        with patch(
            "utils.rfwmtime.PROTECTED_DIRS", frozenset({Path("/etc"), Path("/tmp")})
        ):
            assert is_protected(fake_path) is False

    def test_safe_subdirectory(self):
        """A subdirectory outside any protected zones should not be blocked."""
        from unittest.mock import patch

        fake_path = Path("/mnt/totally_safe_place/sub/deep")
        with patch(
            "utils.rfwmtime.PROTECTED_DIRS", frozenset({Path("/etc"), Path("/tmp")})
        ):
            assert is_protected(fake_path) is False


# ---------------------------------------------------------------------------
# _ALREADY_PREFIXED regex
# ---------------------------------------------------------------------------


class TestAlreadyPrefixedRegex:
    @pytest.mark.parametrize(
        "name",
        [
            "2024-01-15--report.pdf",
            "2000-12-31--archive.tar.gz",
            "1999-06-01--old.txt",
        ],
    )
    def test_already_prefixed(self, name):
        assert _ALREADY_PREFIXED.match(name)

    @pytest.mark.parametrize(
        "name",
        [
            "report.pdf",
            "2024-01-report.pdf",  # Insufficient dashes
            "20240115--report.pdf",  # Missing dashes inside the date
            "2024-1-1--report.pdf",  # Missing padding zeros for month/day
            ".hidden_file",
        ],
    )
    def test_not_prefixed(self, name):
        assert not _ALREADY_PREFIXED.match(name)


# ---------------------------------------------------------------------------
# _unique_path
# ---------------------------------------------------------------------------


class TestUniquePath:
    def test_no_collision(self, tmp_path):
        candidate = tmp_path / "2024-01-01--file.txt"
        assert _unique_path(candidate) == candidate

    def test_single_collision(self, tmp_path):
        candidate = tmp_path / "2024-01-01--file.txt"
        candidate.touch()
        result = _unique_path(candidate)
        assert result == tmp_path / "2024-01-01--file_1.txt"
        assert result != candidate

    def test_multiple_collisions(self, tmp_path):
        base = tmp_path / "2024-01-01--file.txt"
        base.touch()
        (tmp_path / "2024-01-01--file_1.txt").touch()
        (tmp_path / "2024-01-01--file_2.txt").touch()
        result = _unique_path(base)
        assert result == tmp_path / "2024-01-01--file_3.txt"

    def test_no_extension(self, tmp_path):
        candidate = tmp_path / "2024-01-01--Makefile"
        candidate.touch()
        result = _unique_path(candidate)
        assert result == tmp_path / "2024-01-01--Makefile_1"


# ---------------------------------------------------------------------------
# process_directory
# ---------------------------------------------------------------------------


class TestProcessDirectory:
    def _make_file(
        self, parent: Path, name: str, mtime_ts: float | None = None
    ) -> Path:
        p = parent / name
        p.write_text("test content")
        if mtime_ts is not None:
            os.utime(p, (mtime_ts, mtime_ts))
        return p

    def test_nonexistent_directory(self, tmp_path):
        missing = tmp_path / "nonexistent"
        r, s, e = process_directory(missing, dry_run=False, logger=_NULL_LOGGER)
        assert (r, s, e) == (0, 0, 1)

    def test_empty_directory(self, tmp_path):
        r, s, e = process_directory(tmp_path, dry_run=False, logger=_NULL_LOGGER)
        assert (r, s, e) == (0, 0, 0)

    def test_renames_file(self, tmp_path):
        # mtime locked to 2024-03-15
        ts = 1710460800.0  # 2024-03-15 00:00 UTC
        self._make_file(tmp_path, "document.pdf", ts)

        r, s, e = process_directory(tmp_path, dry_run=False, logger=_NULL_LOGGER)
        assert e == 0
        assert r == 1
        renamed_files = list(tmp_path.iterdir())
        assert len(renamed_files) == 1
        assert renamed_files[0].name.startswith("2024-03-")
        assert renamed_files[0].name.endswith("--document.pdf")

    def test_skips_already_prefixed(self, tmp_path):
        self._make_file(tmp_path, "2024-01-01--already.txt")
        r, s, e = process_directory(tmp_path, dry_run=False, logger=_NULL_LOGGER)
        assert (r, s, e) == (0, 1, 0)

    def test_skips_hidden_files(self, tmp_path):
        self._make_file(tmp_path, ".hidden")
        r, s, e = process_directory(tmp_path, dry_run=False, logger=_NULL_LOGGER)
        assert (r, s, e) == (0, 0, 0)
        assert (tmp_path / ".hidden").exists()

    def test_dry_run_does_not_rename(self, tmp_path):
        self._make_file(tmp_path, "report.docx")
        r, s, e = process_directory(tmp_path, dry_run=True, logger=_NULL_LOGGER)
        assert r == 1
        assert e == 0
        # The original file must remain untouched
        assert (tmp_path / "report.docx").exists()

    def test_handles_collision(self, tmp_path):
        ts = 1710460800.0  # 2024-03-15
        self._make_file(tmp_path, "doc.txt", ts)
        # Pre-create the target file name to trigger a naming collision
        (tmp_path / "2024-03-15--doc.txt").write_text("existing")
        r, s, e = process_directory(tmp_path, dry_run=False, logger=_NULL_LOGGER)
        assert e == 0
        assert r == 1
        # The newly resolved file with the numeric suffix must exist
        assert (tmp_path / "2024-03-15--doc_1.txt").exists()

    def test_multiple_files(self, tmp_path):
        ts = 1710460800.0
        for name in ["a.txt", "b.txt", "c.txt"]:
            self._make_file(tmp_path, name, ts)
        r, s, e = process_directory(tmp_path, dry_run=False, logger=_NULL_LOGGER)
        assert (r, s, e) == (3, 0, 0)
        for f in tmp_path.iterdir():
            assert _ALREADY_PREFIXED.match(f.name)


# ---------------------------------------------------------------------------
# collect_directories
# ---------------------------------------------------------------------------


class TestCollectDirectories:
    def test_includes_base(self, tmp_path):
        dirs = collect_directories(tmp_path, max_depth=None)
        assert tmp_path in dirs

    def test_includes_subdirs(self, tmp_path):
        sub = tmp_path / "subdirectory"
        sub.mkdir()
        dirs = collect_directories(tmp_path, max_depth=None)
        assert sub in dirs

    def test_excludes_hidden_dirs(self, tmp_path):
        (tmp_path / ".git").mkdir()
        dirs = collect_directories(tmp_path, max_depth=None)
        assert tmp_path / ".git" not in dirs

    def test_max_depth_zero(self, tmp_path):
        (tmp_path / "sub").mkdir()
        dirs = collect_directories(tmp_path, max_depth=0)
        assert dirs == [tmp_path]

    def test_max_depth_one(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        deep = sub / "deep"
        deep.mkdir()
        dirs = collect_directories(tmp_path, max_depth=1)
        assert sub in dirs
        assert deep not in dirs

    def test_sorted_output(self, tmp_path):
        for name in ["z_dir", "a_dir", "m_dir"]:
            (tmp_path / name).mkdir()
        dirs = collect_directories(tmp_path, max_depth=None)
        assert dirs == sorted(dirs)


# ---------------------------------------------------------------------------
# Integration Scenario
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_full_run_recursive(self, tmp_path):
        """Complete renaming operation across two directory levels."""
        ts = 1710460800.0  # 2024-03-15
        sub = tmp_path / "subdir"
        sub.mkdir()

        for d, name in [(tmp_path, "root.txt"), (sub, "child.md")]:
            p = d / name
            p.write_text("x")
            os.utime(p, (ts, ts))

        all_dirs = collect_directories(tmp_path, max_depth=None)
        total_r = total_e = 0
        for d in all_dirs:
            r, _, e = process_directory(d, dry_run=False, logger=_NULL_LOGGER)
            total_r += r
            total_e += e

        assert total_r == 2
        assert total_e == 0
        assert (tmp_path / "2024-03-15--root.txt").exists()
        assert (sub / "2024-03-15--child.md").exists()
