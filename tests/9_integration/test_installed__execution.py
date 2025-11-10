# tests/9_integration/test_installed__execution.py
"""Verify the installed package version works via `python -m serger`.

NOTE: These tests are currently for file-copying (pocket-build responsibility).
They will be adapted for stitch builds in Phase 5.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import serger.meta as mod_meta


# --- only for installed runs ---
__runtime_mode__ = "installed"

pytestmark = pytest.mark.pocket_build_compat


def test_installed_module_execution() -> None:
    """Ensure the installed package can be invoked as `python -m <package>`."""
    # --- setup ---

    # - Execution check (isolated temp dir) -
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        dummy = tmp / "dummy.txt"
        dummy.write_text("hi", encoding="utf-8")

        config = tmp / f".{mod_meta.PROGRAM_CONFIG}.json"
        config.write_text(
            '{"builds":[{"include":["dummy.txt"],"out":"dist"}]}',
            encoding="utf-8",
        )

        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", mod_meta.PROGRAM_PACKAGE, "--out", "tmp-dist"],
            check=False,
            cwd=tmp,  # ✅ run in temp dir
            capture_output=True,
            text=True,
            timeout=15,
        )

    # --- verify ---
    assert result.returncode == 0, (
        f"Non-zero exit ({result.returncode}):\n{result.stderr}"
    )
    assert "Build completed" in result.stdout
    assert "🎉 All builds complete" in result.stdout
