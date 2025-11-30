# tests/50_core/test_verify_compiles.py
"""Tests for verify_compiles function."""

from pathlib import Path

import serger.verify_script as mod_verify


def test_verify_compiles_valid_python(tmp_path: Path) -> None:
    """Should return True for valid Python code."""
    path = tmp_path / "test.py"
    path.write_text("def hello():\n    return 'world'\n")

    result = mod_verify.verify_compiles(path)
    assert result is True


def test_verify_compiles_invalid_syntax(tmp_path: Path) -> None:
    """Should return False for invalid Python syntax."""
    path = tmp_path / "test.py"
    path.write_text("def hello(\n    return 'world'\n")  # Missing closing paren

    result = mod_verify.verify_compiles(path)
    assert result is False


def test_verify_compiles_empty_file(tmp_path: Path) -> None:
    """Should return True for empty file (valid Python)."""
    path = tmp_path / "test.py"
    path.write_text("")

    result = mod_verify.verify_compiles(path)
    assert result is True


def test_verify_compiles_nonexistent_file() -> None:
    """Should return False for non-existent file."""
    path = Path("/nonexistent/file.py")
    # py_compile raises FileNotFoundError for nonexistent files, which our
    # function catches and returns False for
    result = mod_verify.verify_compiles(path)
    assert result is False
