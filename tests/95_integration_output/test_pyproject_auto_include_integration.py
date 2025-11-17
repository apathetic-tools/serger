# tests/95_integration_output/test_pyproject_auto_include_integration.py
"""Integration tests for pyproject.toml auto-include feature.

Tests that when pyproject.toml has a name matching a module in module_bases,
auto-include works correctly without requiring explicit includes.
"""

from pathlib import Path

import pytest

import serger.cli as mod_cli
import serger.meta as mod_meta


def test_pyproject_auto_include_single_file_module_in_module_bases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Build succeeds when pyproject name matches single-file module in module_bases.

    Scenario:
    - Has pyproject.toml with name = "mymodule"
    - No config file
    - No CLI includes/arguments
    - src/mymodule.py exists (single-file module)
    - module_bases defaults to ["src"]
    - Auto-include should set includes to src/mymodule.py
    - Build should succeed
    """
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create single-file module matching pyproject name
    module_file = src_dir / "mymodule.py"
    module_file.write_text(
        """def hello():
    return "Hello from mymodule"
"""
    )

    # Create pyproject.toml with name matching the module
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "mymodule"
version = "1.0.0"
"""
    )

    # Create minimal config with module_bases but no package or includes
    # Package should come from pyproject.toml, includes should be auto-set
    # Need to enable use_pyproject_metadata since we have a config file
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        """{
    "module_bases": ["src"],
    "out": "dist",
    "use_pyproject_metadata": true
}
""",
        encoding="utf-8",
    )

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    captured = capsys.readouterr()
    out = (captured.out + captured.err).lower()

    # Should exit successfully
    assert code == 0, f"Build failed. Output: {out}"

    # Output directory should exist and contain stitched file
    dist = tmp_path / "dist"
    assert dist.exists(), "Output directory should exist"
    stitched_file = dist / "mymodule.py"
    assert stitched_file.exists(), "Stitched file should exist"
    assert stitched_file.is_file(), "Stitched file should be a file"

    # Log output should mention stitching
    assert "stitch completed" in out or "all builds complete" in out

    # Verify the stitched file contains the module content
    content = stitched_file.read_text()
    assert "def hello()" in content
    assert "Hello from mymodule" in content


def test_pyproject_auto_include_package_in_module_bases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Build should succeed when pyproject name matches package in module_bases.

    Scenario:
    - Has pyproject.toml with name = "mypkg"
    - No config file
    - No CLI includes/arguments
    - src/mypkg/ exists (package directory, no __init__.py needed)
    - src/mypkg/module.py exists
    - module_bases defaults to ["src"]
    - Auto-include should set includes to src/mypkg
    - Build should succeed
    """
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create package directory (namespace package, no __init__.py)
    pkg_dir = src_dir / "mypkg"
    pkg_dir.mkdir()
    module_file = pkg_dir / "module.py"
    module_file.write_text(
        """def hello():
    return "Hello from mypkg"
"""
    )

    # Create pyproject.toml with name matching the package
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "mypkg"
version = "1.0.0"
"""
    )

    # Create minimal config with module_bases but no package or includes
    # Package should come from pyproject.toml, includes should be auto-set
    # Need to enable use_pyproject_metadata since we have a config file
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        """{
    "module_bases": ["src"],
    "out": "dist",
    "use_pyproject_metadata": true
}
""",
        encoding="utf-8",
    )

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    captured = capsys.readouterr()
    out = (captured.out + captured.err).lower()

    # Should exit successfully
    assert code == 0, f"Build failed. Output: {out}"

    # Output directory should exist and contain stitched file
    dist = tmp_path / "dist"
    assert dist.exists(), "Output directory should exist"
    stitched_file = dist / "mypkg.py"
    assert stitched_file.exists(), "Stitched file should exist"
    assert stitched_file.is_file(), "Stitched file should be a file"

    # Log output should mention stitching
    assert "stitch completed" in out or "all builds complete" in out

    # Verify the stitched file contains the module content
    content = stitched_file.read_text()
    assert "def hello()" in content
    assert "Hello from mypkg" in content


def test_pyproject_auto_include_configless_single_file_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Build should succeed configless when pyproject name matches single-file module.

    Scenario:
    - Has pyproject.toml with name = "mymodule"
    - NO config file (truly configless)
    - No CLI includes/arguments
    - src/mymodule.py exists (single-file module)
    - module_bases defaults to ["src"]
    - Auto-include should set includes to src/mymodule.py
    - Package should come from pyproject.toml
    - Build should succeed with all required information
    """
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create single-file module matching pyproject name
    module_file = src_dir / "mymodule.py"
    module_file.write_text(
        """def hello():
    return "Hello from mymodule"
"""
    )

    # Create pyproject.toml with name matching the module
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "mymodule"
version = "1.0.0"
""",
        encoding="utf-8",
    )

    # NO config file - truly configless
    # Ensure no config file exists
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    if config.exists():
        config.unlink()

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    captured = capsys.readouterr()
    out = (captured.out + captured.err).lower()

    # Should exit successfully
    assert code == 0, f"Build failed. Output: {out}"

    # Output directory should exist and contain stitched file
    # Default output is dist/<package>.py
    dist = tmp_path / "dist"
    assert dist.exists(), "Output directory should exist"
    stitched_file = dist / "mymodule.py"
    assert stitched_file.exists(), "Stitched file should exist"
    assert stitched_file.is_file(), "Stitched file should be a file"

    # Log output should mention stitching
    assert "stitch completed" in out or "all builds complete" in out

    # Verify the stitched file contains the module content
    content = stitched_file.read_text()
    assert "def hello()" in content
    assert "Hello from mymodule" in content
