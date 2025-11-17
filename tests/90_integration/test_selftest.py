# tests/90_integration/test_selftest.py
"""Tests for --selftest flag in serger CLI.

These tests verify that the --selftest flag runs the self-test functionality,
which creates a test package, stitches it together, and verifies the output
compiles and executes correctly.
"""

import pytest

import serger.cli as mod_cli


def test_selftest_flag_success(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--selftest should run the self-test and exit with code 0 on success."""
    # --- execute ---
    code = mod_cli.main(["--selftest"])

    # --- verify ---
    assert code == 0

    # Check output mentions self-test
    captured = capsys.readouterr()
    out = (captured.out + captured.err).lower()
    assert "self-test" in out or "selftest" in out.replace("-", "")


def test_selftest_ignores_other_flags(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--selftest should run and exit early, ignoring other CLI flags."""
    # --- execute ---
    # --selftest should exit immediately without requiring a config or includes
    code = mod_cli.main(["--selftest", "--verbose", "--dry-run"])

    # --- verify ---
    assert code == 0

    # Output should indicate self-test ran
    captured = capsys.readouterr()
    out = (captured.out + captured.err).lower()
    assert "self-test" in out or "selftest" in out.replace("-", "")


def test_selftest_shows_success_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--selftest should show a success message when the test passes."""
    # --- execute ---
    code = mod_cli.main(["--selftest"])

    # --- verify ---
    assert code == 0

    captured = capsys.readouterr()
    out = (captured.out + captured.err).lower()
    # Should show success message
    assert "self-test passed" in out or "passed" in out
    # Should mention it's working correctly
    assert "working correctly" in out or "is working" in out


def test_selftest_verbose_shows_debug_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--selftest with --verbose should show DEBUG level output."""
    # --- execute ---
    code = mod_cli.main(["--selftest", "--verbose"])

    # --- verify ---
    assert code == 0

    captured = capsys.readouterr()
    out = captured.out + captured.err
    # Verbose mode should show DEBUG output with [SELFTEST] prefix
    assert "[SELFTEST]" in out or "[DEBUG]" in out
    # Should show phase information
    assert "phase" in out.lower() or "temp dir" in out.lower()
