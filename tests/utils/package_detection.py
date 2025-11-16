# tests/utils/package_detection.py
"""Package detection utilities for test helpers.

Copied from serger.stitch to avoid circular dependencies.
"""

from pathlib import Path


def _find_package_root_for_file(file_path: Path) -> Path | None:
    """Find the package root for a file by walking up looking for __init__.py.

    Starting from the file's directory, walks up the directory tree while
    we find __init__.py files. The topmost directory with __init__.py is
    the package root.

    Args:
        file_path: Path to the Python file

    Returns:
        Path to the package root directory, or None if not found
    """
    current_dir = file_path.parent.resolve()
    last_package_dir: Path | None = None

    # Walk up from the file's directory
    while True:
        # Check if current directory has __init__.py
        init_file = current_dir / "__init__.py"
        if init_file.exists():
            # This directory is part of a package
            last_package_dir = current_dir
        else:
            # This directory doesn't have __init__.py, so we've gone past the package
            # Return the last directory that had __init__.py
            return last_package_dir

        # Move up one level
        parent = current_dir.parent
        if parent == current_dir:
            # Reached filesystem root
            return last_package_dir
        current_dir = parent


def detect_packages_from_files(
    file_paths: list[Path],
    package_name: str,
) -> set[str]:
    """Detect packages by walking up from files looking for __init__.py.

    Follows Python's import rules: only detects regular packages (with
    __init__.py files). Falls back to configured package_name if none detected.

    Args:
        file_paths: List of file paths to check
        package_name: Configured package name (used as fallback)

    Returns:
        Set of detected package names (always includes package_name)
    """
    detected: set[str] = set()

    # Detect packages from __init__.py files
    for file_path in file_paths:
        pkg_root = _find_package_root_for_file(file_path)
        if pkg_root:
            # Extract package name from directory name
            pkg_name = pkg_root.name
            detected.add(pkg_name)

    # Always include configured package (for fallback and multi-package scenarios)
    detected.add(package_name)

    return detected


def find_all_packages_under_path(root_path: Path) -> set[str]:
    """Find all package names under a directory by scanning for __init__.py files.

    Args:
        root_path: Path to the root directory to scan

    Returns:
        Set of package names found under the root directory
    """
    detected: set[str] = set()

    if not root_path.exists():
        return detected

    # Find all __init__.py files under root_path
    for init_file in root_path.rglob("__init__.py"):
        # Find the package root by walking up
        pkg_root = _find_package_root_for_file(init_file)
        if pkg_root:
            # Extract package name from root directory name
            # Relative to root_path to get the top-level package name
            try:
                rel_path = pkg_root.relative_to(root_path)
                # The first component is the top-level package name
                top_level_pkg = rel_path.parts[0]
                detected.add(top_level_pkg)
            except ValueError:
                # If pkg_root is not under root_path, skip it
                pass

    return detected
