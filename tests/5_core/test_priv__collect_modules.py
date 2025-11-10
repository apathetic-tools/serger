# tests/5_core/test_priv__collect_modules.py
"""Tests for internal _collect_modules helper function."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

import tempfile
from pathlib import Path

import serger.stitch as mod_stitch


class TestCollectModulesBasic:
    """Test basic module collection."""

    def test_collect_simple_modules(self) -> None:
        """Should collect modules in specified order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)

            # Create modules
            (src_dir / "a.py").write_text("A = 1\n")
            (src_dir / "b.py").write_text("B = 2\n")

            module_sources, _all_imports, parts = mod_stitch._collect_modules(
                src_dir, ["a", "b"], "testpkg"
            )

            assert "a.py" in module_sources
            assert "b.py" in module_sources
            expected_module_count = 2
            assert len(parts) == expected_module_count
            # Check order is preserved
            assert "# === a.py ===" in parts[0]
            assert "# === b.py ===" in parts[1]

    def test_collect_with_external_imports(self) -> None:
        """Should extract external imports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)

            (src_dir / "a.py").write_text("import json\n\nA = 1\n")
            (src_dir / "b.py").write_text("from typing import List\n\nB = 2\n")

            _module_sources, all_imports, _parts = mod_stitch._collect_modules(
                src_dir, ["a", "b"], "testpkg"
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

            _module_sources, _all_imports, parts = mod_stitch._collect_modules(
                src_dir, ["a"], "testpkg"
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

            module_sources, _all_imports, parts = mod_stitch._collect_modules(
                src_dir, ["exists", "missing"], "testpkg"
            )

            assert "exists.py" in module_sources
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

            _module_sources, _all_imports, parts = mod_stitch._collect_modules(
                src_dir, ["main"], "testpkg"
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

            _module_sources, _all_imports, parts = mod_stitch._collect_modules(
                src_dir, ["c", "a", "b"], "testpkg"
            )

            # Check order
            c_pos = next(i for i, p in enumerate(parts) if "# === c.py ===" in p)
            a_pos = next(i for i, p in enumerate(parts) if "# === a.py ===" in p)
            b_pos = next(i for i, p in enumerate(parts) if "# === b.py ===" in p)
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

            _module_sources, all_imports, _parts = mod_stitch._collect_modules(
                src_dir, ["a", "b"], "testpkg"
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

            _module_sources, all_imports, _parts = mod_stitch._collect_modules(
                src_dir, ["a", "b"], "testpkg"
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

            _module_sources, all_imports, _parts = mod_stitch._collect_modules(
                src_dir, ["a"], "testpkg"
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

            module_sources, _, _ = mod_stitch._collect_modules(
                src_dir, ["a", "b"], "testpkg"
            )

            assert isinstance(module_sources, dict)
            assert "a.py" in module_sources
            assert "b.py" in module_sources

    def test_sources_match_original_content(self) -> None:
        """Should preserve module content (minus redundant blocks)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)

            original = "def func():\n    return 42\n"
            (src_dir / "main.py").write_text(original)

            module_sources, _, _ = mod_stitch._collect_modules(
                src_dir, ["main"], "testpkg"
            )

            assert "def func():" in module_sources["main.py"]
            assert "return 42" in module_sources["main.py"]

    def test_parts_format(self) -> None:
        """Should return parts with proper formatting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)

            (src_dir / "a.py").write_text("A = 1\n")

            _, _, parts = mod_stitch._collect_modules(src_dir, ["a"], "testpkg")

            assert len(parts) == 1
            part = parts[0]
            # Should have header comment
            assert "# === a.py ===" in part
            # Should have code
            assert "A = 1" in part
            # Should be stripped of extra whitespace at start/end
            assert part.startswith("\n#")
