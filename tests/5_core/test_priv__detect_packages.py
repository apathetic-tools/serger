# tests/5_core/test_priv__detect_packages.py
"""Tests for package detection helper functions."""

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


class TestDetectPackagesFromFiles:
    """Tests for _detect_packages_from_files function."""

    def test_detects_single_package(self) -> None:
        """Should detect single package from __init__.py files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = Path(tmpdir) / "mypkg"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("# package\n")
            module_file = pkg_dir / "module.py"
            module_file.write_text("# module\n")

            result = mod_stitch._detect_packages_from_files([module_file], "mypkg")

            assert result == {"mypkg"}

    def test_detects_multiple_packages(self) -> None:
        """Should detect multiple packages from different files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg1_dir = Path(tmpdir) / "pkg1"
            pkg1_dir.mkdir()
            (pkg1_dir / "__init__.py").write_text("# pkg1\n")
            file1 = pkg1_dir / "module1.py"
            file1.write_text("# module1\n")

            pkg2_dir = Path(tmpdir) / "pkg2"
            pkg2_dir.mkdir()
            (pkg2_dir / "__init__.py").write_text("# pkg2\n")
            file2 = pkg2_dir / "module2.py"
            file2.write_text("# module2\n")

            result = mod_stitch._detect_packages_from_files([file1, file2], "default")

            assert result == {"pkg1", "pkg2", "default"}

    def test_falls_back_to_configured_package(self) -> None:
        """Should always include configured package name as fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # No __init__.py files
            loose_file = Path(tmpdir) / "script.py"
            loose_file.write_text("# script\n")

            result = mod_stitch._detect_packages_from_files(
                [loose_file], "configured_pkg"
            )

            # Should include configured package even if no __init__.py found
            assert "configured_pkg" in result
            assert result == {"configured_pkg"}

    def test_detects_nested_packages_correctly(self) -> None:
        """Should detect top-level package in nested structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            outer_pkg = Path(tmpdir) / "outer"
            outer_pkg.mkdir()
            (outer_pkg / "__init__.py").write_text("# outer\n")
            inner_pkg = outer_pkg / "inner"
            inner_pkg.mkdir()
            (inner_pkg / "__init__.py").write_text("# inner\n")
            file1 = outer_pkg / "module1.py"
            file1.write_text("# module1\n")
            file2 = inner_pkg / "module2.py"
            file2.write_text("# module2\n")

            result = mod_stitch._detect_packages_from_files([file1, file2], "default")

            # Should detect "outer" (top-level package) for both files
            assert "outer" in result
            assert "default" in result
            # Should not detect "inner" as separate package (it's nested)

    def test_handles_mixed_packages_and_loose_files(self) -> None:
        """Should handle mix of package files and loose files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Package file
            pkg_dir = Path(tmpdir) / "mypkg"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("# package\n")
            pkg_file = pkg_dir / "module.py"
            pkg_file.write_text("# module\n")

            # Loose file (no __init__.py)
            loose_dir = Path(tmpdir) / "loose"
            loose_dir.mkdir()
            loose_file = loose_dir / "script.py"
            loose_file.write_text("# script\n")

            result = mod_stitch._detect_packages_from_files(
                [pkg_file, loose_file], "default"
            )

            # Should detect "mypkg" and include "default" as fallback
            assert "mypkg" in result
            assert "default" in result
            assert len(result) == 2  # noqa: PLR2004

    def test_detects_same_package_from_multiple_files(self) -> None:
        """Should detect package once even with multiple files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = Path(tmpdir) / "mypkg"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("# package\n")
            file1 = pkg_dir / "module1.py"
            file1.write_text("# module1\n")
            file2 = pkg_dir / "module2.py"
            file2.write_text("# module2\n")
            file3 = pkg_dir / "module3.py"
            file3.write_text("# module3\n")

            result = mod_stitch._detect_packages_from_files(
                [file1, file2, file3], "mypkg"
            )

            # Should only have "mypkg" once (plus configured package)
            assert result == {"mypkg"}

    def test_empty_file_list_returns_configured_package(self) -> None:
        """Should return configured package when no files provided."""
        result = mod_stitch._detect_packages_from_files([], "default_pkg")

        assert result == {"default_pkg"}

    def test_deterministic_output_order(self) -> None:
        """Should produce deterministic results (for build reproducibility)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg1_dir = Path(tmpdir) / "pkg1"
            pkg1_dir.mkdir()
            (pkg1_dir / "__init__.py").write_text("# pkg1\n")
            file1 = pkg1_dir / "module1.py"
            file1.write_text("# module1\n")

            pkg2_dir = Path(tmpdir) / "pkg2"
            pkg2_dir.mkdir()
            (pkg2_dir / "__init__.py").write_text("# pkg2\n")
            file2 = pkg2_dir / "module2.py"
            file2.write_text("# module2\n")

            # Call multiple times with different file order
            result1 = mod_stitch._detect_packages_from_files([file1, file2], "default")
            result2 = mod_stitch._detect_packages_from_files([file2, file1], "default")

            # Results should be identical (sets are unordered, but contents same)
            assert result1 == result2
            assert sorted(result1) == sorted(result2)
