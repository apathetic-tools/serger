# tests/90_integration/test_version.py
"""Tests for package.cli (package and standalone versions)."""

import os
import re
import sys

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
        in_ci = is_ci()
        ci_env = os.getenv("CI")
        github_actions = os.getenv("GITHUB_ACTIONS")
        git_tag = os.getenv("GIT_TAG")
        github_ref = os.getenv("GITHUB_REF")
        runtime_mode = os.getenv("RUNTIME_MODE")
        # Debug output
        print(
            f"\n[DEBUG test_version_flag] "
            f"in_ci={in_ci}, CI={ci_env}, GITHUB_ACTIONS={github_actions}, "
            f"GIT_TAG={git_tag}, GITHUB_REF={github_ref}, "
            f"RUNTIME_MODE={runtime_mode}",
            file=sys.stderr,
            flush=True,
        )
        print(
            f"[DEBUG test_version_flag] output: {out!r}",
            file=sys.stderr,
            flush=True,
        )
        if is_ci():
            assert re.search(r"\([0-9a-f]{4,}\)", out)
        else:
            assert "(unknown (local build))".lower() in out
    else:
        # installed (source) version — should always have a live git commit hash
        assert re.search(r"\([0-9a-f]{4,}\)", out)
