# tests/90_integration/test_package__execution.py
"""Verify the package version works via `python -m serger`."""

import sys
from pathlib import Path

import apathetic_utils

import serger.meta as mod_meta
from tests.utils import make_test_package, write_config_file


# --- only for package runs ---
__runtime_mode__ = "package"


def test_package_module_execution(tmp_path: Path) -> None:
    """Ensure the package can be invoked as `python -m <package>`."""
    # --- setup ---

    # - Execution check (isolated temp dir) -
    tmp = tmp_path

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

    result = apathetic_utils.run_with_output(
        [sys.executable, "-m", mod_meta.PROGRAM_PACKAGE],
        check=False,
        cwd=tmp,  # ✅ run in temp dir
        timeout=15,
    )

    # --- verify ---
    assert result.returncode == 0, (
        f"Non-zero exit ({result.returncode}):\n{result.stderr}"
    )
    assert "Stitch completed" in result.stdout
    assert "✅" in result.stdout
    assert "completed" in result.stdout.lower()
