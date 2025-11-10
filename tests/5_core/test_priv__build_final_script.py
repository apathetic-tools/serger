# tests/5_core/test_priv__build_final_script.py
"""Tests for internal _build_final_script helper function."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

from collections import OrderedDict

import serger.stitch as mod_stitch


class TestBuildFinalScriptBasic:
    """Test basic script building."""

    def test_returns_string(self) -> None:
        """Should return a string."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            license_header="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_includes_shebang(self) -> None:
        """Should start with shebang."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            license_header="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        assert result.startswith("#!/usr/bin/env python3\n")

    def test_includes_license_header(self) -> None:
        """Should include license header if provided."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        license_text = "# License: MIT"
        result = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            license_header=license_text,
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        assert license_text in result

    def test_includes_metadata_comments(self) -> None:
        """Should include version, commit, and date comments."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            license_header="",
            version="2.3.4",
            commit="def456",
            build_date="2025-06-15",
        )

        assert "# Version: 2.3.4" in result
        assert "# Commit: def456" in result
        assert "# Build Date: 2025-06-15" in result


class TestBuildFinalScriptMetadata:
    """Test metadata embedding."""

    def test_embeds_version_constant(self) -> None:
        """Should embed __version__ constant."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            license_header="",
            version="3.2.1",
            commit="abc123",
            build_date="2025-01-01",
        )

        assert '__version__ = "3.2.1"' in result

    def test_embeds_commit_constant(self) -> None:
        """Should embed __commit__ constant."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            license_header="",
            version="1.0.0",
            commit="xyz789",
            build_date="2025-01-01",
        )

        assert '__commit__ = "xyz789"' in result

    def test_embeds_build_date_constant(self) -> None:
        """Should embed __build_date__ constant."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            license_header="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-12-25 15:30:00 UTC",
        )

        assert '__build_date__ = "2025-12-25 15:30:00 UTC"' in result

    def test_embeds_standalone_flag(self) -> None:
        """Should embed __STANDALONE__ = True flag."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            license_header="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        assert "__STANDALONE__ = True" in result


class TestBuildFinalScriptImports:
    """Test import handling."""

    def test_separates_future_imports(self) -> None:
        """Should place __future__ imports before other imports."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None
        all_imports["from __future__ import annotations\n"] = None
        all_imports["import json\n"] = None

        result = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            license_header="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        # __future__ should come before other imports
        future_pos = result.find("from __future__")
        sys_pos = result.find("import sys")
        assert future_pos < sys_pos

    def test_includes_all_imports(self) -> None:
        """Should include all external imports."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None
        all_imports["import json\n"] = None
        all_imports["from typing import List\n"] = None

        result = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            license_header="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        assert "import sys" in result
        assert "import json" in result
        assert "from typing import List" in result


class TestBuildFinalScriptShims:
    """Test import shim generation."""

    def test_generates_shim_block(self) -> None:
        """Should generate import shim block."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            license_header="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        assert "# --- import shims for single-file runtime ---" in result

    def test_shim_includes_public_modules(self) -> None:
        """Should create shims for public modules."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result = mod_stitch._build_final_script(
            package_name="mylib",
            all_imports=all_imports,
            parts=[
                "# === utils.py ===\nUTILS = 1\n",
                "# === core.py ===\nCORE = 2\n",
            ],
            order_names=["utils", "core"],
            license_header="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        # Check for f-string with curly braces {_pkg}
        assert "sys.modules[f'{_pkg}.utils']" in result
        assert "sys.modules[f'{_pkg}.core']" in result

    def test_shim_excludes_private_modules(self) -> None:
        """Should not create shims for private modules."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result = mod_stitch._build_final_script(
            package_name="mylib",
            all_imports=all_imports,
            parts=[
                "# === public.py ===\nPUBLIC = 1\n",
                "# === _private.py ===\nPRIVATE = 2\n",
            ],
            order_names=["public", "_private"],
            license_header="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        # Check for f-string with curly braces {_pkg}
        assert "sys.modules[f'{_pkg}.public']" in result
        assert "sys.modules[f'{_pkg}._private']" not in result

    def test_shim_package_name(self) -> None:
        """Should use correct package name in shims."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result = mod_stitch._build_final_script(
            package_name="custompackage",
            all_imports=all_imports,
            parts=["# === mod.py ===\nMOD = 1\n"],
            order_names=["mod"],
            license_header="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        assert "_pkg = 'custompackage'" in result


class TestBuildFinalScriptParts:
    """Test module parts inclusion."""

    def test_includes_all_module_parts(self) -> None:
        """Should include all provided module parts."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=[
                "# === a.py ===\nA = 1\n",
                "# === b.py ===\nB = 2\n",
                "# === c.py ===\nC = 3\n",
            ],
            order_names=["a", "b", "c"],
            license_header="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        assert "# === a.py ===" in result
        assert "A = 1" in result
        assert "# === b.py ===" in result
        assert "B = 2" in result
        assert "# === c.py ===" in result
        assert "C = 3" in result

    def test_preserves_module_order_in_output(self) -> None:
        """Should maintain module order in final script."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=[
                "# === c.py ===\nC = 3\n",
                "# === a.py ===\nA = 1\n",
                "# === b.py ===\nB = 2\n",
            ],
            order_names=["c", "a", "b"],
            license_header="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        c_pos = result.find("# === c.py ===")
        a_pos = result.find("# === a.py ===")
        b_pos = result.find("# === b.py ===")
        assert c_pos < a_pos < b_pos


class TestBuildFinalScriptDocstring:
    """Test script docstring generation."""

    def test_includes_docstring(self) -> None:
        """Should include a module docstring."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            license_header="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        assert '"""' in result or "'''" in result
        assert "testpkg" in result

    def test_docstring_includes_metadata(self) -> None:
        """Should include metadata in docstring."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            license_header="",
            version="5.6.7",
            commit="ghijkl",
            build_date="2025-09-30",
        )

        docstring = result[result.find('"""') : result.rfind('"""') + 3]
        assert "5.6.7" in docstring
        assert "ghijkl" in docstring
        assert "2025-09-30" in docstring
