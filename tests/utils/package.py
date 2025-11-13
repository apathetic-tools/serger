# tests/utils/package.py
"""Shared test helpers for creating test Python packages and file structures."""

from pathlib import Path


def make_test_package(
    pkg_dir: Path,
    *,
    init_content: str | None = None,
    module_name: str = "module",
    module_content: str | None = None,
    **extra: str,
) -> None:
    r"""Create a minimal test Python package structure.

    Args:
        pkg_dir: Directory where the package should be created
        init_content: Content for __init__.py (defaults to empty string)
        module_name: Name of the module file without .py extension
            (defaults to "module")
        module_content: Content for the module.py file
            (defaults to simple hello function)
        **extra: Additional files to create as filename: content pairs

    Examples:
        >>> # Simple usage with defaults
        >>> make_test_package(tmp_path / "mypkg")
        >>> # Custom module content
        >>> make_test_package(
        ...     tmp_path / "mypkg",
        ...     module_content='def hello():\n    return "custom"\n',
        ... )
        >>> # Multiple files
        >>> make_test_package(
        ...     tmp_path / "mypkg",
        ...     utils_content='def util():\n    pass\n',
        ... )
    """
    pkg_dir.mkdir()

    # Create __init__.py
    init_text = init_content if init_content is not None else ""
    (pkg_dir / "__init__.py").write_text(init_text, encoding="utf-8")

    # Create module.py (default behavior)
    if module_content is None:
        module_content = 'def hello():\n    return "world"\n'
    (pkg_dir / f"{module_name}.py").write_text(module_content, encoding="utf-8")

    # Create any additional files from **extra
    for key, content in extra.items():
        # Remove _content suffix if present (e.g., utils_content -> utils.py)
        file_path = key.removesuffix("_content") if key.endswith("_content") else key
        if not file_path.endswith(".py"):
            file_path = f"{file_path}.py"
        (pkg_dir / file_path).write_text(content, encoding="utf-8")
