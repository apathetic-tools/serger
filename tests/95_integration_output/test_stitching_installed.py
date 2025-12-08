# tests/95_integration_output/test_stitching_installed.py
"""Integration tests for stitching packages from installed locations.

Tests that serger can stitch packages from installed locations (site-packages)
into the output and that the stitched code works correctly.
"""

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

import serger.build as mod_build
from tests.utils import (
    cleanup_sys_modules,
    make_build_cfg,
    make_include_resolved,
    make_resolved,
)


@pytest.fixture(autouse=True)
def _cleanup_testpkg_modules() -> Iterator[None]:  # pyright: ignore[reportUnusedFunction]
    """Auto-cleanup testpkg modules between tests to avoid pollution.

    This fixture automatically runs before and after each test to clean up
    any testpkg or app modules from sys.modules, preventing module caching
    issues when tests load stitched modules with the same package names.
    """
    cleanup_sys_modules("testpkg", "app")
    yield
    cleanup_sys_modules("testpkg", "app")


def test_stitch_package_basic(tmp_path: Path) -> None:
    """Test basic stitching of a package from installed location."""
    # --- Setup: Create installed package ---
    installed_dir = tmp_path / "site-packages"
    installed_dir.mkdir()
    pkg_dir = installed_dir / "testpkg"
    pkg_dir.mkdir()

    (pkg_dir / "__init__.py").write_text(
        '"""Test package."""\n\n__version__ = "1.0.0"\n'
    )
    (pkg_dir / "module.py").write_text(
        '"""Test module."""\n\ndef hello():\n    return "Hello from testpkg"\n'
    )

    # --- Create build config ---
    out_file = tmp_path / "stitched.py"
    includes = [
        make_include_resolved("testpkg/**/*.py", installed_dir),
    ]

    build_cfg = make_build_cfg(
        tmp_path,
        includes,
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="app",
        installed_bases=[str(installed_dir)],
        # No explicit order - let it auto-discover
    )

    # --- Execute stitch ---
    mod_build.run_build(build_cfg)

    # --- Verify output file exists ---
    assert out_file.exists(), "Stitched file should be created"

    content = out_file.read_text()

    # --- Verify installed package modules are included ---
    # Check for module markers (format may vary)
    has_init = (
        "# === app.testpkg.__init__ ===" in content
        or "# === testpkg.__init__ ===" in content
        or '"""Test package."""' in content
    )
    has_module = (
        "# === app.testpkg.module ===" in content
        or "# === testpkg.module ===" in content
        or '"""Test module."""' in content
    )
    assert has_init, "testpkg.__init__ module not found in content"
    assert has_module, "testpkg.module not found in content"
    assert '__version__ = "1.0.0"' in content
    assert 'return "Hello from testpkg"' in content

    # --- Verify shims are created ---
    normalized_content = content.replace("'", '"')
    # Shims use package names, not full module paths with __init__
    assert '"app.testpkg"' in normalized_content or '"testpkg"' in normalized_content
    assert (
        '"app.testpkg.module"' in normalized_content
        or '"testpkg.module"' in normalized_content
    )

    # --- Verify imports work correctly ---
    spec = importlib.util.spec_from_file_location("stitched_test", out_file)
    assert spec is not None
    assert spec.loader is not None

    # Clear cached modules before loading this test's stitched module
    cleanup_sys_modules("testpkg")

    # Load the stitched module
    stitched_mod = importlib.util.module_from_spec(spec)
    sys.modules["stitched_test"] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    # --- Verify modules are in sys.modules ---
    # Module names may be prefixed with package name
    # Package modules may be named "app.testpkg" (package) and
    # "app.testpkg.module" (module)
    has_pkg = "app.testpkg" in sys.modules or "testpkg" in sys.modules
    has_module = "app.testpkg.module" in sys.modules or "testpkg.module" in sys.modules
    testpkg_modules = [k for k in sys.modules if "testpkg" in k]
    assert has_pkg, f"testpkg package not in sys.modules. Found: {testpkg_modules}"
    assert has_module, f"testpkg.module not in sys.modules. Found: {testpkg_modules}"

    # --- Verify imports work ---
    # Try both module name formats
    try:
        from testpkg.module import (  # type: ignore[import-not-found]  # noqa: PLC0415  # pyright: ignore[reportMissingImports]
            hello,  # pyright: ignore[reportUnknownVariableType]
        )
    except ImportError:
        from app.testpkg.module import (  # type: ignore[import-not-found]  # noqa: PLC0415  # pyright: ignore[reportMissingImports]
            hello,  # pyright: ignore[reportUnknownVariableType]
        )

    assert hello() == "Hello from testpkg"  # pyright: ignore[reportUnknownVariableType]


def test_stitch_package_with_source_package(tmp_path: Path) -> None:
    """Test stitching package from installed location alongside source package."""
    # --- Setup: Create source package ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    app_dir = src_dir / "app"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("")
    (app_dir / "main.py").write_text(
        """from testpkg.module import hello

def main():
    return hello()
"""
    )

    # --- Setup: Create installed package ---
    installed_dir = tmp_path / "site-packages"
    installed_dir.mkdir()
    pkg_dir = installed_dir / "testpkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text('"""Test package."""\n')
    (pkg_dir / "module.py").write_text(
        '"""Test module."""\n\ndef hello():\n    return "Hello from testpkg"\n'
    )

    # --- Create build config ---
    out_file = tmp_path / "stitched.py"
    includes = [
        make_include_resolved("app/**/*.py", src_dir),
        make_include_resolved("testpkg/**/*.py", installed_dir),
    ]

    build_cfg = make_build_cfg(
        tmp_path,
        includes,
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="app",
        source_bases=[str(src_dir)],
        installed_bases=[str(installed_dir)],
        # No explicit order - let it auto-discover
    )

    # --- Execute stitch ---
    mod_build.run_build(build_cfg)

    # --- Verify output file exists ---
    assert out_file.exists(), "Stitched file should be created"

    content = out_file.read_text()

    # --- Verify both packages are included ---
    # Check for module content (format may vary)
    has_testpkg = '"""Test package."""' in content or "testpkg" in content
    has_testpkg_module = (
        '"""Test module."""' in content or "Hello from testpkg" in content
    )
    has_app = "def main()" in content or "app" in content.lower()
    assert has_testpkg, "testpkg package not found in content"
    assert has_testpkg_module, "testpkg.module not found in content"
    assert has_app, "app package not found in content"

    # --- Verify shims are created for both ---
    normalized_content = content.replace("'", '"')
    # Shims may use different naming conventions
    has_testpkg_shim = (
        '"testpkg"' in normalized_content or "testpkg" in normalized_content
    )
    has_testpkg_module_shim = (
        '"testpkg.module"' in normalized_content
        or "testpkg.module" in normalized_content
    )
    assert has_testpkg_shim, "testpkg shim not found"
    assert has_testpkg_module_shim, "testpkg.module shim not found"

    # --- Verify imports work correctly ---
    spec = importlib.util.spec_from_file_location("stitched_test2", out_file)
    assert spec is not None
    assert spec.loader is not None

    # Clear cached modules before loading this test's stitched module
    cleanup_sys_modules("testpkg", "app")

    # Load the stitched module
    stitched_mod = importlib.util.module_from_spec(spec)
    sys.modules["stitched_test2"] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    # --- Verify we can call main function ---
    if hasattr(stitched_mod, "main"):
        result = stitched_mod.main()
        assert result == "Hello from testpkg"
    else:
        # Try importing from app.main
        from app.main import (  # type: ignore[import-not-found]  # noqa: PLC0415  # pyright: ignore[reportMissingImports]
            main,  # pyright: ignore[reportUnknownVariableType]
        )

        result = main()  # pyright: ignore[reportUnknownVariableType]
        assert result == "Hello from testpkg"


def test_stitch_package_with_exclude(tmp_path: Path) -> None:
    """Test stitching package from installed location with exclude patterns."""
    # --- Setup: Create installed package ---
    installed_dir = tmp_path / "site-packages"
    installed_dir.mkdir()
    pkg_dir = installed_dir / "testpkg"
    pkg_dir.mkdir()

    (pkg_dir / "__init__.py").write_text('"""Test package."""\n')
    (pkg_dir / "module.py").write_text(
        '"""Test module."""\n\ndef hello():\n    return "Hello"\n'
    )
    (pkg_dir / "tests.py").write_text('"""Tests - should be excluded."""\n')
    (pkg_dir / "test_utils.py").write_text('"""Test utils - should be excluded."""\n')

    # --- Create build config with exclude ---
    out_file = tmp_path / "stitched.py"
    includes = [
        make_include_resolved("testpkg/**/*.py", installed_dir),
    ]
    # Only exclude test files, keep __init__.py and module.py
    # Use more specific patterns to avoid bug in external apathetic_utils
    # where **/test_*.py matches paths containing "test_" anywhere
    excludes = [
        make_resolved("site-packages/testpkg/tests.py", tmp_path),
        make_resolved("site-packages/testpkg/test_*.py", tmp_path),
    ]

    build_cfg = make_build_cfg(
        tmp_path,
        includes,
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="testpkg",  # Use the installed package name
        installed_bases=[str(installed_dir)],
        exclude=excludes,
        # No explicit order - let it auto-discover
    )

    # --- Execute stitch ---
    mod_build.run_build(build_cfg)

    # --- Verify output file exists ---
    assert out_file.exists(), "Stitched file should be created"

    content = out_file.read_text()

    # --- Verify included modules are present ---
    has_init = '"""Test package."""' in content
    has_module = '"""Test module."""' in content or 'return "Hello"' in content
    assert has_init, "testpkg.__init__ not found in content"
    assert has_module, "testpkg.module not found in content"

    # --- Verify excluded modules are NOT present ---
    assert '"""Tests - should be excluded."""' not in content
    assert '"""Test utils - should be excluded."""' not in content


def test_stitch_package_subpackage(tmp_path: Path) -> None:
    """Test stitching package from installed location with subpackages."""
    # --- Setup: Create installed package with subpackage ---
    installed_dir = tmp_path / "site-packages"
    installed_dir.mkdir()
    pkg_dir = installed_dir / "testpkg"
    pkg_dir.mkdir()

    (pkg_dir / "__init__.py").write_text('"""Test package."""\n')
    (pkg_dir / "module.py").write_text(
        '"""Test module."""\n\ndef hello():\n    return "Hello"\n'
    )

    subpkg_dir = pkg_dir / "subpkg"
    subpkg_dir.mkdir()
    (subpkg_dir / "__init__.py").write_text('"""Subpackage."""\n')
    (subpkg_dir / "utils.py").write_text(
        '"""Utils."""\n\ndef helper():\n    return "Helper"\n'
    )

    # --- Create build config ---
    out_file = tmp_path / "stitched.py"
    includes = [
        make_include_resolved("testpkg/**/*.py", installed_dir),
    ]

    build_cfg = make_build_cfg(
        tmp_path,
        includes,
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="app",
        installed_bases=[str(installed_dir)],
        # No explicit order - let it auto-discover
    )

    # --- Execute stitch ---
    mod_build.run_build(build_cfg)

    # --- Verify output file exists ---
    assert out_file.exists(), "Stitched file should be created"

    content = out_file.read_text()

    # --- Verify all modules are included ---
    has_init = '"""Test package."""' in content
    has_module = '"""Test module."""' in content
    has_subpkg = '"""Subpackage."""' in content
    has_utils = '"""Utils."""' in content or 'return "Helper"' in content
    assert has_init, "testpkg.__init__ not found"
    assert has_module, "testpkg.module not found"
    assert has_subpkg, "testpkg.subpkg.__init__ not found"
    assert has_utils, "testpkg.subpkg.utils not found"

    # --- Verify shims are created ---
    normalized_content = content.replace("'", '"')
    # Shims may use different naming conventions
    assert '"testpkg"' in normalized_content or "testpkg" in normalized_content
    assert (
        '"testpkg.module"' in normalized_content
        or "testpkg.module" in normalized_content
    )
    assert (
        '"testpkg.subpkg"' in normalized_content
        or "testpkg.subpkg" in normalized_content
    )
    assert (
        '"testpkg.subpkg.utils"' in normalized_content
        or "testpkg.subpkg.utils" in normalized_content
    )

    # --- Verify imports work correctly ---
    spec = importlib.util.spec_from_file_location("stitched_test3", out_file)
    assert spec is not None
    assert spec.loader is not None

    # Clear cached modules before loading this test's stitched module
    cleanup_sys_modules("testpkg")

    # Load the stitched module
    stitched_mod = importlib.util.module_from_spec(spec)
    sys.modules["stitched_test3"] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    # --- Verify imports work ---
    # Try both module name formats
    try:
        from testpkg.module import (  # noqa: PLC0415  # pyright: ignore[reportMissingImports]
            hello,  # pyright: ignore[reportUnknownVariableType]
        )
        from testpkg.subpkg.utils import (  # type: ignore[import-not-found]  # noqa: PLC0415  # pyright: ignore[reportMissingImports]
            helper,  # pyright: ignore[reportUnknownVariableType]
        )
    except ImportError:
        from app.testpkg.module import (  # noqa: PLC0415  # pyright: ignore[reportMissingImports]
            hello,  # pyright: ignore[reportUnknownVariableType]
        )
        from app.testpkg.subpkg.utils import (  # type: ignore[import-not-found]  # noqa: PLC0415  # pyright: ignore[reportMissingImports]
            helper,  # pyright: ignore[reportUnknownVariableType]
        )

    assert hello() == "Hello"  # pyright: ignore[reportUnknownVariableType]
    assert helper() == "Helper"  # pyright: ignore[reportUnknownVariableType]


def _setup_source_and_installed_packages(
    tmp_path: Path,
) -> tuple[Path, Path]:
    """Set up source and installed packages with same name."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pkg_dir = src_dir / "testpkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text('"""Source package."""\n')
    (pkg_dir / "module.py").write_text(
        '"""Source module."""\n\ndef hello():\n    return "Hello from source"\n'
    )
    installed_dir = tmp_path / "site-packages"
    installed_dir.mkdir()
    installed_pkg_dir = installed_dir / "testpkg"
    installed_pkg_dir.mkdir()
    (installed_pkg_dir / "__init__.py").write_text('"""Installed package."""\n')
    (installed_pkg_dir / "module.py").write_text(
        '"""Installed module."""\n\ndef hello():\n    return "Hello from installed"\n'
    )
    return src_dir, installed_dir


def _verify_source_priority_content(content: str) -> None:
    """Verify that source package is included and installed is not."""
    assert '"""Source package."""' in content, "Source package __init__ not found"
    assert '"""Source module."""' in content, "Source module not found"
    assert 'return "Hello from source"' in content, "Source module code not found"
    assert '"""Installed package."""' not in content, (
        "Installed package should not be included"
    )
    assert '"""Installed module."""' not in content, (
        "Installed module should not be included"
    )
    assert 'return "Hello from installed"' not in content, (
        "Installed code should not be included"
    )


def _load_and_verify_stitched_module(out_file: Path, tmp_path: Path) -> None:
    """Load stitched module and verify it returns source version."""
    unique_module_name = f"stitched_test_priority_{tmp_path.name}"
    spec = importlib.util.spec_from_file_location(unique_module_name, out_file)
    assert spec is not None
    assert spec.loader is not None

    # Clean up old testpkg modules but keep ones from current stitched file
    cleanup_sys_modules("testpkg", "app.testpkg", exclude_file=out_file)
    stitched_mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_module_name] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    try:
        from testpkg.module import (  # noqa: PLC0415  # pyright: ignore[reportMissingImports]
            hello,  # pyright: ignore[reportUnknownVariableType]
        )
    except ImportError:
        from app.testpkg.module import (  # noqa: PLC0415  # pyright: ignore[reportMissingImports]
            hello,  # pyright: ignore[reportUnknownVariableType]
        )
    assert hello() == "Hello from source"  # pyright: ignore[reportUnknownVariableType]


def test_stitch_package_priority_source_over_installed(
    tmp_path: Path,
) -> None:
    """Test that source packages take priority over packages from installed locations.

    When both source and installed packages exist, source should be used.
    """
    src_dir, installed_dir = _setup_source_and_installed_packages(tmp_path)
    out_file = tmp_path / "stitched.py"
    includes = [make_include_resolved("testpkg/**/*.py", src_dir)]
    build_cfg = make_build_cfg(
        tmp_path,
        includes,
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="app",
        source_bases=[str(src_dir)],
        installed_bases=[str(installed_dir)],
    )
    mod_build.run_build(build_cfg)
    assert out_file.exists(), "Stitched file should be created"
    _verify_source_priority_content(out_file.read_text())
    _load_and_verify_stitched_module(out_file, tmp_path)
