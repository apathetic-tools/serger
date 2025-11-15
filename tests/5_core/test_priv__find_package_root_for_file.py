# tests/5_core/test_priv__find_package_root_for_file.py
"""Tests for _find_package_root_for_file helper function."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

import tempfile
from pathlib import Path

import serger.stitch as mod_stitch


class TestFindPackageRootForFile:
    """Tests for _find_package_root_for_file helper function."""

    def test_finds_package_root_with_init_py(self) -> None:
        """Should find package root when __init__.py exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = Path(tmpdir) / "mypkg"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("# package\n")
            module_file = pkg_dir / "module.py"
            module_file.write_text("# module\n")

            result = mod_stitch._find_package_root_for_file(module_file)

            assert result == pkg_dir.resolve()

    def test_finds_nested_package_root(self) -> None:
        """Should find topmost package root in nested structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            outer_pkg = Path(tmpdir) / "outer"
            outer_pkg.mkdir()
            (outer_pkg / "__init__.py").write_text("# outer\n")
            inner_pkg = outer_pkg / "inner"
            inner_pkg.mkdir()
            (inner_pkg / "__init__.py").write_text("# inner\n")
            module_file = inner_pkg / "module.py"
            module_file.write_text("# module\n")

            result = mod_stitch._find_package_root_for_file(module_file)

            # Should return the topmost package (outer)
            assert result == outer_pkg.resolve()

    def test_returns_none_when_no_init_py(self) -> None:
        """Should return None when no __init__.py found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = Path(tmpdir) / "mypkg"
            pkg_dir.mkdir()
            # No __init__.py
            module_file = pkg_dir / "module.py"
            module_file.write_text("# module\n")

            result = mod_stitch._find_package_root_for_file(module_file)

            assert result is None

    def test_handles_file_in_root_directory(self) -> None:
        """Should handle files at filesystem root (edge case)."""
        # This is unlikely in practice but should not crash
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "script.py"
            root_file.write_text("# script\n")

            result = mod_stitch._find_package_root_for_file(root_file)

            # No __init__.py at root, so should return None
            assert result is None

    def test_stops_at_first_missing_init_py(self) -> None:
        """Should stop walking up when __init__.py is missing.

        The function starts from the file's directory and walks up.
        If the file's directory doesn't have __init__.py, it returns None
        immediately (doesn't check parent). This is the current behavior.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create structure: outer/__init__.py, outer/inner/ (no __init__.py)
            outer_pkg = Path(tmpdir) / "outer"
            outer_pkg.mkdir()
            (outer_pkg / "__init__.py").write_text("# outer\n")
            inner_dir = outer_pkg / "inner"
            inner_dir.mkdir()
            # No __init__.py in inner
            module_file = inner_dir / "module.py"
            module_file.write_text("# module\n")

            result = mod_stitch._find_package_root_for_file(module_file)

            # Current behavior: starts from inner/, finds no __init__.py,
            # returns None immediately (doesn't check parent outer/)
            # This is actually correct - inner/ is not a package, so the file
            # is not in a package. The outer package would be detected if
            # we had a file directly in outer/.
            assert result is None

    def test_handles_init_py_in_same_directory(self) -> None:
        """Should find package when __init__.py is in same directory as file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = Path(tmpdir) / "mypkg"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("# package\n")
            # File in same directory as __init__.py
            module_file = pkg_dir / "module.py"
            module_file.write_text("# module\n")

            result = mod_stitch._find_package_root_for_file(module_file)

            assert result == pkg_dir.resolve()
