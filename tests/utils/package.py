# tests/utils/package.py
"""Shared test helpers for creating test Python packages and file structures."""

from pathlib import Path


def make_test_package(
    pkg_dir: Path,
    module_content: str = 'def hello():\n    return "world"\n',
) -> None:
    """Create a minimal test Python package structure.

    Args:
        pkg_dir: Directory where the package should be created
        module_content: Content for the module.py file
            (defaults to simple hello function)
    """
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "module.py").write_text(module_content, encoding="utf-8")
