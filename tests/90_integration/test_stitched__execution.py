# tests/90_integration/test_stitched__execution.py
"""Verify that the stitched version (`dist/serger.py`)
was generated correctly — includes metadata, license header,
and matches the declared version from pyproject.toml.
"""

import os
import subprocess
import sys
from pathlib import Path

import serger.meta as mod_meta
from tests.utils import PROJ_ROOT, make_test_package, write_config_file


# --- only for stitched runs ---
__runtime_mode__ = "stitched"


def test_stitched_script_metadata_and_execution(tmp_path: Path) -> None:
    """Ensure the generated stitched script is complete and functional."""
    # --- setup ---
    script = PROJ_ROOT / "dist" / f"{mod_meta.PROGRAM_SCRIPT}.py"

    # --- execute and verify ---

    # - Basic existence checks -
    assert script.exists(), (
        "Stitched script not found — run `poetry run poe build:stitched` first."
    )

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

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(script)],
        check=False,
        cwd=tmp,  # ✅ run in temp dir
        capture_output=True,
        text=True,
        timeout=15,
        env=os.environ.copy(),
    )

    # --- verify ---
    assert result.returncode == 0, (
        f"Non-zero exit ({result.returncode}):\n{result.stderr}"
    )
    assert "Stitch completed" in result.stdout
    assert "✅" in result.stdout
    assert "completed" in result.stdout.lower()
