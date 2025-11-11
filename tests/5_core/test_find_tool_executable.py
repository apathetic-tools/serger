# tests/5_core/test_find_tool_executable.py
"""Tests for find_tool_executable function."""

import shutil
import tempfile
from pathlib import Path

import pytest

import serger.verify_script as mod_verify
from tests.utils import patch_everywhere


def test_find_tool_executable_when_tool_exists() -> None:
    """Should return tool path when tool is available."""
    # This test will only pass if ruff is actually available
    result = mod_verify.find_tool_executable("ruff")
    if shutil.which("ruff") is not None:
        assert result is not None
        assert isinstance(result, str)
    else:
        assert result is None


def test_find_tool_executable_when_tool_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should return None when tool is not available."""

    # Mock shutil.which to return None
    def mock_which(_: str) -> None:
        return None

    patch_everywhere(monkeypatch, shutil, "which", mock_which)
    result = mod_verify.find_tool_executable("nonexistent_tool")
    assert result is None


def test_find_tool_executable_with_custom_path() -> None:
    """Should return custom path when it exists."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        custom_path = f.name

    try:
        result = mod_verify.find_tool_executable("ruff", custom_path=custom_path)
        assert result is not None
        assert Path(result).exists()
    finally:
        Path(custom_path).unlink(missing_ok=True)


def test_find_tool_executable_with_invalid_custom_path() -> None:
    """Should fall back to PATH when custom path doesn't exist."""
    invalid_path = "/nonexistent/path/to/tool"
    result = mod_verify.find_tool_executable("ruff", custom_path=invalid_path)
    # Should fall back to PATH lookup
    if shutil.which("ruff") is not None:
        assert result is not None
    else:
        assert result is None
