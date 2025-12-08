# tests/95_integration_output/test_pkg_module_reuse_bug.py
"""Test for package module reuse bug.

Tests that _create_pkg_module always creates new module objects instead of
reusing existing ones from sys.modules, which could have incorrect attributes
or be the stitched module itself.
"""

import importlib.util
import sys
import types
from pathlib import Path

import serger.build as mod_build
from tests.utils.buildconfig import make_build_cfg, make_include_resolved, make_resolved


def test_pkg_module_always_creates_new_object(tmp_path: Path) -> None:
    """Test that _create_pkg_module always creates new module objects.

    This test verifies that when a module with the same name as a package
    already exists in sys.modules (with incorrect attributes), the shim code
    creates a new module object instead of reusing the existing one.
    """
    # --- Setup: Create package structure ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()

    (pkg_dir / "__init__.py").write_text('"""My package."""\n\n__version__ = "1.0.0"\n')
    (pkg_dir / "module.py").write_text(
        '"""Test module."""\n\ndef get_value():\n    return 42\n'
    )

    # --- Pre-register a module with the same name as the package ---
    # This simulates a scenario where a module with the package name already
    # exists in sys.modules (could be from a previous import, or even the
    # stitched module itself)
    # When package="app" is set, "mypkg" becomes "app.mypkg"
    pkg_module_name = "app.mypkg"
    existing_module = types.ModuleType(pkg_module_name)
    existing_module.__package__ = "wrong_package"  # Wrong attribute
    existing_module.__file__ = "/fake/path/to/mypkg.py"  # Wrong file
    existing_module.some_attribute = "should_not_be_present"  # type: ignore[attr-defined]  # Extra attribute
    sys.modules[pkg_module_name] = existing_module

    # Store the original module ID to verify it's replaced
    original_module_id = id(existing_module)

    try:
        # --- Create build config ---
        out_file = tmp_path / "stitched.py"
        includes = [
            make_include_resolved("mypkg/**/*.py", tmp_path),
        ]

        build_cfg = make_build_cfg(
            tmp_path,
            includes,
            respect_gitignore=False,
            out=make_resolved("stitched.py", tmp_path),
            package="app",
            # No explicit order - let it auto-discover
        )

        # --- Execute stitch ---
        mod_build.run_build(build_cfg)

        # --- Verify output file exists ---
        assert out_file.exists(), "Stitched file should be created"

        # --- Load the stitched module ---
        unique_module_name = f"stitched_test_reuse_{tmp_path.name}"
        spec = importlib.util.spec_from_file_location(unique_module_name, out_file)
        assert spec is not None
        assert spec.loader is not None

        # Load the stitched module
        stitched_mod = importlib.util.module_from_spec(spec)
        sys.modules[unique_module_name] = stitched_mod
        spec.loader.exec_module(stitched_mod)

        # --- Verify that app.mypkg module was replaced with a new object ---
        # The shim code should have created a new module object, not reused
        # the existing one with wrong attributes
        assert pkg_module_name in sys.modules, (
            f"{pkg_module_name} should be in sys.modules. "
            f"Found: {[k for k in sys.modules if 'mypkg' in k]}"
        )

        mypkg_module = sys.modules[pkg_module_name]
        new_module_id = id(mypkg_module)

        # The module should be a NEW object (different ID)
        assert new_module_id != original_module_id, (
            f"{pkg_module_name} module should be a new object, not reused. "
            f"Original ID: {original_module_id}, New ID: {new_module_id}"
        )

        # The new module should have correct attributes
        # (not the wrong ones from old module)
        # The __package__ should be set (not "wrong_package" from the old module)
        assert mypkg_module.__package__ != "wrong_package", (
            f"{pkg_module_name}.__package__ should not be 'wrong_package' "
            f"(from old module). Got: '{mypkg_module.__package__}'"
        )
        assert mypkg_module.__package__ is not None, (
            f"{pkg_module_name}.__package__ should be set"
        )

        # The wrong attribute should not be present
        assert not hasattr(mypkg_module, "some_attribute"), (
            f"{pkg_module_name} module should not have 'some_attribute' "
            f"from the old module. Attributes: {sorted(dir(mypkg_module))}"
        )

        # The wrong __file__ should not be present (or should be different)
        if hasattr(mypkg_module, "__file__"):
            assert mypkg_module.__file__ != "/fake/path/to/mypkg.py", (
                f"{pkg_module_name}.__file__ should not be the fake path "
                f"from old module. Got: '{mypkg_module.__file__}'"
            )

        # Verify the module works correctly
        assert hasattr(mypkg_module, "module"), (
            f"{pkg_module_name} should have 'module' attribute. "
            f"Attributes: {sorted(dir(mypkg_module))}"
        )

        # Verify we can import and use the module
        from app.mypkg.module import (  # type: ignore[import-not-found]  # noqa: PLC0415  # pyright: ignore[reportMissingImports]
            get_value,  # pyright: ignore[reportUnknownVariableType]
        )

        assert get_value() == 42  # noqa: PLR2004  # pyright: ignore[reportUnknownVariableType]

    finally:
        # Cleanup
        for name in list(sys.modules.keys()):
            if name.startswith(("mypkg", "app.mypkg")):
                del sys.modules[name]
        # Also clean up the pre-registered module if it still exists
        if pkg_module_name in sys.modules:
            del sys.modules[pkg_module_name]
