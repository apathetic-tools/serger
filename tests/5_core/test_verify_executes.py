# tests/5_core/test_verify_executes.py
"""Tests for verify_executes function."""

import tempfile
from pathlib import Path

import serger.verify_script as mod_verify


def test_verify_executes_valid_script() -> None:
    """Should return True for valid Python script."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        script_content = (
            "def main():\n    return 0\n\n"
            "if __name__ == '__main__':\n    exit(main())\n"
        )
        f.write(script_content)
        f.flush()
        path = Path(f.name)
        path.chmod(0o755)

    try:
        result = mod_verify.verify_executes(path)
        assert result is True
    finally:
        path.unlink()


def test_verify_executes_script_with_help_flag() -> None:
    """Should return True for script that supports --help flag."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        # Simple script that handles --help
        f.write(
            "import sys\n"
            "if '--help' in sys.argv:\n"
            "    print('Usage: script.py')\n"
            "    sys.exit(0)\n"
            "sys.exit(1)\n"
        )
        f.flush()
        path = Path(f.name)
        path.chmod(0o755)

    try:
        result = mod_verify.verify_executes(path)
        assert result is True
    finally:
        path.unlink()


def test_verify_executes_invalid_syntax() -> None:
    """Should return False for script with syntax errors."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("def main(\n    return 0\n")  # Invalid syntax
        f.flush()
        path = Path(f.name)

    try:
        result = mod_verify.verify_executes(path)
        assert result is False
    finally:
        path.unlink()


def test_verify_executes_empty_file() -> None:
    """Should return True for empty file (valid Python)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("")
        f.flush()
        path = Path(f.name)

    try:
        result = mod_verify.verify_executes(path)
        assert result is True
    finally:
        path.unlink()


def test_verify_executes_nonexistent_file() -> None:
    """Should return False for non-existent file."""
    path = Path("/nonexistent/file.py")
    result = mod_verify.verify_executes(path)
    assert result is False
