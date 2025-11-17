# tests/90_integration/test_help.py
"""Tests for package.cli (package and standalone versions)."""

import pytest

import serger.cli as mod_cli
import serger.meta as mod_meta


def test_help_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should print usage information and exit cleanly when --help is passed."""
    # --- execute ---
    # Capture SystemExit since argparse exits after printing help.
    with pytest.raises(SystemExit) as e:
        mod_cli.main(["--help"])

    # --- verify ---
    # Argparse exits with code 0 for --help (must be outside context)
    assert e.value.code == 0

    out = capsys.readouterr().out.lower()
    assert "usage:".lower() in out
    assert mod_meta.PROGRAM_SCRIPT.lower() in out
    assert "--out".lower() in out
