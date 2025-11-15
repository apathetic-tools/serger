# tests/5_core/test_detect_packages_from_files.py
"""Tests for detect_packages_from_files function."""

import tempfile
from pathlib import Path

import serger.stitch as mod_stitch


class TestDetectPackagesFromFiles:
    """Tests for detect_packages_from_files function."""

    def test_detects_single_package(self) -> None:
        """Should detect single package from __init__.py files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = Path(tmpdir) / "mypkg"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("# package\n")
            module_file = pkg_dir / "module.py"
            module_file.write_text("# module\n")

            result = mod_stitch.detect_packages_from_files([module_file], "mypkg")

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

            result = mod_stitch.detect_packages_from_files([file1, file2], "default")

            assert result == {"pkg1", "pkg2", "default"}

    def test_falls_back_to_configured_package(self) -> None:
        """Should always include configured package name as fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # No __init__.py files
            loose_file = Path(tmpdir) / "script.py"
            loose_file.write_text("# script\n")

            result = mod_stitch.detect_packages_from_files(
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

            result = mod_stitch.detect_packages_from_files([file1, file2], "default")

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

            result = mod_stitch.detect_packages_from_files(
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

            result = mod_stitch.detect_packages_from_files(
                [file1, file2, file3], "mypkg"
            )

            # Should only have "mypkg" once (plus configured package)
            assert result == {"mypkg"}

    def test_empty_file_list_returns_configured_package(self) -> None:
        """Should return configured package when no files provided."""
        result = mod_stitch.detect_packages_from_files([], "default_pkg")

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
            result1 = mod_stitch.detect_packages_from_files([file1, file2], "default")
            result2 = mod_stitch.detect_packages_from_files([file2, file1], "default")

            # Results should be identical (sets are unordered, but contents same)
            assert result1 == result2
            assert sorted(result1) == sorted(result2)
