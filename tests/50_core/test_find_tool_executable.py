# tests/50_core/test_find_tool_executable.py
"""Tests for find_tool_executable function."""

import shutil
from pathlib import Path

import apathetic_utils as mod_utils
import pytest

import serger.meta as mod_meta
import serger.verify_script as mod_verify


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

    mod_utils.patch_everywhere(
        monkeypatch,
        shutil,
        "which",
        mock_which,
        package_prefix=mod_meta.PROGRAM_PACKAGE,
        stitch_hints={"/dist/", "standalone", f"{mod_meta.PROGRAM_SCRIPT}.py", ".pyz"},
    )
    result = mod_verify.find_tool_executable("nonexistent_tool")
    assert result is None


def test_find_tool_executable_with_custom_path(tmp_path: Path) -> None:
    """Should return custom path when it exists."""
    custom_path = tmp_path / "tool"
    custom_path.touch()

    result = mod_verify.find_tool_executable("ruff", custom_path=str(custom_path))
    assert result is not None
    assert Path(result).exists()


def test_find_tool_executable_with_invalid_custom_path() -> None:
    """Should fall back to PATH when custom path doesn't exist."""
    invalid_path = "/nonexistent/path/to/tool"
    result = mod_verify.find_tool_executable("ruff", custom_path=invalid_path)
    # Should fall back to PATH lookup
    if shutil.which("ruff") is not None:
        assert result is not None
    else:
        assert result is None
