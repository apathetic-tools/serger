# tests/90_integration/test_version.py
"""Tests for package.cli (package and standalone versions)."""

import os
import re

import pytest

import serger.cli as mod_cli
import serger.meta as mod_meta
from tests.utils import is_ci


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
        # If we're running in CI, the script was built in CI and should have
        # a commit hash. If we're running locally, the script was built locally
        # and should show "unknown (local build)"
        if is_ci():
            assert re.search(r"\([0-9a-f]{4,}\)", out)
        else:
            assert "(unknown (local build))".lower() in out
    else:
        # installed (source) version — should always have a live git commit hash
        assert re.search(r"\([0-9a-f]{4,}\)", out)
