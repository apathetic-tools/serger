# tests/50_core/test_find_package_root.py
"""Tests for find_package_root() common root computation."""

# we import `_` private for testing purposes only
# pyright: reportPrivateUsage=false

from pathlib import Path

import pytest

import serger.build as mod_build


def test_find_common_root_simple(tmp_path: Path) -> None:
    """Should find common root of files in same directory."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    file1 = src / "a.py"
    file2 = src / "b.py"
    file1.write_text("A = 1")
    file2.write_text("B = 2")

    file_paths = [file1, file2]

    # --- execute ---
    result = mod_build.find_package_root(file_paths)

    # --- verify ---
    assert result == src


def test_find_common_root_nested(tmp_path: Path) -> None:
    """Should find common root of files in nested directories."""
    # --- setup ---
    src = tmp_path / "src"
    sub1 = src / "sub1"
    sub2 = src / "sub2"
    sub1.mkdir(parents=True)
    sub2.mkdir(parents=True)
    file1 = sub1 / "a.py"
    file2 = sub2 / "b.py"
    file1.write_text("A = 1")
    file2.write_text("B = 2")

    file_paths = [file1, file2]

    # --- execute ---
    result = mod_build.find_package_root(file_paths)

    # --- verify ---
    assert result == src


def test_find_common_root_deeply_nested(tmp_path: Path) -> None:
    """Should find common root of deeply nested files."""
    # --- setup ---
    src = tmp_path / "src"
    deep1 = src / "a" / "b" / "c"
    deep2 = src / "x" / "y" / "z"
    deep1.mkdir(parents=True)
    deep2.mkdir(parents=True)
    file1 = deep1 / "file1.py"
    file2 = deep2 / "file2.py"
    file1.write_text("FILE1 = 1")
    file2.write_text("FILE2 = 2")

    file_paths = [file1, file2]

    # --- execute ---
    result = mod_build.find_package_root(file_paths)

    # --- verify ---
    assert result == src


def test_find_common_root_single_file(tmp_path: Path) -> None:
    """Should return parent directory for single file."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    file1 = src / "a.py"
    file1.write_text("A = 1")

    file_paths = [file1]

    # --- execute ---
    result = mod_build.find_package_root(file_paths)

    # --- verify ---
    assert result == src


def test_find_common_root_empty_list() -> None:
    """Should raise ValueError for empty file list."""
    # --- setup ---
    file_paths: list[Path] = []

    # --- execute & verify ---
    with pytest.raises(ValueError, match="no file paths provided"):
        mod_build.find_package_root(file_paths)


def test_find_common_root_different_anchors(tmp_path: Path) -> None:
    """Should handle files with different filesystem roots."""
    # --- setup ---
    # On Unix, this would be /tmp vs /usr, but we'll use tmp_path structure
    src = tmp_path / "src"
    src.mkdir()
    file1 = src / "a.py"
    file1.write_text("A = 1")
    # Create a file in a different subdirectory to simulate different roots
    other = tmp_path / "other"
    other.mkdir()
    file2 = other / "b.py"
    file2.write_text("B = 2")

    file_paths = [file1, file2]

    # --- execute ---
    result = mod_build.find_package_root(file_paths)

    # --- verify ---
    # Common root should be tmp_path (parent of both src and other)
    assert result == tmp_path
