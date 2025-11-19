# tests/90_integration/test_version.py
"""Tests for package.cli (package and standalone versions)."""

import os
import re

import pytest

import serger.cli as mod_cli
import serger.meta as mod_meta


def test_version_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should print version and commit info cleanly."""
    # --- execute ---
    code = mod_cli.main(["--version"])
    out = capsys.readouterr().out.lower()

    # --- verify ---
    assert code == 0
    assert mod_meta.PROGRAM_DISPLAY.lower() in out
    assert re.search(r"\d+\.\d+\.\d+", out)

    if os.getenv("RUNTIME_MODE") in {"singlefile"}:
        # Standalone version — commit is determined at build time
        # Check the actual output: if script has a commit hash, it was built in CI
        # If it has "unknown (local build)", it was built locally
        # We check the actual output rather than is_ci() at runtime because
        # the script's commit is embedded at build time, not runtime
        has_commit_hash = bool(re.search(r"\([0-9a-f]{4,}\)", out))
        has_unknown_local = "(unknown (local build))".lower() in out
        assert has_commit_hash or has_unknown_local, (
            f"Expected either commit hash or 'unknown (local build)' in output: {out!r}"
        )
    else:
        # installed (source) version — should always have a live git commit hash
        assert re.search(r"\([0-9a-f]{4,}\)", out)
