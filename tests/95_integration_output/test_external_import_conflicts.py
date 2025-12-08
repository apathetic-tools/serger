# tests/95_integration_output/test_external_import_conflicts.py
"""Integration tests for external import conflict detection.

Tests that verify builds fail when external imports (stdlib or third-party)
conflict with shim module names.
"""

from argparse import Namespace
from pathlib import Path

import pytest

import serger.build as mod_build
import serger.config.config_loader as mod_config_loader
import serger.config.config_resolve as mod_config_resolve


def test_stdlib_import_conflicts_with_shim_fails(
    tmp_path: Path,
) -> None:
    """Verify that builds fail when external stdlib imports conflict with shims.

    This test verifies that when a local module has the same name as a stdlib
    module (e.g., `subprocess.py`) and the code imports that stdlib module,
    the build fails with a clear error message about the conflict.

    Previously, this was handled at runtime, but now we fail early during
    the build to prevent confusion.
    """
    # Create a test package with a local module named 'subprocess'
    # (conflicts with stdlib)
    pkg_dir = tmp_path / "testpkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("# Package\n")

    # Create subprocess.py - a local module that shadows stdlib subprocess
    (pkg_dir / "subprocess.py").write_text(
        '"""Local subprocess module (not stdlib)."""\n\n'
        'def helper_function():\n    return "from local subprocess"\n'
    )

    # Create runtime.py that imports stdlib subprocess (intending to use stdlib)
    (pkg_dir / "runtime.py").write_text(
        '"""Module that uses stdlib subprocess."""\n\n'
        "import subprocess\n\n"
        "def run_command(cmd: list[str]) -> subprocess.CompletedProcess:\n"
        "    # This should use stdlib subprocess.run(), not local subprocess module\n"
        "    return subprocess.run(cmd, capture_output=True, text=True)\n"
    )

    # Stitch it
    config_file = tmp_path / ".serger.jsonc"
    config_file.write_text(
        """{
  "include": ["testpkg/**/*.py"],
  "package": "testpkg",
  "out": "stitched.py"
}
"""
    )

    args = Namespace(config=str(config_file))
    config_result = mod_config_loader.load_and_validate_config(args)
    assert config_result is not None
    _, root_cfg, _ = config_result

    config_dir = config_file.parent
    cwd = Path.cwd()
    empty_args = Namespace()
    resolved_config = mod_config_resolve.resolve_config(
        root_cfg, empty_args, config_dir, cwd
    )

    # Build should fail with a conflict error
    with pytest.raises(ValueError, match="External import conflicts with module shim"):
        mod_build.run_build(resolved_config)
