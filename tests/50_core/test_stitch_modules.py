# tests/50_core/test_stitch_modules.py
"""Tests for stitch_modules orchestration function and helpers."""

import py_compile
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

import serger.build as mod_build
import serger.config.config_types as mod_config_types
import serger.stitch as mod_stitch
from tests.utils import is_serger_build_for_test, run_with_output
from tests.utils.buildconfig import make_include_resolved


def _setup_stitch_test(
    src_dir: Path, order_names: list[str], package_name: str = "testpkg"
) -> tuple[
    list[Path],
    Path,
    dict[Path, mod_config_types.IncludeResolved],
    dict[str, Any],
]:
    """Helper to set up stitch_modules test with new signature.

    Args:
        src_dir: Directory containing Python modules
        order_names: List of module names (will be converted to paths)
        package_name: Package name for config

    Returns:
        Tuple of (file_paths, package_root, file_to_include, config)
    """
    # Create file paths from order_names
    file_paths = [(src_dir / f"{name}.py").resolve() for name in order_names]

    # Compute package root
    package_root = mod_build.find_package_root(file_paths)

    # Create file_to_include mapping (simple - all from same root)
    file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
    include = make_include_resolved(str(src_dir.name), src_dir.parent)
    for file_path in file_paths:
        file_to_include[file_path] = include

    # Create config with order as paths
    config: dict[str, Any] = {
        "package": package_name,
        "order": file_paths,  # Order as Path objects
        "exclude_names": [],  # Exclude names as Path objects
        "stitch_mode": "raw",
    }

    return file_paths, package_root, file_to_include, config


class TestStitchModulesValidation:
    """Test validation in stitch_modules."""

    def test_missing_package_field(self, tmp_path: Path) -> None:
        """Should raise RuntimeError when package is not specified."""
        config: dict[str, Any] = {
            "order": [Path("module_a.py"), Path("module_b.py")],
            "stitch_mode": "raw",
        }
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "module_a.py").write_text("A = 1\n")
        (src_dir / "module_b.py").write_text("B = 2\n")

        file_paths = [
            (src_dir / "module_a.py").resolve(),
            (src_dir / "module_b.py").resolve(),
        ]
        package_root = mod_build.find_package_root(file_paths)
        file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
        out_path = tmp_path / "output.py"

        with pytest.raises(TypeError, match="package"):
            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

    def test_missing_order_field(self, tmp_path: Path) -> None:
        """Should raise RuntimeError when order is not specified."""
        config: dict[str, Any] = {
            "package": "testpkg",
            "stitch_mode": "raw",
        }
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "module_a.py").write_text("A = 1\n")

        file_paths = [(src_dir / "module_a.py").resolve()]
        package_root = mod_build.find_package_root(file_paths)
        file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
        out_path = tmp_path / "output.py"

        with pytest.raises(RuntimeError, match="order"):
            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

    def test_invalid_package_type(self, tmp_path: Path) -> None:
        """Should raise TypeError when package is not a string."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "module_a.py").write_text("A = 1\n")

        file_paths = [(src_dir / "module_a.py").resolve()]
        package_root = mod_build.find_package_root(file_paths)
        file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
        out_path = tmp_path / "output.py"

        config: dict[str, Any] = {
            "package": 123,  # Not a string
            "order": file_paths,
            "stitch_mode": "raw",
        }

        with pytest.raises(TypeError, match="package"):
            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

    def test_invalid_order_type(self, tmp_path: Path) -> None:
        """Should raise TypeError when order is not a list."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "module_a.py").write_text("A = 1\n")

        file_paths = [(src_dir / "module_a.py").resolve()]
        package_root = mod_build.find_package_root(file_paths)
        file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
        out_path = tmp_path / "output.py"

        config: dict[str, Any] = {
            "package": "testpkg",
            "order": "module_a",  # Not a list
            "stitch_mode": "raw",
        }

        with pytest.raises(TypeError, match="order"):
            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

    def test_invalid_stitch_mode(self, tmp_path: Path) -> None:
        """Should raise ValueError when stitch_mode is invalid."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "module_a.py").write_text("A = 1\n")

        file_paths = [(src_dir / "module_a.py").resolve()]
        package_root = mod_build.find_package_root(file_paths)
        file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
        out_path = tmp_path / "output.py"

        config: dict[str, Any] = {
            "package": "testpkg",
            "order": file_paths,
            "stitch_mode": "invalid_mode",
        }

        with pytest.raises(ValueError, match="Invalid stitch_mode"):
            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

    def test_unimplemented_stitch_mode_class(self, tmp_path: Path) -> None:
        """Should raise NotImplementedError when stitch_mode is 'class'."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "module_a.py").write_text("A = 1\n")

        file_paths = [(src_dir / "module_a.py").resolve()]
        package_root = mod_build.find_package_root(file_paths)
        file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
        out_path = tmp_path / "output.py"

        config: dict[str, Any] = {
            "package": "testpkg",
            "order": file_paths,
            "stitch_mode": "class",
        }

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

    def test_unimplemented_stitch_mode_exec(self, tmp_path: Path) -> None:
        """Should raise NotImplementedError when stitch_mode is 'exec'."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "module_a.py").write_text("A = 1\n")

        file_paths = [(src_dir / "module_a.py").resolve()]
        package_root = mod_build.find_package_root(file_paths)
        file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
        out_path = tmp_path / "output.py"

        config: dict[str, Any] = {
            "package": "testpkg",
            "order": file_paths,
            "stitch_mode": "exec",
        }

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )


class TestStitchModulesBasic:
    """Test basic stitch_modules functionality."""

    def test_stitch_simple_modules(self, tmp_path: Path) -> None:
        """Should stitch simple modules without dependencies."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        # Create simple modules
        (src_dir / "base.py").write_text("BASE = 1\n")
        (src_dir / "main.py").write_text("MAIN = BASE\n")

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["base", "main"]
        )

        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            version="1.0.0",
            commit="abc123",
            build_date="2025-01-01",
            is_serger_build=is_serger_build_for_test(out_path),
        )

        # Verify output exists and contains both modules
        assert out_path.exists()
        content = out_path.read_text()
        # Module names are now derived from paths (e.g., "base" not "base.py")
        assert "# === base ===" in content or "# === base.py ===" in content
        assert "# === main ===" in content or "# === main.py ===" in content
        assert "BASE = 1" in content
        assert "MAIN = BASE" in content
        assert '__version__ = "1.0.0"' in content
        assert '__commit__ = "abc123"' in content

    def test_stitch_with_external_imports(self, tmp_path: Path) -> None:
        """Should collect external imports and place at top."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        # Create modules with external imports
        (src_dir / "base.py").write_text("import json\n\nBASE = 1\n")
        (src_dir / "main.py").write_text(
            "import sys\nfrom typing import Any\n\nMAIN = 2\n"
        )

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["base", "main"]
        )

        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

        content = out_path.read_text()
        # External imports should be near the top
        # Module header might be "base" or "base.py" depending on derivation
        header_marker = "# === base" if "# === base" in content else "# === base.py ==="
        import_section = content[: content.find(header_marker)]
        assert "import json" in import_section
        assert "import sys" in import_section
        assert "from typing import Any" in import_section

    def test_stitch_with_external_imports_keep_mode(self, tmp_path: Path) -> None:
        """Should keep external imports in their original locations."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        # Create modules with external imports
        (src_dir / "base.py").write_text("import json\n\nBASE = 1\n")
        (src_dir / "main.py").write_text(
            "import sys\nfrom typing import Any\n\nMAIN = 2\n"
        )

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["base", "main"]
        )
        config["external_imports"] = "keep"

        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

        content = out_path.read_text()
        # External imports should be in their module sections, not at top
        # Find module sections
        base_section_start = content.find("# === base")
        if base_section_start == -1:
            base_section_start = content.find("# === base.py ===")
        main_section_start = content.find("# === main")
        if main_section_start == -1:
            main_section_start = content.find("# === main.py ===")

        # Extract module sections
        base_section = content[base_section_start:main_section_start]
        main_section = content[main_section_start:]

        # Imports should be in their respective module sections
        assert "import json" in base_section
        assert "BASE = 1" in base_section
        assert "import sys" in main_section
        assert "from typing import Any" in main_section
        assert "MAIN = 2" in main_section

        # Imports should NOT be in the top import section
        # (only sys and types should be there for shim system)
        import_section = content[:base_section_start]
        # Module-specific imports should NOT be hoisted
        assert "import json" not in import_section
        assert "from typing import Any" not in import_section
        # But sys and types should still be there for shim system
        assert "import sys\n" in import_section or "import sys" in import_section
        assert "import types\n" in import_section or "import types" in import_section

    def test_stitch_removes_shebangs(self, tmp_path: Path) -> None:
        """Should remove shebangs from module sources."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        # Create module with shebang
        (src_dir / "main.py").write_text("#!/usr/bin/env python3\n\nMAIN = 1\n")

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["main"]
        )

        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

        content = out_path.read_text()
        # Output should have shebang at top, but not in module sections
        lines = content.split("\n")
        assert lines[0] == "#!/usr/bin/env python3"
        # But module body should not have it
        assert content.count("#!/usr/bin/env python3") == 1

    def test_stitch_preserves_module_order(self, tmp_path: Path) -> None:
        """Should maintain specified module order in output."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        # Create modules
        (src_dir / "a.py").write_text("A = 1\n")
        (src_dir / "b.py").write_text("B = 2\n")
        (src_dir / "c.py").write_text("C = 3\n")

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir,
            ["c", "a", "b"],  # Non-alphabetical order
        )

        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

        content = out_path.read_text()
        # Check order is preserved (module names derived from paths)
        c_pos = (
            content.find("# === c")
            if "# === c" in content
            else content.find("# === c.py ===")
        )
        a_pos = (
            content.find("# === a")
            if "# === a" in content
            else content.find("# === a.py ===")
        )
        b_pos = (
            content.find("# === b")
            if "# === b" in content
            else content.find("# === b.py ===")
        )
        assert c_pos < a_pos < b_pos

    def test_stitch_missing_module_warning(self, tmp_path: Path) -> None:
        """Should skip missing modules with warning."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        # Create only one of two specified modules
        (src_dir / "exists.py").write_text("EXISTS = 1\n")

        # Only include the existing file in file_paths
        file_paths = [(src_dir / "exists.py").resolve()]
        package_root = mod_build.find_package_root(file_paths)
        file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
        include = make_include_resolved(str(src_dir.name), src_dir.parent)
        for file_path in file_paths:
            file_to_include[file_path] = include

        config: dict[str, Any] = {
            "package": "testpkg",
            "order": file_paths,  # Only existing file
            "exclude_names": [],
        }

        # Should not raise, just skip missing module
        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

        content = out_path.read_text()
        assert "# === exists" in content or "# === exists.py ===" in content
        # Missing module should not appear
        assert "# === missing" not in content


class TestStitchModulesCollisionDetection:
    """Test name collision detection."""

    def test_collision_detection_functions(self, tmp_path: Path) -> None:
        """Should raise RuntimeError when functions collide."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        # Create modules with colliding function names
        (src_dir / "a.py").write_text("def func():\n    return 1\n")
        (src_dir / "b.py").write_text("def func():\n    return 2\n")

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["a", "b"]
        )

        with pytest.raises(RuntimeError, match="collision"):
            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

    def test_collision_detection_classes(self, tmp_path: Path) -> None:
        """Should raise RuntimeError when classes collide."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        # Create modules with colliding class names
        (src_dir / "a.py").write_text("class MyClass:\n    pass\n")
        (src_dir / "b.py").write_text("class MyClass:\n    pass\n")

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["a", "b"]
        )

        with pytest.raises(RuntimeError, match="collision"):
            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

    def test_no_collision_with_ignored_names(self, tmp_path: Path) -> None:
        """Should allow collisions with ignored names like __version__."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        # Create modules with ignored collision names
        (src_dir / "a.py").write_text("__version__ = '1.0'\n")
        (src_dir / "b.py").write_text("__version__ = '2.0'\n")

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["a", "b"]
        )

        # Should not raise - __version__ is ignored
        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

    def test_collision_detection_with_assign_mode(self, tmp_path: Path) -> None:
        """Should detect collisions when assign mode creates assignments."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        # Create modules in a package:
        # testpkg/a.py: defines Config class
        # testpkg/b.py: imports Config from testpkg.a with alias Cfg
        # testpkg/c.py: also defines Cfg class
        # (assign mode creates Cfg = Config in b.py, which conflicts with
        # class Cfg in c.py)
        # This should trigger a collision
        (src_dir / "a.py").write_text("class Config:\n    pass\n")
        (src_dir / "b.py").write_text("from testpkg.a import Config as Cfg\n")
        (src_dir / "c.py").write_text("class Cfg:\n    pass\n")

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["a", "b", "c"], package_name="testpkg"
        )
        # Use assign mode for internal imports
        config["internal_imports"] = "assign"

        with pytest.raises(RuntimeError, match="collision"):
            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )


class TestStitchModulesAssignMode:
    """Integration tests for assign mode."""

    def test_assign_mode_basic_import(self, tmp_path: Path) -> None:
        """Should transform imports to assignments and execute correctly."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        # Module A defines a class
        (src_dir / "a.py").write_text("class AppConfig:\n    value = 42\n")
        # Module B imports and uses it with alias to avoid collision
        (src_dir / "b.py").write_text(
            "from testpkg.a import AppConfig as Config\n\nresult = Config.value\n"
        )

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["a", "b"], package_name="testpkg"
        )
        config["internal_imports"] = "assign"

        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

        # Verify output compiles
        py_compile.compile(str(out_path), doraise=True)

        # Verify content has assignment (non-no-op with alias)
        content = out_path.read_text()
        assert "Config = AppConfig" in content

        # Verify it executes correctly
        # If assignments used sys.modules (not available yet), this would fail
        result = run_with_output(
            [sys.executable, str(out_path)],
            check=False,
            cwd=tmp_path,
        )
        assert result.returncode == 0, (
            f"Stitched file failed to execute:\n"
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )

    def test_assign_mode_direct_reference_works(self, tmp_path: Path) -> None:
        """Should work with direct references (would fail with sys.modules).

        This test specifically verifies that direct references work correctly.
        With sys.modules, this would fail because:
        1. Module code runs before shims are created
        2. sys.modules['testpkg.utils'] doesn't exist yet
        3. Assignment would raise KeyError

        With direct references, it works because all symbols are in the same
        global namespace.
        """
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        # Module utils defines a function
        (src_dir / "utils.py").write_text(
            "def helper(x: int) -> int:\n    return x * 2\n"
        )
        # Module main imports and uses it with alias to avoid collision
        (src_dir / "main.py").write_text(
            "from testpkg.utils import helper as compute\n\nanswer = compute(21)\n"
        )

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["utils", "main"], package_name="testpkg"
        )
        config["internal_imports"] = "assign"

        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

        # Verify output compiles
        py_compile.compile(str(out_path), doraise=True)

        # Verify content has assignment
        content = out_path.read_text()
        assert "compute = helper" in content

        # Verify it executes correctly
        # If assignments used sys.modules (not available yet), this would fail
        result = run_with_output(
            [sys.executable, str(out_path)],
            check=False,
            cwd=tmp_path,
        )
        assert result.returncode == 0, (
            f"Stitched file failed to execute (would fail with sys.modules):\n"
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )

        # Verify the code actually ran (answer should be 42)
        # We can't easily check this without modifying the code, but the
        # fact that it executed without error is the key test

    def test_assign_mode_with_alias(self, tmp_path: Path) -> None:
        """Should handle aliased imports correctly."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        (src_dir / "config.py").write_text("class MySettings:\n    pass\n")
        (src_dir / "app.py").write_text(
            "from testpkg.config import MySettings as MyConfig\n\n"
            "my_config = MyConfig()\n"
        )

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["config", "app"], package_name="testpkg"
        )
        config["internal_imports"] = "assign"

        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

        # Verify output compiles
        py_compile.compile(str(out_path), doraise=True)

        # Verify alias assignment
        content = out_path.read_text()
        assert "MyConfig = MySettings" in content
        assert "my_config = MyConfig()" in content

        # Verify it executes
        result = run_with_output(
            [sys.executable, str(out_path)],
            check=False,
            cwd=tmp_path,
        )
        assert result.returncode == 0, (
            f"Stitched file failed to execute:\n"
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )

    def test_assign_mode_relative_import(self, tmp_path: Path) -> None:
        """Should handle relative imports correctly."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        (src_dir / "base.py").write_text("BASE_VALUE = 100\n")
        (src_dir / "derived.py").write_text(
            "from .base import BASE_VALUE as base_val\n\nDERIVED = base_val + 1\n"
        )

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["base", "derived"], package_name="testpkg"
        )
        config["internal_imports"] = "assign"

        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

        # Verify output compiles
        py_compile.compile(str(out_path), doraise=True)

        # Verify relative import was transformed
        content = out_path.read_text()
        assert "base_val = BASE_VALUE" in content
        assert "from .base import" not in content

        # Verify it executes
        result = run_with_output(
            [sys.executable, str(out_path)],
            check=False,
            cwd=tmp_path,
        )
        assert result.returncode == 0, (
            f"Stitched file failed to execute:\n"
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )

    def test_assign_mode_multiple_imports(self, tmp_path: Path) -> None:
        """Should handle multiple imports from same module."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        (src_dir / "types.py").write_text(
            "class A:\n    pass\n\nclass B:\n    pass\n\nclass C:\n    pass\n"
        )
        (src_dir / "main.py").write_text(
            "from testpkg.types import A as TypeA, B as TypeB, C as TypeC\n\n"
            "items = [TypeA(), TypeB(), TypeC()]\n"
        )

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["types", "main"], package_name="testpkg"
        )
        config["internal_imports"] = "assign"

        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

        # Verify output compiles
        py_compile.compile(str(out_path), doraise=True)

        # Verify all assignments are present
        content = out_path.read_text()
        assert "TypeA = A" in content
        assert "TypeB = B" in content
        assert "TypeC = C" in content

        # Verify it executes
        result = run_with_output(
            [sys.executable, str(out_path)],
            check=False,
            cwd=tmp_path,
        )
        assert result.returncode == 0, (
            f"Stitched file failed to execute:\n"
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )

    def test_assign_mode_function_local_import(self, tmp_path: Path) -> None:
        """Should handle function-local imports correctly."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        (src_dir / "utils.py").write_text(
            "def compute(x: int) -> int:\n    return x * 3\n"
        )
        (src_dir / "main.py").write_text(
            "def run():\n"
            "    from testpkg.utils import compute as calc\n"
            "    return calc(7)\n"
        )

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["utils", "main"], package_name="testpkg"
        )
        config["internal_imports"] = "assign"

        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

        # Verify output compiles
        py_compile.compile(str(out_path), doraise=True)

        # Verify function-local assignment
        content = out_path.read_text()
        assert "calc = compute" in content
        assert "def run():" in content

        # Verify it executes
        result = run_with_output(
            [sys.executable, str(out_path)],
            check=False,
            cwd=tmp_path,
        )
        assert result.returncode == 0, (
            f"Stitched file failed to execute:\n"
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )

    def test_assign_mode_end_to_end_execution(self, tmp_path: Path) -> None:
        """Should produce working stitched code that executes correctly.

        Creates a multi-file project with actual functionality, stitches it
        with assign mode, and verifies it executes and produces expected output.
        This ensures assign mode assignments actually work at runtime.
        """
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        # File 1: Defines a utility function
        (src_dir / "utils.py").write_text(
            "def multiply(x: int, y: int) -> int:\n"
            "    print(f'Multiplying {x} * {y}')\n"
            "    return x * y\n"
        )

        # File 2: Defines a calculator class (uses alias to avoid collision)
        (src_dir / "calculator.py").write_text(
            "from testpkg.utils import multiply as mult\n\n"
            "class Calculator:\n"
            "    def __init__(self):\n"
            "        print('Calculator initialized')\n"
            "    \n"
            "    def compute(self, a: int, b: int) -> int:\n"
            "        result = mult(a, b)\n"
            "        print(f'Result: {result}')\n"
            "        return result\n"
        )

        # File 3: Main entry point that uses both (uses alias to avoid collision)
        (src_dir / "main.py").write_text(
            "from testpkg.calculator import Calculator as Calc\n\n"
            "def main(_args=None):\n"
            "    print('Starting application')\n"
            "    calc = Calc()\n"
            "    answer = calc.compute(6, 7)\n"
            "    print(f'Final answer: {answer}')\n"
            "    return 0\n"
        )

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["utils", "calculator", "main"], package_name="testpkg"
        )
        config["internal_imports"] = "assign"

        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

        # Verify output compiles
        py_compile.compile(str(out_path), doraise=True)

        # Verify assignments are present (non-no-op with aliases)
        content = out_path.read_text()
        assert "mult = multiply" in content
        assert "Calc = Calculator" in content

        # Execute and verify output
        result = run_with_output(
            [sys.executable, str(out_path)],
            check=False,
            cwd=tmp_path,
        )

        assert result.returncode == 0, (
            f"Stitched file failed to execute:\n"
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )

        # Verify expected output appears in correct order
        output = result.stdout
        assert "Starting application" in output
        assert "Calculator initialized" in output
        assert "Multiplying 6 * 7" in output
        assert "Result: 42" in output
        assert "Final answer: 42" in output

        # Verify output order is correct (rough check)
        assert output.find("Starting application") < output.find(
            "Calculator initialized"
        )
        assert output.find("Calculator initialized") < output.find("Multiplying 6 * 7")
        assert output.find("Multiplying 6 * 7") < output.find("Result: 42")
        assert output.find("Result: 42") < output.find("Final answer: 42")


class TestStitchModulesOtherImportModes:
    """Integration tests for other internal import modes (force_strip, strip, keep)."""

    def test_force_strip_mode_end_to_end(self, tmp_path: Path) -> None:
        """Should remove internal imports and code still executes correctly."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        (src_dir / "utils.py").write_text(
            "def add(x: int, y: int) -> int:\n    return x + y\n"
        )
        (src_dir / "main.py").write_text(
            "from testpkg.utils import add\n\n"
            "def main(_args=None):\n"
            "    result = add(10, 20)\n"
            "    print(f'Result: {result}')\n"
            "    return 0\n"
        )

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["utils", "main"], package_name="testpkg"
        )
        config["internal_imports"] = "force_strip"

        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

        # Verify output compiles
        py_compile.compile(str(out_path), doraise=True)

        # Verify import was removed
        content = out_path.read_text()
        assert "from testpkg.utils import add" not in content

        # Execute and verify it works
        result = run_with_output(
            [sys.executable, str(out_path)],
            check=False,
            cwd=tmp_path,
        )

        assert result.returncode == 0, (
            f"Stitched file failed to execute:\n"
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
        assert "Result: 30" in result.stdout

    def test_keep_mode_end_to_end(self, tmp_path: Path) -> None:
        """Should keep internal imports (may fail at runtime, but verifies structure).

        Note: Internal imports in 'keep' mode may not work in stitched output
        since the import system isn't set up. This test verifies the structure
        is correct even if execution might fail.
        """
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_path = tmp_path / "output.py"

        (src_dir / "utils.py").write_text(
            "def subtract(x: int, y: int) -> int:\n    return x - y\n"
        )
        (src_dir / "main.py").write_text(
            "from testpkg.utils import subtract\n\n"
            "def main(_args=None):\n"
            "    result = subtract(50, 20)\n"
            "    print(f'Result: {result}')\n"
            "    return 0\n"
        )

        file_paths, package_root, file_to_include, config = _setup_stitch_test(
            src_dir, ["utils", "main"], package_name="testpkg"
        )
        config["internal_imports"] = "keep"

        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

        # Verify output compiles
        py_compile.compile(str(out_path), doraise=True)

        # Verify import was kept
        content = out_path.read_text()
        assert "from testpkg.utils import subtract" in content

        # Note: Execution may fail because internal imports don't work
        # in stitched mode, but we verify the structure is correct

    def test_internal_imports_keep_with_excluded_init(self) -> None:
        """Test that internal_imports: 'keep' works when __init__.py is excluded.

        This tests a scenario where:
        - A package is included in the stitch
        - __init__.py is excluded
        - A source file imports the package at top level
        - internal_imports: "keep" is set
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src" / "mypkg"
            src_dir.mkdir(parents=True)
            out_path = tmp_path / "output.py"

            # Create a module in the package
            (src_dir / "module.py").write_text("# Module in mypkg\nVALUE = 42\n")

            # Create __init__.py (will be excluded)
            (src_dir / "__init__.py").write_text("# Package init\n")

            # Create source file that imports the package
            # Use "from package import ..." to trigger validation
            source_dir = tmp_path / "source"
            source_dir.mkdir()
            (source_dir / "app.py").write_text(
                "# Application file\nfrom mypkg import module\n\n"
                "def main() -> int:\n"
                "    # Access the package\n"
                "    value = module.VALUE\n"
                "    assert value == 42\n"
                "    return 0\n"
            )

            # Create file paths
            file_paths = [
                (source_dir / "app.py").resolve(),
                (src_dir / "module.py").resolve(),
            ]

            # Compute package root
            package_root = mod_build.find_package_root(file_paths)

            # Create file_to_include mapping
            file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
            include_src = make_include_resolved("src", tmp_path)
            include_source = make_include_resolved("source", tmp_path)
            for file_path in file_paths:
                if "source" in str(file_path):
                    file_to_include[file_path] = include_source
                else:
                    file_to_include[file_path] = include_src

            # Create config
            config: dict[str, Any] = {
                "package": "test_app",
                "order": file_paths,
                "exclude_names": [src_dir / "__init__.py"],
                "stitch_mode": "raw",
                "source_bases": ["src"],
                "internal_imports": "keep",  # Keep internal imports
                "module_mode": "multi",  # Generate shims for packages
            }

            # Should succeed (currently fails with "Unresolved internal imports: mypkg")
            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

            # Verify stitched file exists
            assert out_path.exists(), "Stitched file should be created"

            # Verify the import is kept in the output
            stitched_content = out_path.read_text()
            assert "from mypkg import module" in stitched_content, (
                "Import statement should be kept in stitched output"
            )

            # Verify it compiles
            compile(stitched_content, str(out_path), "exec")


class TestStitchModulesMetadata:
    """Test metadata embedding in output."""

    def test_metadata_embedding(self) -> None:
        """Should embed version, commit, build date, authors, and repo in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )
            config["authors"] = "Alice <alice@example.com>, Bob"
            config["repo"] = "https://example.com/repo"

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                license_text="MIT",
                version="2.1.3",
                commit="def456",
                build_date="2025-06-15 10:30:00 UTC",
                is_serger_build=is_serger_build_for_test(out_path),
            )

            content = out_path.read_text()
            # Header comments - single line format
            assert "# License: MIT" in content
            assert "# Version: 2.1.3" in content
            assert "# Commit: def456" in content
            assert "# Build Date: 2025-06-15 10:30:00 UTC" in content
            assert "# Authors: Alice <alice@example.com>, Bob" in content
            assert "# Repo: https://example.com/repo" in content
            # Docstring
            assert "Authors: Alice <alice@example.com>, Bob" in content
            # Constants
            assert '__version__ = "2.1.3"' in content
            assert '__commit__ = "def456"' in content
            assert '__AUTHORS__ = "Alice <alice@example.com>, Bob"' in content
            assert "__STANDALONE__ = True" in content

    def test_license_with_file_content(self) -> None:
        """Should include license file content as comments with marker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            # Create a simple module
            (src_dir / "main.py").write_text("MAIN = 1\n")

            # License content with multiple lines
            license_content = (
                "MIT License\n\nCopyright (c) 2024 Test Author\nAll rights reserved."
            )

            # Use helper to set up proper config
            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                license_text=license_content,
                version="1.0.0",
                commit="abc123",
                build_date="2024-01-01 00:00:00 UTC",
                is_serger_build=is_serger_build_for_test(out_path),
            )

            content = out_path.read_text()
            # Check for multi-line license block format
            assert "# ============LICENSE=============" in content
            assert "# ================================" in content
            # Check that license content is included as comments
            assert "# MIT License" in content
            assert "# Copyright (c) 2024 Test Author" in content
            assert "# All rights reserved." in content

    def test_license_optional(self) -> None:
        """Should handle empty license gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )

            # Should not raise with empty license header
            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                license_text="",
                is_serger_build=is_serger_build_for_test(out_path),
            )

            content = out_path.read_text()
            assert "#!/usr/bin/env python3" in content


class TestStitchModulesShims:
    """Test import shim generation."""

    def test_shim_block_generated(self) -> None:
        """Should generate import shims for all non-private modules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "public_a.py").write_text("A = 1\n")
            (src_dir / "public_b.py").write_text("B = 2\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["public_a", "public_b"]
            )

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

            content = out_path.read_text()
            # Shim block should exist
            assert "# --- import shims for single-file runtime ---" in content
            # Check for loop-based shim generation
            # The shims are now generated as:
            # for _name in [...]: sys.modules[_name] = _mod
            assert "for _name in" in content
            assert "sys.modules[_name] = _mod" in content
            # Module names are derived from paths, so might be "public_a"
            # or "public_a.py"
            normalized_content = content.replace("'", '"')
            assert (
                '"testpkg.public_a"' in normalized_content
                or '"public_a"' in normalized_content
                or '"testpkg.public_a.py"' in normalized_content
                or '"public_a.py"' in normalized_content
            )
            assert (
                '"testpkg.public_b"' in normalized_content
                or '"public_b"' in normalized_content
                or '"testpkg.public_b.py"' in normalized_content
                or '"public_b.py"' in normalized_content
            )

    def test_private_modules_included_in_shims(self) -> None:
        """Should create shims for all modules, including private ones.

        This matches installed package behavior where private modules
        are accessible. If specific modules should be excluded,
        use the 'exclude' config option.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "public.py").write_text("PUBLIC = 1\n")
            (src_dir / "_private.py").write_text("PRIVATE = 2\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["public", "_private"]
            )

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

            content = out_path.read_text()
            # Check for loop-based shim generation
            assert "for _name in" in content
            assert "sys.modules[_name] = _mod" in content
            # Public should have shim
            normalized_content = content.replace("'", '"')
            assert (
                '"testpkg.public"' in normalized_content
                or '"public"' in normalized_content
                or '"testpkg.public.py"' in normalized_content
                or '"public.py"' in normalized_content
            )
            # Private should also have shim (matching installed package behavior)
            assert (
                '"testpkg._private"' in normalized_content
                or '"_private"' in normalized_content
            )


class TestStitchModulesOutput:
    """Test output file generation."""

    def test_output_file_created(self) -> None:
        """Should create output file at specified path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "subdir" / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

            # Output file should exist
            assert out_path.exists()
            # Parent directory should be created
            assert out_path.parent.exists()

    def test_output_file_executable(self) -> None:
        """Should make output file executable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

            # Check executable bit is set
            mode = out_path.stat().st_mode
            assert mode & stat.S_IXUSR

    def test_output_file_compiles(self) -> None:
        """Should generate valid Python that compiles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "a.py").write_text("A = 1\n")
            (src_dir / "b.py").write_text("B = A + 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["a", "b"]
            )

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

            # Verify it compiles
            py_compile.compile(str(out_path), doraise=True)

    def test_refuses_to_overwrite_non_serger_file(self) -> None:
        """Should refuse to overwrite files that aren't serger builds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            # Create a non-serger Python file at the output path
            out_path.write_text("#!/usr/bin/env python3\nprint('Hello, world!')\n")

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )

            # Should raise RuntimeError when trying to overwrite
            with pytest.raises(RuntimeError, match="does not appear to be a serger"):
                mod_stitch.stitch_modules(
                    config=config,
                    file_paths=file_paths,
                    package_root=package_root,
                    file_to_include=file_to_include,
                    out_path=out_path,
                    is_serger_build=is_serger_build_for_test(out_path),
                )

            # Original file should still exist and be unchanged
            assert out_path.exists()
            assert "Hello, world!" in out_path.read_text()

    def test_allows_overwriting_serger_build(self) -> None:
        """Should allow overwriting files that are serger builds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )

            # First build - creates the file
            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

            # Verify it's a serger build
            content = out_path.read_text()
            assert "__STITCH_SOURCE__" in content

            # Modify source and rebuild - should succeed
            (src_dir / "main.py").write_text("MAIN = 2\n")

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

            # Verify it was overwritten with new content
            new_content = out_path.read_text()
            assert "MAIN = 2" in new_content
            assert "__STITCH_SOURCE__" in new_content

    @pytest.mark.parametrize(
        ("content", "description"),
        [
            ("# Build Tool: serger\n", "standard format"),
            ("# Build Tool: SERGER\n", "uppercase"),
            ("# Build Tool: Serger\n", "mixed case"),
            ("#  Build Tool: serger\n", "with extra whitespace"),
            ("# Build Tool:  serger\n", "with extra whitespace after colon"),
            ("# Build Tool:serger\n", "no space after colon"),
            ("#Build Tool: serger\n", "no space after hash"),
        ],
    )
    def test_is_serger_build_recognizes_serger_builds(
        self, content: str, description: str
    ) -> None:
        """Should recognize serger builds with different comment formats and case."""
        # Access function through module for testing
        is_serger_build = mod_stitch.is_serger_build

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            test_file = tmp_path / "test.py"
            test_file.write_text(content)
            assert is_serger_build(test_file), f"Failed for: {description}"

    @pytest.mark.parametrize(
        ("content", "description"),
        [
            ('__STITCH_SOURCE__ = "other_tool"\n', "non-serger value"),
            ("print('Hello, world!')\n", "missing variable"),
        ],
    )
    def test_is_serger_build_rejects_non_serger_files(
        self, content: str, description: str
    ) -> None:
        """Should reject files that are not serger builds."""
        # Access function through module for testing
        is_serger_build = mod_stitch.is_serger_build

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            test_file = tmp_path / "test.py"
            test_file.write_text(content)
            assert not is_serger_build(test_file), f"Failed for: {description}"

    def test_is_serger_build_respects_max_lines_parameter(self) -> None:
        """Should respect max_lines parameter when provided."""
        # Access function through module for testing
        is_serger_build = mod_stitch.is_serger_build

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            test_file = tmp_path / "test.py"
            # Create a file with the marker beyond line 10
            lines = ["# Line 1\n"] * 15
            lines.insert(10, "# Build Tool: serger\n")
            test_file.write_text("".join(lines))

            # Should find it with default (200 lines)
            assert is_serger_build(test_file), "Should find marker with default limit"

            # Should find it with custom limit (15 lines)
            assert is_serger_build(test_file, max_lines=15), (
                "Should find marker with custom limit"
            )

            # Should NOT find it with limit too low (5 lines)
            assert not is_serger_build(test_file, max_lines=5), (
                "Should not find marker with limit too low"
            )


class TestStitchModulesDisplayConfig:
    """Test displayName and description configuration in stitch_modules."""

    def test_both_display_name_and_description(self) -> None:
        """Should format header with both name and description."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )
            config["display_name"] = "TestProject"
            config["description"] = "A test project"

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                license_text="MIT",
                is_serger_build=is_serger_build_for_test(out_path),
            )

            content = out_path.read_text()
            lines = content.split("\n")
            # Docstring now comes first (after shebang) per PEP 8
            assert lines[1] == '"""'
            # Find header after docstring
            header_idx = next(
                i
                for i, line in enumerate(lines)
                if line == "# TestProject — A test project"
            )
            assert header_idx > 1

    def test_only_display_name(self) -> None:
        """Should format header with only display name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )
            config["display_name"] = "TestProject"

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

            content = out_path.read_text()
            lines = content.split("\n")
            # Docstring now comes first (after shebang) per PEP 8
            assert lines[1] == '"""'
            # Find header after docstring
            header_idx = next(
                i for i, line in enumerate(lines) if line == "# TestProject"
            )
            assert header_idx > 1

    def test_only_description(self) -> None:
        """Should format header with package name and description."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )
            config["description"] = "A test project"

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

            content = out_path.read_text()
            lines = content.split("\n")
            # Docstring now comes first (after shebang) per PEP 8
            assert lines[1] == '"""'
            # Find header after docstring
            header_idx = next(
                i
                for i, line in enumerate(lines)
                if line == "# testpkg — A test project"
            )
            assert header_idx > 1

    def test_custom_header_overrides_display_name(self) -> None:
        """Should use custom_header when provided, overriding display_name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )
            config["display_name"] = "TestProject"
            config["description"] = "A test project"
            config["custom_header"] = "Custom Header Text"

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                license_text="MIT",
                is_serger_build=is_serger_build_for_test(out_path),
            )

            content = out_path.read_text()
            lines = content.split("\n")
            # Docstring now comes first (after shebang) per PEP 8
            assert lines[1] == '"""'
            # Find header after docstring
            header_idx = next(
                i for i, line in enumerate(lines) if line == "# Custom Header Text"
            )
            assert header_idx > 1

    def test_file_docstring_overrides_auto_generated(self) -> None:
        """Should use file_docstring when provided, overriding auto-generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )
            config["file_docstring"] = "Custom docstring content\nwith multiple lines"

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                license_text="MIT",
                is_serger_build=is_serger_build_for_test(out_path),
            )

            content = out_path.read_text()
            # Find the docstring section
            docstring_start = content.find('"""')
            docstring_end = content.find('"""', docstring_start + 3)
            docstring_content = content[docstring_start + 3 : docstring_end]
            assert "Custom docstring content" in docstring_content
            assert "with multiple lines" in docstring_content
            # Should not contain auto-generated content
            assert "This single-file version is auto-generated" not in docstring_content

    def test_neither_provided_defaults_to_package_name(self) -> None:
        """Should use package name when neither field provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

            content = out_path.read_text()
            lines = content.split("\n")
            # Docstring now comes first (after shebang) per PEP 8
            assert lines[1] == '"""'
            # Find header after docstring
            header_idx = next(i for i, line in enumerate(lines) if line == "# testpkg")
            assert header_idx > 1

    def test_empty_strings_treated_as_not_provided(self) -> None:
        """Should treat empty strings as not provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )
            config["display_name"] = ""
            config["description"] = ""

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

            content = out_path.read_text()
            lines = content.split("\n")
            # Docstring now comes first (after shebang) per PEP 8
            assert lines[1] == '"""'
            # Find header after docstring
            header_idx = next(i for i, line in enumerate(lines) if line == "# testpkg")
            assert header_idx > 1


class TestRepoField:
    """Test repo field in stitch_modules header."""

    def test_repo_field_included_when_provided(self) -> None:
        """Should include repo line in header when repo is provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )
            config["repo"] = "https://github.com/user/project"

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

            content = out_path.read_text()
            assert "# Repo: https://github.com/user/project" in content

    def test_repo_field_omitted_when_not_provided(self) -> None:
        """Should NOT include repo line when repo is not in config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )
            # repo field deliberately omitted

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

            content = out_path.read_text()
            assert "# Repo:" not in content

    def test_repo_field_omitted_when_empty_string(self) -> None:
        """Should NOT include repo line when repo is empty string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )
            config["repo"] = ""  # explicitly empty

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                is_serger_build=is_serger_build_for_test(out_path),
            )

            content = out_path.read_text()
            assert "# Repo:" not in content

    def test_repo_line_position_in_header(self) -> None:
        """Should place repo line after Build Date and before ruff noqa."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            out_path = tmp_path / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            file_paths, package_root, file_to_include, config = _setup_stitch_test(
                src_dir, ["main"]
            )
            config["repo"] = "https://github.com/test/test"

            mod_stitch.stitch_modules(
                config=config,
                file_paths=file_paths,
                package_root=package_root,
                file_to_include=file_to_include,
                out_path=out_path,
                version="1.0.0",
                build_date="2025-01-01 12:00:00 UTC",
                is_serger_build=is_serger_build_for_test(out_path),
            )

            content = out_path.read_text()
            lines = content.split("\n")

            # Find key header lines
            build_date_idx = None
            repo_idx = None
            ruff_noqa_idx = None

            for i, line in enumerate(lines):
                if "# Build Date:" in line:
                    build_date_idx = i
                if "# Repo:" in line:
                    repo_idx = i
                if "# noqa:" in line:
                    ruff_noqa_idx = i

            assert build_date_idx is not None, "Build Date line not found"
            assert repo_idx is not None, "Repo line not found"
            assert ruff_noqa_idx is not None, "Ruff noqa line not found"

            # Verify order: Build Date → Repo → ruff noqa
            assert build_date_idx < repo_idx, (
                f"Repo line should come after Build Date "
                f"(Build Date at {build_date_idx}, Repo at {repo_idx})"
            )
            assert repo_idx < ruff_noqa_idx, (
                f"Ruff noqa line should come after Repo "
                f"(Repo at {repo_idx}, Ruff noqa at {ruff_noqa_idx})"
            )

    def test_repo_string_passed_through(self) -> None:
        """Should pass repo string through as-is to header."""
        test_strings = [
            "https://github.com/user/repo",
            "my-custom-repo-string",
            "any arbitrary string value",
        ]

        for repo_str in test_strings:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                src_dir = tmp_path / "src"
                src_dir.mkdir()
                out_path = tmp_path / "output.py"

                (src_dir / "main.py").write_text("MAIN = 1\n")

                file_paths, package_root, file_to_include, config = _setup_stitch_test(
                    src_dir, ["main"]
                )
                config["repo"] = repo_str

                mod_stitch.stitch_modules(
                    config=config,
                    file_paths=file_paths,
                    package_root=package_root,
                    file_to_include=file_to_include,
                    out_path=out_path,
                    is_serger_build=is_serger_build_for_test(out_path),
                )

                content = out_path.read_text()
                assert f"# Repo: {repo_str}" in content
