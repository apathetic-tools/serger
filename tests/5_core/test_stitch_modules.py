# tests/5_core/test_stitch_modules.py
"""Tests for stitch_modules orchestration function and helpers."""

import py_compile
import stat
import tempfile
from pathlib import Path
from typing import Any

import pytest

import serger.build as mod_build
import serger.config.config_types as mod_config_types
import serger.stitch as mod_stitch
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
    }

    return file_paths, package_root, file_to_include, config


class TestStitchModulesValidation:
    """Test validation in stitch_modules."""

    def test_missing_package_field(self) -> None:
        """Should raise RuntimeError when package is not specified."""
        config: dict[str, Any] = {
            "order": [Path("module_a.py"), Path("module_b.py")],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
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

            with pytest.raises(RuntimeError, match="package"):
                mod_stitch.stitch_modules(
                    config=config,
                    file_paths=file_paths,
                    package_root=package_root,
                    file_to_include=file_to_include,
                    out_path=out_path,
                )

    def test_missing_order_field(self) -> None:
        """Should raise RuntimeError when order is not specified."""
        config: dict[str, Any] = {
            "package": "testpkg",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
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
                )

    def test_invalid_package_type(self) -> None:
        """Should raise TypeError when package is not a string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
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
            }

            with pytest.raises(TypeError, match="package"):
                mod_stitch.stitch_modules(
                    config=config,
                    file_paths=file_paths,
                    package_root=package_root,
                    file_to_include=file_to_include,
                    out_path=out_path,
                )

    def test_invalid_order_type(self) -> None:
        """Should raise TypeError when order is not a list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
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
            }

            with pytest.raises(TypeError, match="order"):
                mod_stitch.stitch_modules(
                    config=config,
                    file_paths=file_paths,
                    package_root=package_root,
                    file_to_include=file_to_include,
                    out_path=out_path,
                )


class TestStitchModulesBasic:
    """Test basic stitch_modules functionality."""

    def test_stitch_simple_modules(self) -> None:
        """Should stitch simple modules without dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
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

    def test_stitch_with_external_imports(self) -> None:
        """Should collect external imports and place at top."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
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
            )

            content = out_path.read_text()
            # External imports should be near the top
            # Module header might be "base" or "base.py" depending on derivation
            header_marker = (
                "# === base" if "# === base" in content else "# === base.py ==="
            )
            import_section = content[: content.find(header_marker)]
            assert "import json" in import_section
            assert "import sys" in import_section
            assert "from typing import Any" in import_section

    def test_stitch_removes_shebangs(self) -> None:
        """Should remove shebangs from module sources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
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
            )

            content = out_path.read_text()
            # Output should have shebang at top, but not in module sections
            lines = content.split("\n")
            assert lines[0] == "#!/usr/bin/env python3"
            # But module body should not have it
            assert content.count("#!/usr/bin/env python3") == 1

    def test_stitch_preserves_module_order(self) -> None:
        """Should maintain specified module order in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
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

    def test_stitch_missing_module_warning(self) -> None:
        """Should skip missing modules with warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
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
            )

            content = out_path.read_text()
            assert "# === exists" in content or "# === exists.py ===" in content
            # Missing module should not appear
            assert "# === missing" not in content


class TestStitchModulesCollisionDetection:
    """Test name collision detection."""

    def test_collision_detection_functions(self) -> None:
        """Should raise RuntimeError when functions collide."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
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
                )

    def test_collision_detection_classes(self) -> None:
        """Should raise RuntimeError when classes collide."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
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
                )

    def test_no_collision_with_ignored_names(self) -> None:
        """Should allow collisions with ignored names like __version__."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
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
            )


class TestStitchModulesMetadata:
    """Test metadata embedding in output."""

    def test_metadata_embedding(self) -> None:
        """Should embed version, commit, and build date in output."""
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
                license_header="License: MIT",
                version="2.1.3",
                commit="def456",
                build_date="2025-06-15 10:30:00 UTC",
            )

            content = out_path.read_text()
            assert "# License: MIT" in content
            assert "# Version: 2.1.3" in content
            assert "# Commit: def456" in content
            assert "# Build Date: 2025-06-15 10:30:00 UTC" in content
            assert '__version__ = "2.1.3"' in content
            assert '__commit__ = "def456"' in content
            assert "__STANDALONE__ = True" in content

    def test_license_header_optional(self) -> None:
        """Should handle empty license header gracefully."""
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
                license_header="",
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
            )

            # Verify it compiles
            py_compile.compile(str(out_path), doraise=True)


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
                license_header="# License: MIT\n",
            )

            content = out_path.read_text()
            lines = content.split("\n")
            # First line after shebang should be formatted header
            assert lines[1] == "# TestProject — A test project"

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
            )

            content = out_path.read_text()
            lines = content.split("\n")
            assert lines[1] == "# TestProject"

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
            )

            content = out_path.read_text()
            lines = content.split("\n")
            assert lines[1] == "# testpkg — A test project"

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
            )

            content = out_path.read_text()
            lines = content.split("\n")
            assert lines[1] == "# testpkg"

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
            )

            content = out_path.read_text()
            lines = content.split("\n")
            assert lines[1] == "# testpkg"


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
                if "# ruff: noqa:" in line:
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
                )

                content = out_path.read_text()
                assert f"# Repo: {repo_str}" in content
