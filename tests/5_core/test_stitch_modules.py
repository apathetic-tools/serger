# tests/5_core/test_stitch_modules.py
"""Tests for stitch_modules orchestration function and helpers."""

import py_compile
import stat
import tempfile
from pathlib import Path
from typing import Any

import pytest

import serger.stitch as mod_stitch


class TestStitchModulesValidation:
    """Test validation in stitch_modules."""

    def test_missing_package_field(self) -> None:
        """Should raise RuntimeError when package is not specified."""
        config: dict[str, Any] = {
            "order": ["module_a", "module_b"],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"
            with pytest.raises(RuntimeError, match="package"):
                mod_stitch.stitch_modules(config, src_dir, out_path)

    def test_missing_order_field(self) -> None:
        """Should raise RuntimeError when order is not specified."""
        config: dict[str, Any] = {
            "package": "testpkg",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"
            with pytest.raises(RuntimeError, match="order"):
                mod_stitch.stitch_modules(config, src_dir, out_path)

    def test_invalid_package_type(self) -> None:
        """Should raise TypeError when package is not a string."""
        config: dict[str, Any] = {
            "package": 123,  # Not a string
            "order": ["module_a"],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"
            with pytest.raises(TypeError, match="package"):
                mod_stitch.stitch_modules(config, src_dir, out_path)

    def test_invalid_order_type(self) -> None:
        """Should raise TypeError when order is not a list."""
        config: dict[str, Any] = {
            "package": "testpkg",
            "order": "module_a",  # Not a list
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"
            with pytest.raises(TypeError, match="order"):
                mod_stitch.stitch_modules(config, src_dir, out_path)


class TestStitchModulesBasic:
    """Test basic stitch_modules functionality."""

    def test_stitch_simple_modules(self) -> None:
        """Should stitch simple modules without dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"

            # Create simple modules
            (src_dir / "base.py").write_text("BASE = 1\n")
            (src_dir / "main.py").write_text("MAIN = BASE\n")

            config: dict[str, Any] = {
                "package": "testpkg",
                "order": ["base", "main"],
                "exclude_names": [],
            }

            mod_stitch.stitch_modules(
                config,
                src_dir,
                out_path,
                version="1.0.0",
                commit="abc123",
                build_date="2025-01-01",
            )

            # Verify output exists and contains both modules
            assert out_path.exists()
            content = out_path.read_text()
            assert "# === base.py ===" in content
            assert "# === main.py ===" in content
            assert "BASE = 1" in content
            assert "MAIN = BASE" in content
            assert "__version__ = '1.0.0'" in content
            assert "__commit__ = 'abc123'" in content

    def test_stitch_with_external_imports(self) -> None:
        """Should collect external imports and place at top."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"

            # Create modules with external imports
            (src_dir / "base.py").write_text("import json\n\nBASE = 1\n")
            (src_dir / "main.py").write_text(
                "import sys\nfrom typing import Any\n\nMAIN = 2\n"
            )

            config: dict[str, Any] = {
                "package": "testpkg",
                "order": ["base", "main"],
                "exclude_names": [],
            }

            mod_stitch.stitch_modules(config, src_dir, out_path)

            content = out_path.read_text()
            # External imports should be near the top
            import_section = content[: content.find("# === base.py ===")]
            assert "import json" in import_section
            assert "import sys" in import_section
            assert "from typing import Any" in import_section

    def test_stitch_removes_shebangs(self) -> None:
        """Should remove shebangs from module sources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"

            # Create module with shebang
            (src_dir / "main.py").write_text("#!/usr/bin/env python3\n\nMAIN = 1\n")

            config: dict[str, Any] = {
                "package": "testpkg",
                "order": ["main"],
                "exclude_names": [],
            }

            mod_stitch.stitch_modules(config, src_dir, out_path)

            content = out_path.read_text()
            # Output should have shebang at top, but not in module sections
            lines = content.split("\n")
            assert lines[0] == "#!/usr/bin/env python3"
            # But module body should not have it
            assert content.count("#!/usr/bin/env python3") == 1

    def test_stitch_preserves_module_order(self) -> None:
        """Should maintain specified module order in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"

            # Create modules
            (src_dir / "a.py").write_text("A = 1\n")
            (src_dir / "b.py").write_text("B = 2\n")
            (src_dir / "c.py").write_text("C = 3\n")

            config: dict[str, Any] = {
                "package": "testpkg",
                "order": ["c", "a", "b"],  # Non-alphabetical order
                "exclude_names": [],
            }

            mod_stitch.stitch_modules(config, src_dir, out_path)

            content = out_path.read_text()
            # Check order is preserved
            c_pos = content.find("# === c.py ===")
            a_pos = content.find("# === a.py ===")
            b_pos = content.find("# === b.py ===")
            assert c_pos < a_pos < b_pos

    def test_stitch_missing_module_warning(self) -> None:
        """Should skip missing modules with warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"

            # Create only one of two specified modules
            (src_dir / "exists.py").write_text("EXISTS = 1\n")

            config: dict[str, Any] = {
                "package": "testpkg",
                "order": ["exists", "missing"],
                "exclude_names": [],
            }

            # Should not raise, just skip missing module
            mod_stitch.stitch_modules(config, src_dir, out_path)

            content = out_path.read_text()
            assert "# === exists.py ===" in content
            # Missing module should not appear
            assert "# === missing.py ===" not in content


class TestStitchModulesCollisionDetection:
    """Test name collision detection."""

    def test_collision_detection_functions(self) -> None:
        """Should raise RuntimeError when functions collide."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"

            # Create modules with colliding function names
            (src_dir / "a.py").write_text("def func():\n    return 1\n")
            (src_dir / "b.py").write_text("def func():\n    return 2\n")

            config: dict[str, Any] = {
                "package": "testpkg",
                "order": ["a", "b"],
                "exclude_names": [],
            }

            with pytest.raises(RuntimeError, match="collision"):
                mod_stitch.stitch_modules(config, src_dir, out_path)

    def test_collision_detection_classes(self) -> None:
        """Should raise RuntimeError when classes collide."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"

            # Create modules with colliding class names
            (src_dir / "a.py").write_text("class MyClass:\n    pass\n")
            (src_dir / "b.py").write_text("class MyClass:\n    pass\n")

            config: dict[str, Any] = {
                "package": "testpkg",
                "order": ["a", "b"],
                "exclude_names": [],
            }

            with pytest.raises(RuntimeError, match="collision"):
                mod_stitch.stitch_modules(config, src_dir, out_path)

    def test_no_collision_with_ignored_names(self) -> None:
        """Should allow collisions with ignored names like __version__."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"

            # Create modules with ignored collision names
            (src_dir / "a.py").write_text("__version__ = '1.0'\n")
            (src_dir / "b.py").write_text("__version__ = '2.0'\n")

            config: dict[str, Any] = {
                "package": "testpkg",
                "order": ["a", "b"],
                "exclude_names": [],
            }

            # Should not raise - __version__ is ignored
            mod_stitch.stitch_modules(config, src_dir, out_path)


class TestStitchModulesMetadata:
    """Test metadata embedding in output."""

    def test_metadata_embedding(self) -> None:
        """Should embed version, commit, and build date in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            config: dict[str, Any] = {
                "package": "testpkg",
                "order": ["main"],
                "exclude_names": [],
            }

            mod_stitch.stitch_modules(
                config,
                src_dir,
                out_path,
                license_header="# License: MIT",
                version="2.1.3",
                commit="def456",
                build_date="2025-06-15 10:30:00 UTC",
            )

            content = out_path.read_text()
            assert "# License: MIT" in content
            assert "# Version: 2.1.3" in content
            assert "# Commit: def456" in content
            assert "# Build Date: 2025-06-15 10:30:00 UTC" in content
            assert "__version__ = '2.1.3'" in content
            assert "__commit__ = 'def456'" in content
            assert "__STANDALONE__ = True" in content

    def test_license_header_optional(self) -> None:
        """Should handle empty license header gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            config: dict[str, Any] = {
                "package": "testpkg",
                "order": ["main"],
                "exclude_names": [],
            }

            # Should not raise with empty license header
            mod_stitch.stitch_modules(config, src_dir, out_path, license_header="")

            content = out_path.read_text()
            assert "#!/usr/bin/env python3" in content


class TestStitchModulesShims:
    """Test import shim generation."""

    def test_shim_block_generated(self) -> None:
        """Should generate import shims for all non-private modules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"

            (src_dir / "public_a.py").write_text("A = 1\n")
            (src_dir / "public_b.py").write_text("B = 2\n")

            config: dict[str, Any] = {
                "package": "testpkg",
                "order": ["public_a", "public_b"],
                "exclude_names": [],
            }

            mod_stitch.stitch_modules(config, src_dir, out_path)

            content = out_path.read_text()
            # Shim block should exist
            assert "# --- import shims for single-file runtime ---" in content
            # Check for f-string with curly braces {_pkg}
            assert "sys.modules[f'{_pkg}.public_a']" in content
            assert "sys.modules[f'{_pkg}.public_b']" in content

    def test_private_modules_excluded_from_shims(self) -> None:
        """Should not create shims for modules starting with underscore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"

            (src_dir / "public.py").write_text("PUBLIC = 1\n")
            (src_dir / "_private.py").write_text("PRIVATE = 2\n")

            config: dict[str, Any] = {
                "package": "testpkg",
                "order": ["public", "_private"],
                "exclude_names": [],
            }

            mod_stitch.stitch_modules(config, src_dir, out_path)

            content = out_path.read_text()
            # Public should have shim (check for f-string with curly braces {_pkg})
            assert "sys.modules[f'{_pkg}.public']" in content
            # Private should not have shim
            assert "sys.modules[f'{_pkg}._private']" not in content


class TestStitchModulesOutput:
    """Test output file generation."""

    def test_output_file_created(self) -> None:
        """Should create output file at specified path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "subdir" / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            config: dict[str, Any] = {
                "package": "testpkg",
                "order": ["main"],
                "exclude_names": [],
            }

            mod_stitch.stitch_modules(config, src_dir, out_path)

            # Output file should exist
            assert out_path.exists()
            # Parent directory should be created
            assert out_path.parent.exists()

    def test_output_file_executable(self) -> None:
        """Should make output file executable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"

            (src_dir / "main.py").write_text("MAIN = 1\n")

            config: dict[str, Any] = {
                "package": "testpkg",
                "order": ["main"],
                "exclude_names": [],
            }

            mod_stitch.stitch_modules(config, src_dir, out_path)

            # Check executable bit is set
            mode = out_path.stat().st_mode
            assert mode & stat.S_IXUSR

    def test_output_file_compiles(self) -> None:
        """Should generate valid Python that compiles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir)
            out_path = Path(tmpdir) / "output.py"

            (src_dir / "a.py").write_text("A = 1\n")
            (src_dir / "b.py").write_text("B = A + 1\n")

            config: dict[str, Any] = {
                "package": "testpkg",
                "order": ["a", "b"],
                "exclude_names": [],
            }

            mod_stitch.stitch_modules(config, src_dir, out_path)

            # Verify it compiles
            py_compile.compile(str(out_path), doraise=True)
