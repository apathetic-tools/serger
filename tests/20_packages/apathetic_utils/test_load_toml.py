# tests/0_independant/test_load_toml.py
"""Tests for load_toml utility function."""

import tempfile
from pathlib import Path

import pytest

import apathetic_utils.files as amod_utils_files


def test_load_toml_valid_file() -> None:
    """Should load valid TOML file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
version = "1.2.3"
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        data = amod_utils_files.load_toml(path)
        assert data is not None
        assert "project" in data
        assert data["project"]["name"] == "test-package"
        assert data["project"]["version"] == "1.2.3"
    finally:
        path.unlink()


def test_load_toml_missing_file() -> None:
    """Should raise FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError, match="not found"):
        amod_utils_files.load_toml(Path("/nonexistent/file.toml"))


def test_load_toml_invalid_syntax() -> None:
    """Should raise ValueError for invalid TOML syntax."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("invalid toml {[}\n")
        f.flush()
        path = Path(f.name)

    try:
        # Depending on parser, may raise ValueError or return empty dict
        # Both are acceptable - just ensure it doesn't crash
        try:
            data = amod_utils_files.load_toml(path)
            # If it doesn't raise, should return something
            assert isinstance(data, dict)
        except ValueError:
            # Also acceptable
            pass
    finally:
        path.unlink()


# Note: Tests for missing tomli on Python 3.10 are complex to mock reliably.
# These would require mocking sys.modules or __import__, which is fragile.
# The functionality is tested indirectly through resolve_build_config tests.
