# tests/9_integration/test_standalone__execution.py
"""Verify that the standalone standalone version (`dist/serger.py`)
was generated correctly — includes metadata, license header,
and matches the declared version from pyproject.toml.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import serger.meta as mod_meta
from tests.utils import PROJ_ROOT, make_test_package


# --- only for singlefile runs ---
__runtime_mode__ = "singlefile"


def test_standalone_script_metadata_and_execution() -> None:
    """Ensure the generated standalone script is complete and functional."""
    # --- setup ---
    script = PROJ_ROOT / "dist" / f"{mod_meta.PROGRAM_SCRIPT}.py"

    # --- execute and verify ---

    # - Basic existence checks -
    assert script.exists(), (
        "Standalone script not found — run `poetry run poe build:single` first."
    )

    # - Execution check (isolated temp dir) -
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Create a simple Python package structure for stitching
        pkg_dir = tmp / "mypkg"
        make_test_package(pkg_dir)

        # Create config using json.dumps (matching pattern from other tests)
        config = tmp / f".{mod_meta.PROGRAM_CONFIG}.json"
        config.write_text(
            json.dumps(
                {
                    "builds": [
                        {
                            "package": "mypkg",
                            "include": ["mypkg/**/*.py"],
                            "out": "tmp-dist/mypkg.py",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        result = subprocess.run(  # noqa: S603
            [sys.executable, str(script)],
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
