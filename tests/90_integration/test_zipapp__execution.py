# tests/90_integration/test_zipapp__execution.py
"""Verify that the zipapp version (`dist/serger.pyz`)
was generated correctly — includes metadata, license header,
and matches the declared version from pyproject.toml.
"""

import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

import serger.meta as mod_meta
from tests.utils import PROJ_ROOT, make_test_package, write_config_file


# --- only for zipapp runs ---
__runtime_mode__ = "zipapp"


@pytest.mark.skip(reason="Re-enable once zipbundler is fully integrated")
def test_zipapp_metadata_and_execution(tmp_path: Path) -> None:
    """Ensure the generated zipapp is complete and functional."""
    # --- setup ---
    zipapp_file = PROJ_ROOT / "dist" / f"{mod_meta.PROGRAM_SCRIPT}.pyz"

    # --- execute and verify ---

    # - Basic existence checks -
    assert zipapp_file.exists(), (
        "Zipapp not found — run `poetry run poe build:zipapp` first."
    )

    # - Verify it's a valid zip file -
    assert zipfile.is_zipfile(zipapp_file), "Zipapp should be a valid zip file"

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
        [sys.executable, str(zipapp_file)],
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


@pytest.mark.skip(reason="Re-enable once zipbundler is fully integrated")
def test_zipapp_import_semantics() -> None:
    """Test that zipapp builds maintain correct import semantics.

    This test verifies our project code works correctly when built with zipbundler:
    1. Verifies the zipapp exists
    2. Imports from the zipapp and verifies import semantics work correctly:
       - serger module is importable
       - Can import and use the module from zipapp format

    This verifies our project configuration and code work correctly with zipbundler.
    """
    # --- setup ---
    zipapp_file = PROJ_ROOT / "dist" / f"{mod_meta.PROGRAM_SCRIPT}.pyz"

    # --- execute and verify ---
    assert zipapp_file.exists(), (
        "Zipapp not found — run `poetry run poe build:zipapp` first."
    )

    # Verify it's a valid zip file
    assert zipfile.is_zipfile(zipapp_file), "Zipapp should be a valid zip file"

    # Add zipapp to sys.path and import
    zipapp_str = str(zipapp_file)
    original_path = sys.path.copy()

    try:
        if zipapp_str not in sys.path:
            sys.path.insert(0, zipapp_str)

        # Import serger from the zipapp
        import serger  # noqa: PLC0415

        # --- verify: import semantics ---
        # Verify serger module is available and has expected attributes
        # Note: In zipapp mode, __main__ is not an attribute but can be imported
        try:
            import serger.__main__  # noqa: PLC0415  # pyright: ignore[reportUnusedImport]

            __main___available = True
        except ImportError:
            __main___available = False
        assert __main___available, "serger.__main__ should be importable from zipapp"
        assert hasattr(serger, "meta"), "serger.meta should be available"

        # Verify meta module has expected attributes
        assert hasattr(serger.meta, "PROGRAM_PACKAGE"), (
            "serger.meta.PROGRAM_PACKAGE should be available"
        )
        assert hasattr(serger.meta, "PROGRAM_SCRIPT"), (
            "serger.meta.PROGRAM_SCRIPT should be available"
        )

        # Verify the values are correct
        assert serger.meta.PROGRAM_PACKAGE == "serger", (
            f"serger.meta.PROGRAM_PACKAGE should be 'serger', "
            f"got {serger.meta.PROGRAM_PACKAGE!r}"
        )
        assert serger.meta.PROGRAM_SCRIPT == "serger", (
            f"serger.meta.PROGRAM_SCRIPT should be 'serger', "
            f"got {serger.meta.PROGRAM_SCRIPT!r}"
        )

    finally:
        # Clean up sys.path
        sys.path[:] = original_path
        # Clean up imported modules
        modules_to_remove = [
            name
            for name in list(sys.modules.keys())
            if name == "serger" or name.startswith("serger.")
        ]
        for name in modules_to_remove:
            del sys.modules[name]
