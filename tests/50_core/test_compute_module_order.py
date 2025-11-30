# tests/50_core/test_compute_module_order.py
"""Tests for compute_module_order function."""

import ast
from pathlib import Path

import apathetic_utils as mod_utils
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


def test_simple_order(tmp_path: Path) -> None:
    """Should return order for modules with no dependencies."""
    src_dir = tmp_path
    (src_dir / "a.py").write_text("# module a\n")
    (src_dir / "b.py").write_text("# module b\n")

    file_paths, package_root, file_to_include = _setup_order_test(src_dir, ["a", "b"])

    # Detect packages for the test
    detected_packages, _parent_dirs = mod_utils.detect_packages_from_files(
        file_paths, "pkg"
    )

    order = mod_stitch.compute_module_order(
        file_paths,
        package_root,
        "pkg",
        file_to_include,
        detected_packages=detected_packages,
    )
    assert set(order) == set(file_paths)


def test_deterministic_ordering_multiple_valid_orderings(
    tmp_path: Path,
) -> None:
    """Should produce identical order when multiple valid topological orderings exist.

    This test verifies that compute_module_order produces deterministic results
    even when multiple valid topological orderings exist (i.e., when modules
    have no dependencies between them). This is critical for reproducible builds.
    """
    src_dir = tmp_path
    # Create multiple modules with no dependencies between them
    # This creates a scenario where multiple valid topological orderings exist
    (src_dir / "a.py").write_text("# module a\n")
    (src_dir / "b.py").write_text("# module b\n")
    (src_dir / "c.py").write_text("# module c\n")
    (src_dir / "d.py").write_text("# module d\n")
    (src_dir / "e.py").write_text("# module e\n")

    file_paths, package_root, file_to_include = _setup_order_test(
        src_dir, ["a", "b", "c", "d", "e"]
    )

    # Detect packages for the test
    detected_packages, _parent_dirs = mod_utils.detect_packages_from_files(
        file_paths, "pkg"
    )

    # Call compute_module_order multiple times with the same input
    # The order should be identical each time
    orders: list[list[Path]] = []
    for _ in range(10):
        order = mod_stitch.compute_module_order(
            file_paths,
            package_root,
            "pkg",
            file_to_include,
            detected_packages=detected_packages,
        )
        orders.append(order)

    # Verify all orders are identical
    first_order = orders[0]
    for i, order in enumerate(orders[1:], start=1):
        assert order == first_order, (
            f"Order should be deterministic, but iteration {i} produced "
            f"different order. First: {first_order}, Got: {order}"
        )

    # Verify the order is sorted by file path (deterministic tie-breaker)
    # Since there are no dependencies, modules should be ordered by file path
    sorted_paths = sorted(file_paths, key=str)
    assert first_order == sorted_paths, (
        f"When no dependencies exist, modules should be ordered by file path. "
        f"Expected: {sorted_paths}, Got: {first_order}"
    )


def test_dependency_order(tmp_path: Path) -> None:
    """Should correct order based on import dependencies."""
    src_dir = tmp_path
    (src_dir / "base.py").write_text("# base\n")
    (src_dir / "derived.py").write_text("from pkg.base import something\n")

    file_paths, package_root, file_to_include = _setup_order_test(
        src_dir, ["derived", "base"]
    )

    # Detect packages for the test
    detected_packages, _parent_dirs = mod_utils.detect_packages_from_files(
        file_paths, "pkg"
    )

    order = mod_stitch.compute_module_order(
        file_paths,
        package_root,
        "pkg",
        file_to_include,
        detected_packages=detected_packages,
    )
    # base must come before derived
    base_path = next(p for p in file_paths if p.name == "base.py")
    derived_path = next(p for p in file_paths if p.name == "derived.py")
    assert order.index(base_path) < order.index(derived_path)


def test_circular_import_error(tmp_path: Path) -> None:
    """Should raise RuntimeError on circular imports."""
    src_dir = tmp_path
    (src_dir / "a.py").write_text("from pkg.b import x\n")
    (src_dir / "b.py").write_text("from pkg.a import y\n")

    file_paths, package_root, file_to_include = _setup_order_test(src_dir, ["a", "b"])

    # Detect packages for the test
    detected_packages, _parent_dirs = mod_utils.detect_packages_from_files(
        file_paths, "pkg"
    )

    with pytest.raises(RuntimeError):
        mod_stitch.compute_module_order(
            file_paths,
            package_root,
            "pkg",
            file_to_include,
            detected_packages=detected_packages,
        )


def test_relative_import_order(tmp_path: Path) -> None:
    """Should handle relative imports correctly."""
    src_dir = tmp_path
    (src_dir / "base.py").write_text("# base\n")
    (src_dir / "derived.py").write_text("from .base import something\n")

    file_paths, package_root, file_to_include = _setup_order_test(
        src_dir, ["derived", "base"]
    )

    # Detect packages for the test
    detected_packages, _parent_dirs = mod_utils.detect_packages_from_files(
        file_paths, "pkg"
    )

    order = mod_stitch.compute_module_order(
        file_paths,
        package_root,
        "pkg",
        file_to_include,
        detected_packages=detected_packages,
    )
    # base must come before derived
    base_path = next(p for p in file_paths if p.name == "base.py")
    derived_path = next(p for p in file_paths if p.name == "derived.py")
    assert order.index(base_path) < order.index(derived_path)


def test_init_py_relative_import_order(tmp_path: Path) -> None:
    """Should order modules before __init__.py when __init__.py imports from them.

    This tests the bug where __init__.py that imports from other modules in the
    same package should be ordered AFTER those modules, but was being ordered
    before them.

    This reproduces the apathetic_logging scenario where:
    - src/apathetic_logging/__init__.py imports from .namespace
    - src/apathetic_logging/namespace.py defines the class
    - __init__.py should come AFTER namespace.py in the stitched output
    """
    src_dir = tmp_path / "src"
    pkg_dir = src_dir / "apathetic_logging"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("from .namespace import apathetic_logging\n")
    (pkg_dir / "namespace.py").write_text("class apathetic_logging:\n    pass\n")

    file_paths = [
        (pkg_dir / "__init__.py").resolve(),
        (pkg_dir / "namespace.py").resolve(),
    ]

    # Use find_package_root (as in real builds) - this might find wrong root
    package_root = mod_build.find_package_root(file_paths)

    # Create file_to_include mapping
    file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
    include = make_include_resolved("src", tmp_path)
    for file_path in file_paths:
        file_to_include[file_path] = include

    # Detect packages for the test
    detected_packages, _parent_dirs = mod_utils.detect_packages_from_files(
        file_paths, "apathetic_logging"
    )

    order = mod_stitch.compute_module_order(
        file_paths,
        package_root,
        "apathetic_logging",
        file_to_include,
        detected_packages=detected_packages,
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


def test_init_py_relative_import_in_else_block(tmp_path: Path) -> None:
    """Should detect imports inside else blocks for dependency ordering.

    This tests the bug where imports inside conditional blocks (like
    "if not __STANDALONE__: from .namespace import ...") were not being
    detected for dependency ordering.
    """
    src_dir = tmp_path / "src"
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
    include = make_include_resolved("src", tmp_path)
    for file_path in file_paths:
        file_to_include[file_path] = include

    # Detect packages for the test
    detected_packages, _parent_dirs = mod_utils.detect_packages_from_files(
        file_paths, "apathetic_logging"
    )

    order = mod_stitch.compute_module_order(
        file_paths,
        package_root,
        "apathetic_logging",
        file_to_include,
        detected_packages=detected_packages,
    )

    namespace_path = next(p for p in file_paths if p.name == "namespace.py")
    init_path = next(p for p in file_paths if p.name == "__init__.py")
    namespace_idx = order.index(namespace_path)
    init_idx = order.index(init_path)
    assert namespace_idx < init_idx, (
        f"namespace.py (index {namespace_idx}) should come before "
        f"__init__.py (index {init_idx}) even when import is inside else block"
    )


# Tests for helper functions
# we import '_' private for testing purposes only
# pyright: reportPrivateUsage=false


def test_resolve_relative_import_level_1() -> None:
    """Should resolve relative import with level 1."""
    source = "from .constants import X"
    tree = ast.parse(source)
    node = tree.body[0]
    assert isinstance(node, ast.ImportFrom)

    result = mod_stitch._resolve_relative_import(node, "serger.actions")  # noqa: SLF001
    assert result == "serger.constants"


def test_resolve_relative_import_level_2() -> None:
    """Should resolve relative import with level 2."""
    source = "from ..utils import helper"
    tree = ast.parse(source)
    node = tree.body[0]
    assert isinstance(node, ast.ImportFrom)

    result = mod_stitch._resolve_relative_import(node, "serger.actions.sub")  # noqa: SLF001
    assert result == "serger.utils"


def test_resolve_relative_import_beyond_root() -> None:
    """Should return None when relative import goes beyond package root."""
    source = "from ...something import X"
    tree = ast.parse(source)
    node = tree.body[0]
    assert isinstance(node, ast.ImportFrom)

    result = mod_stitch._resolve_relative_import(node, "serger.actions")  # noqa: SLF001
    assert result is None


def test_resolve_relative_import_absolute() -> None:
    """Should return module name for absolute import."""
    source = "from serger.constants import X"
    tree = ast.parse(source)
    node = tree.body[0]
    assert isinstance(node, ast.ImportFrom)

    result = mod_stitch._resolve_relative_import(node, "serger.actions")  # noqa: SLF001
    assert result == "serger.constants"


def test_resolve_relative_import_no_module() -> None:
    """Should handle relative import without module name."""
    source = "from . import something"
    tree = ast.parse(source)
    node = tree.body[0]
    assert isinstance(node, ast.ImportFrom)

    result = mod_stitch._resolve_relative_import(node, "serger.actions")  # noqa: SLF001
    assert result == "serger"


def test_is_internal_import_matches_package() -> None:
    """Should return True when module matches package exactly."""
    detected_packages = {"serger", "other"}
    assert mod_stitch._is_internal_import("serger", detected_packages) is True  # noqa: SLF001


def test_is_internal_import_starts_with_package() -> None:
    """Should return True when module starts with package."""
    detected_packages = {"serger", "other"}
    assert mod_stitch._is_internal_import("serger.actions", detected_packages) is True  # noqa: SLF001


def test_is_internal_import_no_match() -> None:
    """Should return False when module doesn't match any package."""
    detected_packages = {"serger", "other"}
    assert mod_stitch._is_internal_import("external.module", detected_packages) is False  # noqa: SLF001


def test_is_internal_import_false_match_prevention() -> None:
    """Should prevent false matches (e.g., 'foo_bar' matching 'foo')."""
    detected_packages = {"foo"}
    # 'foo_bar' should NOT match 'foo' because it doesn't start with 'foo.'
    assert mod_stitch._is_internal_import("foo_bar", detected_packages) is False  # noqa: SLF001
    # But 'foo.bar' should match
    assert mod_stitch._is_internal_import("foo.bar", detected_packages) is True  # noqa: SLF001


def test_extract_import_module_info_importfrom_absolute() -> None:
    """Should extract module info from absolute ImportFrom."""
    source = "from serger.constants import X"
    tree = ast.parse(source)
    node = tree.body[0]
    assert isinstance(node, ast.ImportFrom)

    detected_packages = {"serger"}
    result = mod_stitch._extract_import_module_info(  # noqa: SLF001
        node, "serger.actions", detected_packages
    )
    assert result == ("serger.constants", True)


def test_extract_import_module_info_importfrom_relative() -> None:
    """Should extract module info from relative ImportFrom."""
    source = "from .constants import X"
    tree = ast.parse(source)
    node = tree.body[0]
    assert isinstance(node, ast.ImportFrom)

    detected_packages = {"serger"}
    result = mod_stitch._extract_import_module_info(  # noqa: SLF001
        node, "serger.actions", detected_packages
    )
    assert result == ("serger.constants", True)


def test_extract_import_module_info_importfrom_external() -> None:
    """Should extract module info from external ImportFrom."""
    source = "from external.module import X"
    tree = ast.parse(source)
    node = tree.body[0]
    assert isinstance(node, ast.ImportFrom)

    detected_packages = {"serger"}
    result = mod_stitch._extract_import_module_info(  # noqa: SLF001
        node, "serger.actions", detected_packages
    )
    assert result == ("external.module", False)


def test_extract_import_module_info_import() -> None:
    """Should extract module info from Import."""
    source = "import serger.constants"
    tree = ast.parse(source)
    node = tree.body[0]
    assert isinstance(node, ast.Import)

    detected_packages = {"serger"}
    result = mod_stitch._extract_import_module_info(  # noqa: SLF001
        node, "serger.actions", detected_packages
    )
    assert result == ("serger.constants", True)


def test_extract_import_module_info_import_external() -> None:
    """Should extract module info from external Import."""
    source = "import external.module"
    tree = ast.parse(source)
    node = tree.body[0]
    assert isinstance(node, ast.Import)

    detected_packages = {"serger"}
    result = mod_stitch._extract_import_module_info(  # noqa: SLF001
        node, "serger.actions", detected_packages
    )
    assert result == ("external.module", False)


def test_extract_import_module_info_relative_beyond_root() -> None:
    """Should return None when relative import goes beyond root."""
    source = "from ...something import X"
    tree = ast.parse(source)
    node = tree.body[0]
    assert isinstance(node, ast.ImportFrom)

    detected_packages = {"serger"}
    result = mod_stitch._extract_import_module_info(  # noqa: SLF001
        node, "serger.actions", detected_packages
    )
    assert result is None


# Tests for _extract_internal_imports_for_deps
def test_extract_internal_imports_for_deps_absolute() -> None:
    """Should extract internal imports from absolute ImportFrom."""
    source = "from serger.constants import X"
    detected_packages = {"serger"}
    result = mod_stitch._extract_internal_imports_for_deps(  # noqa: SLF001
        source, "serger.actions", detected_packages
    )
    assert result == {"serger.constants"}


def test_extract_internal_imports_for_deps_relative() -> None:
    """Should extract internal imports from relative ImportFrom."""
    source = "from .constants import X"
    detected_packages = {"serger"}
    result = mod_stitch._extract_internal_imports_for_deps(  # noqa: SLF001
        source, "serger.actions", detected_packages
    )
    assert result == {"serger.constants"}


def test_extract_internal_imports_for_deps_relative_simple_name() -> None:
    """Should extract relative imports that resolve to simple names.

    Note: This tests the edge case where a relative import resolves to a
    simple name (no dots). In practice, this is rare but the extraction
    function should handle it.
    """
    # This scenario is hard to create in practice, but we test that
    # the function handles it correctly by checking the logic path
    # For a more realistic test, we use a relative import that resolves
    # to a package-prefixed name
    source = "from . import something"
    detected_packages = {"serger"}
    result = mod_stitch._extract_internal_imports_for_deps(  # noqa: SLF001
        source, "serger.sub", detected_packages
    )
    # The relative import "from . import something" in "serger.sub" resolves
    # to "serger", which is package-prefixed, so it should be included
    assert "serger" in result


def test_extract_internal_imports_for_deps_external() -> None:
    """Should not extract external imports."""
    source = "from external.module import X"
    detected_packages = {"serger"}
    result = mod_stitch._extract_internal_imports_for_deps(  # noqa: SLF001
        source, "serger.actions", detected_packages
    )
    assert result == set()


def test_extract_internal_imports_for_deps_import() -> None:
    """Should extract internal imports from Import."""
    source = "import serger.constants"
    detected_packages = {"serger"}
    result = mod_stitch._extract_internal_imports_for_deps(  # noqa: SLF001
        source, "serger.actions", detected_packages
    )
    assert result == {"serger.constants"}


def test_extract_internal_imports_for_deps_multiple_imports() -> None:
    """Should extract multiple internal imports."""
    source = """from serger.constants import X
from serger.utils import helper
import serger.actions
"""
    detected_packages = {"serger"}
    result = mod_stitch._extract_internal_imports_for_deps(  # noqa: SLF001
        source, "serger.main", detected_packages
    )
    assert result == {"serger.constants", "serger.utils", "serger.actions"}


def test_extract_internal_imports_for_deps_conditional_import() -> None:
    """Should extract imports inside conditional blocks."""
    source = """if not __STANDALONE__:
    from .namespace import apathetic_logging
"""
    detected_packages = {"serger"}
    result = mod_stitch._extract_internal_imports_for_deps(  # noqa: SLF001
        source, "serger.actions", detected_packages
    )
    assert "serger.namespace" in result


def test_extract_internal_imports_for_deps_relative_beyond_root() -> None:
    """Should skip relative imports that go beyond package root."""
    source = "from ...something import X"
    detected_packages = {"serger"}
    result = mod_stitch._extract_internal_imports_for_deps(  # noqa: SLF001
        source, "serger.actions", detected_packages
    )
    assert result == set()


def test_extract_internal_imports_for_deps_syntax_error() -> None:
    """Should return empty set on syntax error."""
    source = "def invalid syntax"
    detected_packages = {"serger"}
    result = mod_stitch._extract_internal_imports_for_deps(  # noqa: SLF001
        source, "serger.actions", detected_packages
    )
    assert result == set()


def test_extract_internal_imports_for_deps_mixed_internal_external() -> None:
    """Should extract only internal imports when mixed with external."""
    source = """from serger.constants import X
from external.module import Y
import serger.utils
"""
    detected_packages = {"serger"}
    result = mod_stitch._extract_internal_imports_for_deps(  # noqa: SLF001
        source, "serger.main", detected_packages
    )
    assert result == {"serger.constants", "serger.utils"}
    assert "external.module" not in result
