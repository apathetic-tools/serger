# tests/50_core/test_verify_compiles_string.py
"""Tests for verify_compiles_string function."""

import pytest

import serger.verify_script as mod_verify


def test_verify_compiles_string_valid_code() -> None:
    """Should not raise for valid Python code."""
    valid_code = "def hello():\n    return 'world'\n"
    # Should not raise
    mod_verify.verify_compiles_string(valid_code)


def test_verify_compiles_string_invalid_syntax() -> None:
    """Should raise SyntaxError for invalid Python syntax."""
    invalid_code = "def hello(\n    return 'world'\n"  # Missing closing paren
    with pytest.raises(SyntaxError) as exc_info:
        mod_verify.verify_compiles_string(invalid_code)
    assert exc_info.value.lineno is not None
    assert exc_info.value.msg is not None


def test_verify_compiles_string_empty_code() -> None:
    """Should not raise for empty code (valid Python)."""
    empty_code = ""
    # Should not raise
    mod_verify.verify_compiles_string(empty_code)


def test_verify_compiles_string_preserves_error_details() -> None:
    """Should preserve line number and message in SyntaxError."""
    invalid_code = "x = 1\nx = 2\nx = 3\ninvalid syntax here\n"
    with pytest.raises(SyntaxError) as exc_info:
        mod_verify.verify_compiles_string(invalid_code)
    error = exc_info.value
    expected_line = 4
    assert error.lineno == expected_line
    assert "invalid syntax" in error.msg.lower()
