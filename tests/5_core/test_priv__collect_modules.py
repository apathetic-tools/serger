# tests/5_core/test_priv__collect_modules.py
"""Tests for internal _collect_modules helper function."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

import tempfile
from pathlib import Path

import serger.build as mod_build
import serger.config_types as mod_config_types
import serger.stitch as mod_stitch
from tests.utils import make_include_resolved


def _setup_collect_test(
    src_dir: Path, module_names: list[str]
) -> tuple[list[Path], Path, dict[Path, mod_config_types.IncludeResolved]]:
    """Helper to set up _collect_modules test with new signature.

    Args:
        src_dir: Directory containing Python modules
        module_names: List of module names (will be converted to paths)
        package_name: Package name for config

    Returns:
        Tuple of (file_paths, package_root, file_to_include)
    """
    # Create file paths from module_names
    file_paths = [(src_dir / f"{name}.py").resolve() for name in module_names]

    # Compute package root
    package_root = mod_build.find_package_root(file_paths)

    # Create file_to_include mapping (simple - all from same root)
    file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
    include = make_include_resolved(str(src_dir.name), src_dir.parent)
    for file_path in file_paths:
        file_to_include[file_path] = include

    return file_paths, package_root, file_to_include


class TestCollectModulesBasic:
    """Test basic module collection."""

    def test_collect_simple_modules(self) -> None:
        """Should collect modules in specified order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)

            # Create modules
            (src_dir / "a.py").write_text("A = 1\n")
            (src_dir / "b.py").write_text("B = 2\n")

            file_paths, package_root, file_to_include = _setup_collect_test(
                src_dir, ["a", "b"]
            )

            (
                module_sources,
                _all_imports,
                parts,
                _derived_names,
            ) = mod_stitch._collect_modules(
                file_paths, package_root, "testpkg", file_to_include
            )

            assert "a.py" in module_sources
            assert "b.py" in module_sources
            expected_module_count = 2
            assert len(parts) == expected_module_count
            # Check order is preserved (module names derived from paths)
            assert "# === a" in parts[0] or "# === a.py ===" in parts[0]
            assert "# === b" in parts[1] or "# === b.py ===" in parts[1]

    def test_collect_with_external_imports(self) -> None:
        """Should extract external imports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)

            (src_dir / "a.py").write_text("import json\n\nA = 1\n")
            (src_dir / "b.py").write_text("from typing import List\n\nB = 2\n")

            file_paths, package_root, file_to_include = _setup_collect_test(
                src_dir, ["a", "b"]
            )

            _module_sources, all_imports, _parts, _derived_names = (
                mod_stitch._collect_modules(
                    file_paths, package_root, "testpkg", file_to_include
                )
            )

            # Check imports are collected
            import_list = list(all_imports.keys())
            assert any("json" in imp for imp in import_list)
            assert any("typing" in imp for imp in import_list)
            assert "import sys\n" in import_list  # Always added

    def test_collect_removes_internal_imports(self) -> None:
        """Should remove internal imports from module bodies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)

            (src_dir / "a.py").write_text("from testpkg.b import something\n\nA = 1\n")

            file_paths, package_root, file_to_include = _setup_collect_test(
                src_dir, ["a"]
            )

            _module_sources, _all_imports, parts, _derived_names = (
                mod_stitch._collect_modules(
                    file_paths, package_root, "testpkg", file_to_include
                )
            )

            # Internal import should be removed from body
            body = parts[0]
            assert "from testpkg.b" not in body
            assert "A = 1" in body

    def test_collect_skip_missing_module(self) -> None:
        """Should skip modules that don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)

            (src_dir / "exists.py").write_text("EXISTS = 1\n")

            file_paths, package_root, file_to_include = _setup_collect_test(
                src_dir, ["exists", "missing"]
            )
            # Add missing file to file_paths manually
            missing_path = (src_dir / "missing.py").resolve()
            file_paths.append(missing_path)

            module_sources, _all_imports, parts, _derived_names = (
                mod_stitch._collect_modules(
                    file_paths, package_root, "testpkg", file_to_include
                )
            )

            assert "exists.py" in module_sources or any(
                "exists" in k for k in module_sources
            )
            assert "missing.py" not in module_sources
            assert len(parts) == 1

    def test_collect_strips_shebangs(self) -> None:
        """Should remove shebangs and __main__ blocks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)

            (src_dir / "main.py").write_text(
                "#!/usr/bin/env python3\n\n"
                "def foo():\n"
                "    pass\n\n"
                "if __name__ == '__main__':\n"
                "    foo()\n"
            )

            file_paths, package_root, file_to_include = _setup_collect_test(
                src_dir, ["main"]
            )

            _module_sources, _all_imports, parts, _derived_names = (
                mod_stitch._collect_modules(
                    file_paths, package_root, "testpkg", file_to_include
                )
            )

            body = parts[0]
            assert "#!/usr/bin/env python3" not in body
            assert "if __name__" not in body
            assert "def foo():" in body

    def test_collect_preserves_order(self) -> None:
        """Should maintain specified module order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)

            (src_dir / "a.py").write_text("A = 1\n")
            (src_dir / "b.py").write_text("B = 2\n")
            (src_dir / "c.py").write_text("C = 3\n")

            file_paths, package_root, file_to_include = _setup_collect_test(
                src_dir, ["c", "a", "b"]
            )

            _module_sources, _all_imports, parts, _derived_names = (
                mod_stitch._collect_modules(
                    file_paths, package_root, "testpkg", file_to_include
                )
            )

            # Check order (module names derived from paths)
            c_pos = next(
                i
                for i, p in enumerate(parts)
                if "# === c" in p or "# === c.py ===" in p
            )
            a_pos = next(
                i
                for i, p in enumerate(parts)
                if "# === a" in p or "# === a.py ===" in p
            )
            b_pos = next(
                i
                for i, p in enumerate(parts)
                if "# === b" in p or "# === b.py ===" in p
            )
            assert c_pos < a_pos < b_pos


class TestCollectModulesImportHandling:
    """Test import extraction and deduplication."""

    def test_deduplicates_imports(self) -> None:
        """Should deduplicate identical imports across modules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)

            # Both modules import json
            (src_dir / "a.py").write_text("import json\n\nA = 1\n")
            (src_dir / "b.py").write_text("import json\n\nB = 2\n")

            file_paths, package_root, file_to_include = _setup_collect_test(
                src_dir, ["a", "b"]
            )

            _module_sources, all_imports, _parts, _derived_names = (
                mod_stitch._collect_modules(
                    file_paths, package_root, "testpkg", file_to_include
                )
            )

            # json should appear only once
            import_list = list(all_imports.keys())
            json_imports = [imp for imp in import_list if "json" in imp]
            assert len(json_imports) == 1

    def test_preserves_import_order(self) -> None:
        """Should preserve import order based on module order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)

            (src_dir / "a.py").write_text("import aaa\n\nA = 1\n")
            (src_dir / "b.py").write_text("import bbb\n\nB = 2\n")

            file_paths, package_root, file_to_include = _setup_collect_test(
                src_dir, ["a", "b"]
            )

            _module_sources, all_imports, _parts, _derived_names = (
                mod_stitch._collect_modules(
                    file_paths, package_root, "testpkg", file_to_include
                )
            )

            import_list = list(all_imports.keys())
            # sys should be first (always added)
            assert "import sys" in import_list[0]
            # Then imports in module order
            aaa_idx = next(i for i, imp in enumerate(import_list) if "aaa" in imp)
            bbb_idx = next(i for i, imp in enumerate(import_list) if "bbb" in imp)
            assert aaa_idx < bbb_idx

    def test_handles_multiline_imports(self) -> None:
        """Should handle multiline import statements."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)

            code = "from typing import (\n    Dict,\n    List,\n    Any,\n)\n\nA = 1\n"
            (src_dir / "a.py").write_text(code)

            file_paths, package_root, file_to_include = _setup_collect_test(
                src_dir, ["a"]
            )

            _module_sources, all_imports, _parts, _derived_names = (
                mod_stitch._collect_modules(
                    file_paths, package_root, "testpkg", file_to_include
                )
            )

            # Multiline import should be collected
            import_list = list(all_imports.keys())
            typing_imports = [imp for imp in import_list if "typing" in imp]
            assert len(typing_imports) == 1


class TestCollectModulesSources:
    """Test module source collection."""

    def test_returns_module_sources_dict(self) -> None:
        """Should return dict of module name to source."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)

            (src_dir / "a.py").write_text("A = 1\n")
            (src_dir / "b.py").write_text("B = 2\n")

            file_paths, package_root, file_to_include = _setup_collect_test(
                src_dir, ["a", "b"]
            )

            module_sources, _, _, _ = mod_stitch._collect_modules(
                file_paths, package_root, "testpkg", file_to_include
            )

            assert isinstance(module_sources, dict)
            # Module names are derived, so might be "a.py" or just "a"
            assert any("a" in k for k in module_sources)
            assert any("b" in k for k in module_sources)

    def test_sources_match_original_content(self) -> None:
        """Should preserve module content (minus redundant blocks)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)

            original = "def func():\n    return 42\n"
            (src_dir / "main.py").write_text(original)

            file_paths, package_root, file_to_include = _setup_collect_test(
                src_dir, ["main"]
            )

            module_sources, _, _, _ = mod_stitch._collect_modules(
                file_paths, package_root, "testpkg", file_to_include
            )

            # Find the module source (key might be "main.py" or derived name)
            main_source = next(v for k, v in module_sources.items() if "main" in k)
            assert "def func():" in main_source
            assert "return 42" in main_source

    def test_parts_format(self) -> None:
        """Should return parts with proper formatting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)

            (src_dir / "a.py").write_text("A = 1\n")

            file_paths, package_root, file_to_include = _setup_collect_test(
                src_dir, ["a"]
            )

            _, _, parts, _ = mod_stitch._collect_modules(
                file_paths, package_root, "testpkg", file_to_include
            )

            assert len(parts) == 1
            part = parts[0]
            # Should have header comment (module name derived from path)
            assert "# === a" in part or "# === a.py ===" in part
            # Should have code
            assert "A = 1" in part
            # Should be stripped of extra whitespace at start/end
            assert part.startswith("\n#")


class TestCollectModulesMultiPackage:
    """Test module collection with multiple packages."""

    def test_collect_multi_package_detects_all_packages(self) -> None:
        """Should detect all packages from module names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            pkg1_dir = tmp_path / "pkg1"
            pkg2_dir = tmp_path / "pkg2"
            pkg1_dir.mkdir()
            pkg2_dir.mkdir()

            (pkg1_dir / "module1.py").write_text(
                "from pkg2.module2 import func2\n\nA = 1\n"
            )
            (pkg2_dir / "module2.py").write_text("B = 2\n")

            file_paths = [
                (pkg1_dir / "module1.py").resolve(),
                (pkg2_dir / "module2.py").resolve(),
            ]
            package_root = tmp_path
            file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
            include1 = make_include_resolved("pkg1/**/*.py", tmp_path)
            include2 = make_include_resolved("pkg2/**/*.py", tmp_path)
            file_to_include[file_paths[0]] = include1
            file_to_include[file_paths[1]] = include2

            _module_sources, all_imports, _parts, _derived_names = (
                mod_stitch._collect_modules(
                    file_paths, package_root, "pkg1", file_to_include
                )
            )

            # Cross-package import should be removed (internal)
            import_list = list(all_imports.keys())
            assert not any("pkg2.module2" in imp for imp in import_list)
            # sys and types should always be present
            assert "import sys\n" in import_list
            assert "import types\n" in import_list

    def test_collect_multi_package_three_packages(self) -> None:
        """Should handle three or more packages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            pkg1_dir = tmp_path / "pkg1"
            pkg2_dir = tmp_path / "pkg2"
            pkg3_dir = tmp_path / "pkg3"
            pkg1_dir.mkdir()
            pkg2_dir.mkdir()
            pkg3_dir.mkdir()

            (pkg1_dir / "a.py").write_text("import json\n\nA = 1\n")
            (pkg2_dir / "b.py").write_text("from pkg1.a import A\n\nB = 2\n")
            (pkg3_dir / "c.py").write_text("from external import something\n\nC = 3\n")

            file_paths = [
                (pkg1_dir / "a.py").resolve(),
                (pkg2_dir / "b.py").resolve(),
                (pkg3_dir / "c.py").resolve(),
            ]
            package_root = tmp_path
            file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
            for file_path in file_paths:
                include = make_include_resolved(
                    f"{file_path.parent.name}/**/*.py", tmp_path
                )
                file_to_include[file_path] = include

            _module_sources, all_imports, _parts, _derived_names = (
                mod_stitch._collect_modules(
                    file_paths, package_root, "pkg1", file_to_include
                )
            )

            # External imports should be hoisted
            import_list = list(all_imports.keys())
            assert any("json" in imp for imp in import_list)
            assert any("external" in imp for imp in import_list)
            # Cross-package imports should be removed
            assert not any("pkg1.a" in imp for imp in import_list)
