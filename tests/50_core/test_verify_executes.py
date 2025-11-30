# tests/50_core/test_verify_executes.py
"""Tests for verify_executes function."""

from pathlib import Path

import serger.verify_script as mod_verify


def test_verify_executes_valid_script(tmp_path: Path) -> None:
    """Should return True for valid Python script."""
    path = tmp_path / "script.py"
    script_content = (
        "def main():\n    return 0\n\nif __name__ == '__main__':\n    exit(main())\n"
    )
    path.write_text(script_content)
    path.chmod(0o755)

    result = mod_verify.verify_executes(path)
    assert result is True


def test_verify_executes_script_with_help_flag(tmp_path: Path) -> None:
    """Should return True for script that supports --help flag."""
    path = tmp_path / "script.py"
    # Simple script that handles --help
    path.write_text(
        "import sys\n"
        "if '--help' in sys.argv:\n"
        "    print('Usage: script.py')\n"
        "    sys.exit(0)\n"
        "sys.exit(1)\n"
    )
    path.chmod(0o755)

    result = mod_verify.verify_executes(path)
    assert result is True


def test_verify_executes_invalid_syntax(tmp_path: Path) -> None:
    """Should return False for script with syntax errors."""
    path = tmp_path / "script.py"
    path.write_text("def main(\n    return 0\n")  # Invalid syntax

    result = mod_verify.verify_executes(path)
    assert result is False


def test_verify_executes_empty_file(tmp_path: Path) -> None:
    """Should return True for empty file (valid Python)."""
    path = tmp_path / "script.py"
    path.write_text("")

    result = mod_verify.verify_executes(path)
    assert result is True


def test_verify_executes_nonexistent_file() -> None:
    """Should return False for non-existent file."""
    path = Path("/nonexistent/file.py")
    result = mod_verify.verify_executes(path)
    assert result is False
