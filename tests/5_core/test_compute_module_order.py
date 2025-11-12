# tests/5_core/test_compute_module_order.py
"""Tests for compute_module_order function."""

import tempfile
from pathlib import Path

import pytest

import serger.build as mod_build
import serger.config_types as mod_config_types
import serger.stitch as mod_stitch
from tests.utils import make_include_resolved


def _setup_order_test(
    src_dir: Path, module_names: list[str]
) -> tuple[list[Path], Path, dict[Path, mod_config_types.IncludeResolved]]:
    """Helper to set up compute_module_order test.

    Args:
        src_dir: Directory containing Python modules
        module_names: List of module names (will be converted to paths)

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


def test_simple_order() -> None:
    """Should return order for modules with no dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir)
        (src_dir / "a.py").write_text("# module a\n")
        (src_dir / "b.py").write_text("# module b\n")

        file_paths, package_root, file_to_include = _setup_order_test(
            src_dir, ["a", "b"]
        )

        order = mod_stitch.compute_module_order(
            file_paths, package_root, "pkg", file_to_include
        )
        assert set(order) == set(file_paths)


def test_dependency_order() -> None:
    """Should correct order based on import dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir)
        (src_dir / "base.py").write_text("# base\n")
        (src_dir / "derived.py").write_text("from pkg.base import something\n")

        file_paths, package_root, file_to_include = _setup_order_test(
            src_dir, ["derived", "base"]
        )

        order = mod_stitch.compute_module_order(
            file_paths, package_root, "pkg", file_to_include
        )
        # base must come before derived
        base_path = next(p for p in file_paths if p.name == "base.py")
        derived_path = next(p for p in file_paths if p.name == "derived.py")
        assert order.index(base_path) < order.index(derived_path)


def test_circular_import_error() -> None:
    """Should raise RuntimeError on circular imports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir)
        (src_dir / "a.py").write_text("from pkg.b import x\n")
        (src_dir / "b.py").write_text("from pkg.a import y\n")

        file_paths, package_root, file_to_include = _setup_order_test(
            src_dir, ["a", "b"]
        )

        with pytest.raises(RuntimeError):
            mod_stitch.compute_module_order(
                file_paths, package_root, "pkg", file_to_include
            )


def test_relative_import_order() -> None:
    """Should handle relative imports correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir)
        (src_dir / "base.py").write_text("# base\n")
        (src_dir / "derived.py").write_text("from .base import something\n")

        file_paths, package_root, file_to_include = _setup_order_test(
            src_dir, ["derived", "base"]
        )

        order = mod_stitch.compute_module_order(
            file_paths, package_root, "pkg", file_to_include
        )
        # base must come before derived
        base_path = next(p for p in file_paths if p.name == "base.py")
        derived_path = next(p for p in file_paths if p.name == "derived.py")
        assert order.index(base_path) < order.index(derived_path)
