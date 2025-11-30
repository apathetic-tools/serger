# tests/50_core/test_extract_version.py
"""Tests for extract_version function."""

from pathlib import Path

import serger.stitch as mod_stitch


def test_extract_version_from_valid_file(tmp_path: Path) -> None:
    """Should extract version from valid pyproject.toml."""
    path = tmp_path / "pyproject.toml"
    path.write_text('version = "1.2.3"\n')

    version = mod_stitch.extract_version(path)
    assert version == "1.2.3"


def test_extract_version_missing_file() -> None:
    """Should return 'unknown' if file doesn't exist."""
    version = mod_stitch.extract_version(Path("/nonexistent/pyproject.toml"))
    assert version == "unknown"


def test_extract_version_no_version(tmp_path: Path) -> None:
    """Should return 'unknown' if version not found."""
    path = tmp_path / "pyproject.toml"
    path.write_text("# no version here\n")

    version = mod_stitch.extract_version(path)
    assert version == "unknown"
