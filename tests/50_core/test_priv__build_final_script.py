# tests/50_core/test_priv__build_final_script.py
"""Tests for internal _build_final_script helper function."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

from collections import OrderedDict
from pathlib import Path

import serger.stitch as mod_stitch
from tests.utils.build_final_script import (
    call_build_final_script,
)
from tests.utils.buildconfig import make_build_cfg, make_include_resolved


class TestBuildFinalScriptBasic:
    """Test basic script building."""

    def test_returns_string(self, tmp_path: Path) -> None:
        """Should return a string."""
        result, _ = call_build_final_script(tmp_path=tmp_path)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_includes_shebang(self, tmp_path: Path) -> None:
        """Should start with shebang."""
        result, _ = call_build_final_script(tmp_path=tmp_path)

        assert result.startswith("#!/usr/bin/env python3\n")

    def test_includes_license(self) -> None:
        """Should include license if provided."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        license_text = "MIT"
        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text=license_text,
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        # Single line format: "License: <text>"
        assert "# License: MIT" in result

    def test_includes_license_multi_line(self) -> None:
        """Should format multi-line license as block."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        license_text = (
            "MIT License\n\nCopyright (c) 2024 Test Author\nAll rights reserved."
        )
        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text=license_text,
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        # Multi-line format: ====LICENSE==== block
        assert "# ============LICENSE=============" in result
        assert "# ================================" in result
        assert "# MIT License" in result
        assert "# Copyright (c) 2024 Test Author" in result
        assert "# All rights reserved." in result

    def test_includes_metadata_comments(self) -> None:
        """Should include version, commit, and date comments."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="2.3.4",
            commit="def456",
            build_date="2025-06-15",
        )

        assert "# Version: 2.3.4" in result
        assert "# Commit: def456" in result
        assert "# Build Date: 2025-06-15" in result

    def test_includes_authors_comment(self, tmp_path: Path) -> None:
        """Should include authors comment when provided."""
        result, _ = call_build_final_script(
            tmp_path=tmp_path,
            authors="Alice <alice@example.com>, Bob",
        )

        assert "# Authors: Alice <alice@example.com>, Bob" in result

    def test_omits_authors_comment_when_empty(self, tmp_path: Path) -> None:
        """Should omit authors comment when not provided."""
        result, _ = call_build_final_script(tmp_path=tmp_path, authors="")

        assert "# Authors:" not in result


class TestBuildFinalScriptMetadata:
    """Test metadata embedding."""

    def test_embeds_version_constant(self) -> None:
        """Should embed __version__ constant."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="3.2.1",
            commit="abc123",
            build_date="2025-01-01",
        )

        assert '__version__ = "3.2.1"' in result

    def test_embeds_commit_constant(self) -> None:
        """Should embed __commit__ constant."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="1.0.0",
            commit="xyz789",
            build_date="2025-01-01",
        )

        assert '__commit__ = "xyz789"' in result

    def test_embeds_build_date_constant(self) -> None:
        """Should embed __build_date__ constant."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-12-25 15:30:00 UTC",
        )

        assert '__build_date__ = "2025-12-25 15:30:00 UTC"' in result

    def test_embeds_authors_constant(self, tmp_path: Path) -> None:
        """Should embed __AUTHORS__ constant when provided."""
        result, _ = call_build_final_script(
            tmp_path=tmp_path,
            authors="Alice <alice@example.com>, Bob",
        )

        assert '__AUTHORS__ = "Alice <alice@example.com>, Bob"' in result

    def test_omits_authors_constant_when_empty(self, tmp_path: Path) -> None:
        """Should omit __AUTHORS__ constant when not provided."""
        result, _ = call_build_final_script(tmp_path=tmp_path, authors="")

        assert "__AUTHORS__" not in result

    def test_embeds_standalone_flag(self) -> None:
        """Should embed __STANDALONE__ = True flag."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
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

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
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

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
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

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        assert "# --- import shims for single-file runtime ---" in result

    def test_shim_includes_public_modules(self) -> None:
        """Should create shims for public modules."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result, _ = mod_stitch._build_final_script(
            package_name="mylib",
            all_imports=all_imports,
            parts=[
                "# === utils.py ===\nUTILS = 1\n",
                "# === core.py ===\nCORE = 2\n",
            ],
            order_names=["utils", "core"],
            all_function_names=set(),
            detected_packages={"mylib"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        # Check for loop-based shim generation (module names include package prefix)
        # The shims are now generated as: for _name in [...]: sys.modules[_name] = _mod
        assert "for _name in" in result
        assert "sys.modules[_name] = _mod" in result
        assert "'mylib.utils'" in result or '"mylib.utils"' in result
        assert "'mylib.core'" in result or '"mylib.core"' in result

    def test_shim_includes_private_modules(self) -> None:
        """Should create shims for all modules, including private ones.

        This matches installed package behavior where private modules
        are accessible. If specific modules should be excluded,
        use the 'exclude' config option.
        """
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result, _ = mod_stitch._build_final_script(
            package_name="mylib",
            all_imports=all_imports,
            parts=[
                "# === public.py ===\nPUBLIC = 1\n",
                "# === _private.py ===\nPRIVATE = 2\n",
            ],
            order_names=["public", "_private"],
            all_function_names=set(),
            detected_packages={"mylib"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        # Check for loop-based shim generation
        # The shims are now generated as: for _name in [...]: sys.modules[_name] = _mod
        assert "for _name in" in result
        assert "sys.modules[_name] = _mod" in result
        assert "'mylib.public'" in result or '"mylib.public"' in result
        # Private should also have shim (matching installed package behavior)
        assert "'mylib._private'" in result or '"_private"' in result

    def test_shim_package_name(self) -> None:
        """Should use correct package name in shims."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result, _ = mod_stitch._build_final_script(
            package_name="custompackage",
            all_imports=all_imports,
            parts=["# === mod.py ===\nMOD = 1\n"],
            order_names=["mod"],
            all_function_names=set(),
            detected_packages={"custompackage"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
        )

        assert "_create_pkg_module('custompackage')" in result


class TestBuildFinalScriptParts:
    """Test module parts inclusion."""

    def test_includes_all_module_parts(self) -> None:
        """Should include all provided module parts."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=[
                "# === a.py ===\nA = 1\n",
                "# === b.py ===\nB = 2\n",
                "# === c.py ===\nC = 3\n",
            ],
            order_names=["a", "b", "c"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
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

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=[
                "# === c.py ===\nC = 3\n",
                "# === a.py ===\nA = 1\n",
                "# === b.py ===\nB = 2\n",
            ],
            order_names=["c", "a", "b"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
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

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
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

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="5.6.7",
            commit="ghijkl",
            build_date="2025-09-30",
        )

        docstring = result[result.find('"""') : result.rfind('"""') + 3]
        assert "5.6.7" in docstring
        assert "ghijkl" in docstring
        assert "2025-09-30" in docstring

    def test_custom_header_overrides_formatting(self, tmp_path: Path) -> None:
        """Should use custom_header when provided in config."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        config = make_build_cfg(
            tmp_path,
            include=[make_include_resolved("src", tmp_path)],
            package="testpkg",
            custom_header="My Custom Header",
        )

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
            config=config,
        )

        lines = result.split("\n")
        # Docstring now comes first (after shebang) per PEP 8
        # Header comment comes after the docstring
        assert lines[1] == '"""'
        # Find the header comment after the docstring closes
        header_found = False
        for i, line in enumerate(lines):
            if line == "# My Custom Header":
                header_found = True
                # Header should come after docstring (which starts on line 1)
                assert i > 1
                break
        assert header_found, "Custom header not found in output"

    def test_file_docstring_overrides_auto_generated(self, tmp_path: Path) -> None:
        """Should use file_docstring when provided in config."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        config = make_build_cfg(
            tmp_path,
            include=[make_include_resolved("src", tmp_path)],
            package="testpkg",
            file_docstring="Custom docstring\nwith multiple lines",
        )

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\nMAIN = 1\n"],
            order_names=["main"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
            config=config,
        )

        # Find the docstring section
        docstring_start = result.find('"""')
        docstring_end = result.find('"""', docstring_start + 3)
        docstring_content = result[docstring_start + 3 : docstring_end]
        assert "Custom docstring" in docstring_content
        assert "with multiple lines" in docstring_content
        # Should not contain auto-generated content
        assert "This single-file version is auto-generated" not in docstring_content


class TestBuildFinalScriptMainShim:
    """Test main() shim generation."""

    def test_main_shim_added_when_main_function_exists(self, tmp_path: Path) -> None:
        """Should add main() shim when main() function is present."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        config = make_build_cfg(
            tmp_path,
            include=[make_include_resolved("src", tmp_path)],
            package="testpkg",
            main_mode="auto",
            main_name=None,
        )

        source = "def main():\n    return 0\n"
        module_sources = {"main.py": source}
        main_file = tmp_path / "src" / "main.py"
        main_function_result = ("main", main_file, "main")

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\ndef main():\n    return 0\n"],
            order_names=["main"],
            all_function_names={"main"},
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
            config=config,
            main_function_result=main_function_result,
            module_sources=module_sources,
        )

        # Should include the main() shim
        assert "if __name__ == '__main__':" in result
        assert "sys.exit(main())" in result  # No params, so no sys.argv[1:]

    def test_main_shim_with_params_uses_sys_argv(self, tmp_path: Path) -> None:
        """Should use sys.argv[1:] when main function has parameters."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        config = make_build_cfg(
            tmp_path,
            include=[make_include_resolved("src", tmp_path)],
            package="testpkg",
            main_mode="auto",
            main_name=None,
        )

        source = "def main(args):\n    return 0\n"
        module_sources = {"main.py": source}
        main_file = tmp_path / "src" / "main.py"
        main_function_result = ("main", main_file, "main")

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\ndef main(args):\n    return 0\n"],
            order_names=["main"],
            all_function_names={"main"},
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
            config=config,
            main_function_result=main_function_result,
            module_sources=module_sources,
        )

        # Should include the main() shim with sys.argv[1:]
        assert "if __name__ == '__main__':" in result
        assert "sys.exit(main(sys.argv[1:]))" in result

    def test_main_shim_with_star_args_uses_sys_argv(self, tmp_path: Path) -> None:
        """Should use sys.argv[1:] when main function has *args."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        config = make_build_cfg(
            tmp_path,
            include=[make_include_resolved("src", tmp_path)],
            package="testpkg",
            main_mode="auto",
            main_name=None,
        )

        source = "def main(*args):\n    return 0\n"
        module_sources = {"main.py": source}
        main_file = tmp_path / "src" / "main.py"
        main_function_result = ("main", main_file, "main")

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\ndef main(*args):\n    return 0\n"],
            order_names=["main"],
            all_function_names={"main"},
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
            config=config,
            main_function_result=main_function_result,
            module_sources=module_sources,
        )

        # Should include the main() shim with sys.argv[1:]
        assert "if __name__ == '__main__':" in result
        assert "sys.exit(main(sys.argv[1:]))" in result

    def test_main_mode_none_no_shim(self, tmp_path: Path) -> None:
        """Should not add main() shim when main_mode is 'none'."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        config = make_build_cfg(
            tmp_path,
            include=[make_include_resolved("src", tmp_path)],
            package="testpkg",
            main_mode="none",  # main_mode="none"
            main_name=None,
        )

        source = "def main():\n    return 0\n"
        module_sources = {"main.py": source}
        main_file = tmp_path / "src" / "main.py"
        main_function_result = ("main", main_file, "main")

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === main.py ===\ndef main():\n    return 0\n"],
            order_names=["main"],
            all_function_names={"main"},
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
            config=config,
            main_function_result=main_function_result,
            module_sources=module_sources,
        )

        # Should NOT include the main() shim when main_mode="none"
        assert "if __name__ == '__main__':" not in result
        assert "sys.exit(main(" not in result

    def test_main_shim_not_added_when_no_main_function(self, tmp_path: Path) -> None:
        """Should not add main() shim when main() function is absent."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        config = make_build_cfg(
            tmp_path,
            include=[make_include_resolved("src", tmp_path)],
            package="testpkg",
            main_mode="auto",
            main_name=None,
        )

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === utils.py ===\ndef helper():\n    return 1\n"],
            order_names=["utils"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
            config=config,
            main_function_result=None,  # No main function found
            module_sources=None,
        )

        # Should NOT include the main() shim
        assert "if __name__ == '__main__':" not in result
        assert "sys.exit(main(" not in result

    def test_main_shim_not_added_when_main_is_not_function(
        self, tmp_path: Path
    ) -> None:
        """Should not add main() shim when 'main' exists but is not a function."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        config = make_build_cfg(
            tmp_path,
            include=[make_include_resolved("src", tmp_path)],
            package="testpkg",
            main_mode="auto",
            main_name=None,
        )

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=["# === config.py ===\nmain = 'some value'\n"],
            order_names=["config"],
            all_function_names=set(),
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
            config=config,
            main_function_result=None,  # 'main' is a variable, not a function
            module_sources=None,
        )

        # Should NOT include the main() shim (main is a variable, not a function)
        assert "if __name__ == '__main__':" not in result
        assert "sys.exit(main(" not in result

    def test_main_shim_added_when_main_function_in_multiple_modules(
        self, tmp_path: Path
    ) -> None:
        """Should add main() shim when main() exists in any module."""
        all_imports: OrderedDict[str, None] = OrderedDict()
        all_imports["import sys\n"] = None

        config = make_build_cfg(
            tmp_path,
            include=[make_include_resolved("src", tmp_path)],
            package="testpkg",
            main_mode="auto",
            main_name=None,
        )

        source = "def main():\n    return 0\n"
        module_sources = {"main.py": source}
        main_file = tmp_path / "src" / "main.py"
        main_function_result = ("main", main_file, "main")

        result, _ = mod_stitch._build_final_script(
            package_name="testpkg",
            all_imports=all_imports,
            parts=[
                "# === utils.py ===\ndef helper():\n    return 1\n",
                "# === main.py ===\ndef main():\n    return 0\n",
            ],
            order_names=["utils", "main"],
            all_function_names={"helper", "main"},
            detected_packages={"testpkg"},
            module_mode="multi",
            module_actions=[],
            shim="all",
            license_text="",
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
            config=config,
            main_function_result=main_function_result,
            module_sources=module_sources,
        )

        # Should include the main() shim
        assert "if __name__ == '__main__':" in result
        assert "sys.exit(main())" in result  # No params, so no sys.argv[1:]
