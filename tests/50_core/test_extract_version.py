# tests/50_core/test_extract_version.py
"""Tests for extract_version function."""

import tempfile
from pathlib import Path

import serger.stitch as mod_stitch


def test_extract_version_from_valid_file() -> None:
    """Should extract version from valid pyproject.toml."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('version = "1.2.3"\n')
        f.flush()
        path = Path(f.name)

    try:
        version = mod_stitch.extract_version(path)
        assert version == "1.2.3"
    finally:
        path.unlink()


def test_extract_version_missing_file() -> None:
    """Should return 'unknown' if file doesn't exist."""
    version = mod_stitch.extract_version(Path("/nonexistent/pyproject.toml"))
    assert version == "unknown"


def test_extract_version_no_version() -> None:
    """Should return 'unknown' if version not found."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("# no version here\n")
        f.flush()
        path = Path(f.name)

    try:
        version = mod_stitch.extract_version(path)
        assert version == "unknown"
    finally:
        path.unlink()
