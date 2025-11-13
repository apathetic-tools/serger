# tests/9_integration/test_installed__execution.py
"""Verify the installed package version works via `python -m serger`."""

import subprocess
import sys
import tempfile
from pathlib import Path

import serger.meta as mod_meta
from tests.utils import make_test_package, write_config_file


# --- only for installed runs ---
__runtime_mode__ = "installed"


def test_installed_module_execution() -> None:
    """Ensure the installed package can be invoked as `python -m <package>`."""
    # --- setup ---

    # - Execution check (isolated temp dir) -
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Create a simple Python package structure for stitching
        pkg_dir = tmp / "mypkg"
        make_test_package(pkg_dir)

        # Create config
        config = tmp / f".{mod_meta.PROGRAM_CONFIG}.json"
        write_config_file(
            config,
            package="mypkg",
            include=["mypkg/**/*.py"],
            out="tmp-dist/mypkg.py",
        )

        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", mod_meta.PROGRAM_PACKAGE],
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
    assert "Stitch completed" in result.stdout
    assert "🎉 All builds complete" in result.stdout
