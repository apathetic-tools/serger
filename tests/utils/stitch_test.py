# tests/utils/stitch_test.py
"""Test utilities for stitch_modules testing."""

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
