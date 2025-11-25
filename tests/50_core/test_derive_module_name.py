# tests/50_core/test_derive_module_name.py
"""Tests for derive_module_name() module name derivation."""

# we import `_` private for testing purposes only
# pyright: reportPrivateUsage=false

from pathlib import Path

import serger.utils.utils_modules as mod_utils_modules
from tests.utils.buildconfig import make_include_resolved


def test_derive_preserves_directory_structure(tmp_path: Path) -> None:
    """Should preserve directory structure in module name."""
    # --- setup ---
    src = tmp_path / "src"
    core = src / "core"
    core.mkdir(parents=True)
    file_path = core / "base.py"
    file_path.write_text("BASE = 1")
    package_root = src

    # --- execute ---
    result = mod_utils_modules.derive_module_name(file_path, package_root)

    # --- verify ---
    assert result == "core.base"


def test_derive_top_level_file(tmp_path: Path) -> None:
    """Should derive simple name for top-level file."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    file_path = src / "main.py"
    file_path.write_text("MAIN = 1")
    package_root = src

    # --- execute ---
    result = mod_utils_modules.derive_module_name(file_path, package_root)

    # --- verify ---
    assert result == "main"


def test_derive_with_dest_override(tmp_path: Path) -> None:
    """Should use dest path structure when dest is provided."""
    # --- setup ---
    src = tmp_path / "src"
    core = src / "core"
    core.mkdir(parents=True)
    file_path = core / "base.py"
    file_path.write_text("BASE = 1")
    package_root = src
    include = make_include_resolved(
        "src/core/base.py", tmp_path, dest="custom/sub/base.py"
    )

    # --- execute ---
    result = mod_utils_modules.derive_module_name(file_path, package_root, include)

    # --- verify ---
    # Module name should come from dest structure, not file path
    assert result == "custom.sub.base"


def test_derive_file_not_under_root(tmp_path: Path) -> None:
    """Should use just filename when file not under package root."""
    # --- setup ---
    file_path = tmp_path / "outside.py"
    file_path.write_text("OUTSIDE = 1")
    package_root = tmp_path / "src"  # Different root

    # --- execute ---
    result = mod_utils_modules.derive_module_name(file_path, package_root)

    # --- verify ---
    assert result == "outside"


def test_derive_nested_structure(tmp_path: Path) -> None:
    """Should handle deeply nested directory structures."""
    # --- setup ---
    src = tmp_path / "src"
    deep = src / "a" / "b" / "c"
    deep.mkdir(parents=True)
    file_path = deep / "module.py"
    file_path.write_text("MODULE = 1")
    package_root = src

    # --- execute ---
    result = mod_utils_modules.derive_module_name(file_path, package_root)

    # --- verify ---
    assert result == "a.b.c.module"


def test_derive_with_dest_glob_pattern(tmp_path: Path) -> None:
    """Should handle dest with glob pattern interpretation."""
    # --- setup ---
    src = tmp_path / "src"
    core = src / "core"
    core.mkdir(parents=True)
    file_path = core / "base.py"
    file_path.write_text("BASE = 1")
    package_root = src
    # dest with glob-like pattern
    include = make_include_resolved("src/core/*.py", tmp_path, dest="custom")

    # --- execute ---
    result = mod_utils_modules.derive_module_name(file_path, package_root, include)

    # --- verify ---
    # Should interpret dest relative to glob prefix
    assert result == "custom.base"


def test_derive_external_file_with_source_bases(tmp_path: Path) -> None:
    """Should use source_bases to derive module name for external files."""
    # --- setup ---
    # Create external project structure
    external_proj = tmp_path / "external_proj"
    external_src = external_proj / "src"
    external_pkg = external_src / "mypkg"
    external_pkg.mkdir(parents=True)
    external_file = external_pkg / "module.py"
    external_file.write_text("MODULE = 1")

    # Current project (different location)
    current_proj = tmp_path / "current_proj"
    current_proj.mkdir()
    package_root = current_proj  # package_root is in current project

    # source_bases points to external project src
    source_bases = [str(external_src)]

    # --- execute ---
    # File is external (not under package_root), but should use source_bases
    result = mod_utils_modules.derive_module_name(
        external_file, package_root, source_bases=source_bases
    )

    # --- verify ---
    # Should derive relative to module_base, not use full absolute path
    assert result == "mypkg.module"
    # Should NOT contain full absolute path parts
    assert "external_proj" not in result
    assert "current_proj" not in result


def test_derive_external_file_under_common_package_root(tmp_path: Path) -> None:
    """Should prioritize source_bases even when file is under package_root.

    This tests the case where package_root is computed as the common ancestor
    of both local and external files, so the external file IS under package_root.
    In this case, source_bases should still be used to derive the module name.
    """
    # --- setup ---
    # Create external project structure
    external_proj = tmp_path / "home" / "user" / "external_proj"
    external_src = external_proj / "src"
    external_pkg = external_src / "apathetic_logging"
    external_pkg.mkdir(parents=True)
    external_file = external_pkg / "register_logger_name.py"
    external_file.write_text("def register(): pass")

    # Current project (under same common ancestor)
    current_proj = tmp_path / "home" / "user" / "current_proj"
    current_src = current_proj / "src"
    current_src.mkdir(parents=True)
    local_file = current_src / "app.py"
    local_file.write_text("import apathetic_logging")

    # package_root is common ancestor (includes both projects)
    package_root = tmp_path / "home" / "user"
    # source_bases points to external project src
    source_bases = [str(external_src)]

    # --- execute ---
    # File IS under package_root, but should still use source_bases
    result = mod_utils_modules.derive_module_name(
        external_file, package_root, source_bases=source_bases
    )

    # --- verify ---
    # Should derive relative to module_base, not from package_root
    assert result == "apathetic_logging.register_logger_name"
    # Should NOT contain full absolute path parts from package_root
    assert "home" not in result
    assert "user" not in result
    assert "external_proj" not in result
    assert "current_proj" not in result
