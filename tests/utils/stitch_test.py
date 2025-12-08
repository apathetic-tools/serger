# tests/utils/stitch_test.py
"""Test utilities for stitch_modules testing."""

import sys
from pathlib import Path

import serger.stitch as mod_stitch


def is_serger_build_for_test(out_path: Path) -> bool:
    """Helper to compute is_serger_build for tests.

    Args:
        out_path: Path to the output file

    Returns:
        True if file doesn't exist or is a serger build, False otherwise
    """
    if not out_path.exists():
        return True  # Safe to write new files
    return mod_stitch.is_serger_build(out_path)


def cleanup_sys_modules(
    *patterns: str,
    exclude: str | None = None,
    exclude_file: Path | None = None,
) -> None:
    """Remove modules from sys.modules matching patterns.

    This helps avoid module pollution between tests. When loading stitched
    modules with the same package names, Python may return cached modules
    from previous test runs unless they're explicitly removed.

    Args:
        *patterns: Module name patterns (e.g., "testpkg", "app")
            Removes any module whose name contains any of these patterns
        exclude: Optional module name to keep (used to preserve the current
            stitched module when cleaning up other versions)
        exclude_file: Optional file path - if provided, modules from this
            file are kept (e.g., the file of a loaded stitched module)
    """
    modules_to_remove: list[str] = []
    for name in list(sys.modules.keys()):
        # Check if module matches any pattern
        if any(pattern in name for pattern in patterns):
            # Skip excluded module
            if exclude and name == exclude:
                continue
            # Skip modules from excluded file
            if exclude_file is not None:
                mod = sys.modules.get(name)
                if mod is not None:
                    mod_file = getattr(mod, "__file__", None)
                    if mod_file == str(exclude_file):
                        continue
            modules_to_remove.append(name)

    for name in modules_to_remove:
        del sys.modules[name]
