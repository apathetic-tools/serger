# tests/95_integration_output/test_zero_config_auto_detect.py
"""Integration tests for zero-config auto-detection feature.

Tests that when there's exactly one module in source_bases and no package
is provided (or package doesn't match), Serger automatically detects and
uses that single module.
"""

from pathlib import Path

import pytest

import serger.cli as mod_cli
import serger.meta as mod_meta


def test_zero_config_auto_detect_single_package_no_package_setting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Build succeeds with zero config when single package exists and no package is set.

    Scenario:
    - NO config file (truly configless)
    - NO pyproject.toml
    - NO CLI arguments
    - src/mypkg/ exists (single package directory)
    - source_bases defaults to ["src", "lib", "packages"]
    - Should auto-detect mypkg as package and set includes to src/mypkg/
    - Build should succeed
    """
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create single package directory
    pkg_dir = src_dir / "mypkg"
    pkg_dir.mkdir()
    module_file = pkg_dir / "module.py"
    module_file.write_text(
        """def hello():
    return "Hello from mypkg"
"""
    )

    # NO config file - truly configless
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    if config.exists():
        config.unlink()

    # NO pyproject.toml
    pyproject = tmp_path / "pyproject.toml"
    if pyproject.exists():
        pyproject.unlink()

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
    stitched_file = dist / "mypkg.py"
    assert stitched_file.exists(), "Stitched file should exist"
    assert stitched_file.is_file(), "Stitched file should be a file"

    # Log output should mention stitching
    assert "stitch completed" in out or "all builds complete" in out

    # Verify the stitched file contains the module content
    content = stitched_file.read_text()
    assert "def hello()" in content
    assert "Hello from mypkg" in content


def test_zero_config_auto_detect_single_file_module_no_package_setting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Build succeeds with zero config when single file module exists.

    Scenario:
    - NO config file (truly configless)
    - NO pyproject.toml
    - NO CLI arguments
    - src/mymodule.py exists (single-file module)
    - source_bases defaults to ["src", "lib", "packages"]
    - Should auto-detect mymodule as package and set includes to src/mymodule.py
    - Build should succeed
    """
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create single-file module
    module_file = src_dir / "mymodule.py"
    module_file.write_text(
        """def hello():
    return "Hello from mymodule"
"""
    )

    # NO config file - truly configless
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    if config.exists():
        config.unlink()

    # NO pyproject.toml
    pyproject = tmp_path / "pyproject.toml"
    if pyproject.exists():
        pyproject.unlink()

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


def test_zero_config_auto_detect_package_not_found_in_source_bases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Build uses user-provided package even when not found in source_bases.

    Scenario:
    - Has config with package="nonexistent" but no includes
    - src/mypkg/ exists (single package directory)
    - source_bases = ["src"]
    - Package "nonexistent" is not found in source_bases
    - User-provided package is always respected (highest priority)
    - Build should fail because package is not found (no includes auto-set)
    """
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create single package directory
    pkg_dir = src_dir / "mypkg"
    pkg_dir.mkdir()
    module_file = pkg_dir / "module.py"
    module_file.write_text(
        """def hello():
    return "Hello from mypkg"
"""
    )

    # Create config with package that doesn't exist in source_bases
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        """{
    "package": "nonexistent",
    "source_bases": ["src"],
    "out": "dist"
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

    # Should fail because user-provided package "nonexistent" is not found
    # and no includes were auto-set (package not found in source_bases)
    assert code != 0, f"Build should fail. Output: {out}"
    assert (
        "package name 'nonexistent' provided" in out
        or "no include patterns found" in out
    )


def test_zero_config_no_auto_detect_when_all_bases_have_multiple_modules(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Build succeeds using first package in source_bases when all have multiple.

    Scenario:
    - Has config with source_bases=["src", "lib"] but no package/includes
    - src/ has multiple modules (pkg1, pkg2)
    - lib/ has multiple modules (pkg3, pkg4)
    - With new resolution logic (step 7), uses first package in source_bases
    - Build should succeed with auto-detected package and auto-set includes
    """
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    # Multiple modules in src - rejected
    (src_dir / "pkg1").mkdir()
    ((src_dir / "pkg1") / "module.py").write_text("def hello1(): pass\n")
    (src_dir / "pkg2").mkdir()
    ((src_dir / "pkg2") / "module.py").write_text("def hello2(): pass\n")

    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    # Multiple modules in lib - also rejected
    (lib_dir / "pkg3").mkdir()
    ((lib_dir / "pkg3") / "module.py").write_text("def hello3(): pass\n")
    (lib_dir / "pkg4").mkdir()
    ((lib_dir / "pkg4") / "module.py").write_text("def hello4(): pass\n")

    # Create config with multiple source_bases, all with multiple modules
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        """{
    "source_bases": ["src", "lib"],
    "out": "dist"
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

    # Should succeed with first package in source_bases order (step 7)
    assert code == 0, f"Build should succeed. Output: {out}"
    # Package should be auto-detected (pkg1 or pkg3, depending on order)
    assert "auto-detected" in out or "selected from source_bases" in out
    # Output directory should exist
    dist = tmp_path / "dist"
    assert dist.exists(), "Output directory should exist"


def test_zero_config_auto_detect_with_custom_source_bases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Build succeeds with custom source_bases when single module exists.

    Scenario:
    - Has config with custom source_bases=["lib"] but no package/includes
    - lib/mypkg/ exists (single package directory)
    - Should auto-detect mypkg as package and set includes to lib/mypkg/
    - Build should succeed
    """
    # --- setup ---
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()

    # Create single package directory in custom source_bases
    pkg_dir = lib_dir / "mypkg"
    pkg_dir.mkdir()
    module_file = pkg_dir / "module.py"
    module_file.write_text(
        """def hello():
    return "Hello from mypkg"
"""
    )

    # Create config with custom source_bases but no package/includes
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        """{
    "source_bases": ["lib"],
    "out": "dist"
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


def test_zero_config_auto_detect_picks_first_base_with_single_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Build succeeds by picking first source_base with exactly 1 module.

    Scenario:
    - Has config with source_bases=["src", "lib"] but no package/includes
    - src/ has multiple modules (pkg1, pkg2) - should be rejected
    - lib/ has exactly 1 module (mypkg) - should be picked
    - Should auto-detect mypkg from lib/ and set includes to lib/mypkg/
    - Build should succeed
    """
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    # Multiple modules in src - should be rejected
    (src_dir / "pkg1").mkdir()
    ((src_dir / "pkg1") / "module.py").write_text("def hello1(): pass\n")
    (src_dir / "pkg2").mkdir()
    ((src_dir / "pkg2") / "module.py").write_text("def hello2(): pass\n")

    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    # Single module in lib - should be picked
    pkg_dir = lib_dir / "mypkg"
    pkg_dir.mkdir()
    module_file = pkg_dir / "module.py"
    module_file.write_text(
        """def hello():
    return "Hello from mypkg"
"""
    )

    # Create config with multiple source_bases but no package/includes
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        """{
    "source_bases": ["src", "lib"],
    "out": "dist"
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

    # Verify the stitched file contains the module content from lib/mypkg
    content = stitched_file.read_text()
    assert "def hello()" in content
    assert "Hello from mypkg" in content
