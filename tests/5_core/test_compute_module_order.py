# tests/5_core/test_compute_module_order.py
"""Tests for compute_module_order function."""

import tempfile
from pathlib import Path

import pytest

import serger.build as mod_build
import serger.config.config_types as mod_config_types
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


def test_init_py_relative_import_order() -> None:
    """Should order modules before __init__.py when __init__.py imports from them.

    This tests the bug where __init__.py that imports from other modules in the
    same package should be ordered AFTER those modules, but was being ordered
    before them.

    This reproduces the apathetic_logging scenario where:
    - src/apathetic_logging/__init__.py imports from .namespace
    - src/apathetic_logging/namespace.py defines the class
    - __init__.py should come AFTER namespace.py in the stitched output
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir) / "src"
        pkg_dir = src_dir / "apathetic_logging"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text(
            "from .namespace import apathetic_logging\n"
        )
        (pkg_dir / "namespace.py").write_text("class apathetic_logging:\n    pass\n")

        file_paths = [
            (pkg_dir / "__init__.py").resolve(),
            (pkg_dir / "namespace.py").resolve(),
        ]

        # Use find_package_root (as in real builds) - this might find wrong root
        package_root = mod_build.find_package_root(file_paths)

        # Create file_to_include mapping
        file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
        include = make_include_resolved("src", tmpdir)
        for file_path in file_paths:
            file_to_include[file_path] = include

        order = mod_stitch.compute_module_order(
            file_paths, package_root, "apathetic_logging", file_to_include
        )

        # namespace.py must come before __init__.py
        namespace_path = next(p for p in file_paths if p.name == "namespace.py")
        init_path = next(p for p in file_paths if p.name == "__init__.py")
        namespace_idx = order.index(namespace_path)
        init_idx = order.index(init_path)
        assert namespace_idx < init_idx, (
            f"namespace.py (index {namespace_idx}) should come before "
            f"__init__.py (index {init_idx}) when __init__.py imports from namespace"
        )


def test_init_py_relative_import_in_else_block() -> None:
    """Should detect imports inside else blocks for dependency ordering.

    This tests the bug where imports inside conditional blocks (like
    "if not __STANDALONE__: from .namespace import ...") were not being
    detected for dependency ordering.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir) / "src"
        pkg_dir = src_dir / "apathetic_logging"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text(
            """if globals().get("__STANDALONE__"):
    _apathetic_logging_ns = None
else:
    from .namespace import apathetic_logging as _apathetic_logging_ns
"""
        )
        (pkg_dir / "namespace.py").write_text("class apathetic_logging:\n    pass\n")

        file_paths = [
            (pkg_dir / "__init__.py").resolve(),
            (pkg_dir / "namespace.py").resolve(),
        ]

        # Use src as package root
        package_root = src_dir.resolve()

        file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
        include = make_include_resolved("src", tmpdir)
        for file_path in file_paths:
            file_to_include[file_path] = include

        order = mod_stitch.compute_module_order(
            file_paths, package_root, "apathetic_logging", file_to_include
        )

        namespace_path = next(p for p in file_paths if p.name == "namespace.py")
        init_path = next(p for p in file_paths if p.name == "__init__.py")
        namespace_idx = order.index(namespace_path)
        init_idx = order.index(init_path)
        assert namespace_idx < init_idx, (
            f"namespace.py (index {namespace_idx}) should come before "
            f"__init__.py (index {init_idx}) even when import is inside else block"
        )
