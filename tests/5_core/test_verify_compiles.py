# tests/5_core/test_verify_compiles.py
"""Tests for verify_compiles function."""

import tempfile
from pathlib import Path

import serger.verify_script as mod_verify


def test_verify_compiles_valid_python() -> None:
    """Should return True for valid Python code."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("def hello():\n    return 'world'\n")
        f.flush()
        path = Path(f.name)

    try:
        result = mod_verify.verify_compiles(path)
        assert result is True
    finally:
        path.unlink()


def test_verify_compiles_invalid_syntax() -> None:
    """Should return False for invalid Python syntax."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("def hello(\n    return 'world'\n")  # Missing closing paren
        f.flush()
        path = Path(f.name)

    try:
        result = mod_verify.verify_compiles(path)
        assert result is False
    finally:
        path.unlink()


def test_verify_compiles_empty_file() -> None:
    """Should return True for empty file (valid Python)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("")
        f.flush()
        path = Path(f.name)

    try:
        result = mod_verify.verify_compiles(path)
        assert result is True
    finally:
        path.unlink()


def test_verify_compiles_nonexistent_file() -> None:
    """Should return False for non-existent file."""
    path = Path("/nonexistent/file.py")
    # py_compile raises FileNotFoundError for nonexistent files, which our
    # function catches and returns False for
    result = mod_verify.verify_compiles(path)
    assert result is False
