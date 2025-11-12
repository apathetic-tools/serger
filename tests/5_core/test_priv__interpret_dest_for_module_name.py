# tests/5_core/test_priv__interpret_dest_for_module_name.py
"""Tests for _interpret_dest_for_module_name() dest parameter interpretation.

Adapted from test_priv__compute_dest.py - focuses on dest interpretation
for module name derivation rather than file copying.
"""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

from pathlib import Path
from typing import Any

# Import submodule - works in both installed and singlefile modes
# (singlefile mode excludes __init__.py but includes submodules)
import serger.utils.utils_modules as mod_utils_modules


class _MockUtils:
    """Mock utils module for testing private functions."""

    def _interpret_dest_for_module_name(
        self,
        file_path: Path,
        include_root: Path,
        include_pattern: str,
        dest: Path | str,
    ) -> Path:
        return mod_utils_modules._interpret_dest_for_module_name(
            file_path, include_root, include_pattern, dest
        )


mod_utils: Any = _MockUtils()


def test_interpret_dest_explicit_dest(tmp_path: Path) -> None:
    """Explicit 'dest' should be used directly."""
    # --- setup ---
    file_path = tmp_path / "a" / "b.py"
    file_path.parent.mkdir(parents=True)
    include_root = tmp_path
    include_pattern = "a/*.py"
    dest = Path("custom")

    # --- execute ---
    result = mod_utils._interpret_dest_for_module_name(
        file_path, include_root, include_pattern, dest
    )

    # --- verify ---
    assert result == dest


def test_interpret_dest_with_glob_pattern(tmp_path: Path) -> None:
    """Glob pattern should strip non-glob prefix correctly."""
    # --- setup ---
    file_path = tmp_path / "a" / "sub" / "b.py"
    file_path.parent.mkdir(parents=True)
    include_root = tmp_path
    include_pattern = "a/*"
    dest = Path("custom")

    # --- execute ---
    result = mod_utils._interpret_dest_for_module_name(
        file_path, include_root, include_pattern, dest
    )

    # --- verify ---
    # The prefix 'a/' (the glob root) is stripped — file goes under 'custom/sub/b.py'
    assert result == dest / "sub" / "b.py"


def test_interpret_dest_without_glob(tmp_path: Path) -> None:
    """Non-glob pattern should preserve relative path structure."""
    # --- setup ---
    file_path = tmp_path / "docs" / "readme.py"
    file_path.parent.mkdir(parents=True)
    include_root = tmp_path
    include_pattern = "docs/readme.py"
    dest = Path("custom")

    # --- execute ---
    result = mod_utils._interpret_dest_for_module_name(
        file_path, include_root, include_pattern, dest
    )

    # --- verify ---
    assert result == dest / "docs" / "readme.py"


def test_interpret_dest_root_not_ancestor(tmp_path: Path) -> None:
    """Falls back safely when root is not an ancestor of file_path."""
    # --- setup ---
    file_path = Path("/etc/hosts")  # Absolute path outside tmp_path
    include_root = tmp_path
    include_pattern = "*.txt"
    dest = Path("custom")

    # --- execute ---
    result = mod_utils._interpret_dest_for_module_name(
        file_path, include_root, include_pattern, dest
    )

    # --- verify ---
    # When root and file_path don't align, fallback uses just the filename
    assert result == dest / "hosts"


def test_interpret_dest_with_trailing_slash(tmp_path: Path) -> None:
    """Trailing slash pattern should preserve relative structure."""
    # --- setup ---
    file_path = tmp_path / "src" / "a.py"
    file_path.parent.mkdir(parents=True)
    include_root = tmp_path
    include_pattern = "src/"
    dest = Path("custom")

    # --- execute ---
    result = mod_utils._interpret_dest_for_module_name(
        file_path, include_root, include_pattern, dest
    )

    # --- verify ---
    assert result == dest / "a.py"


def test_interpret_dest_absolute_dest(tmp_path: Path) -> None:
    """Absolute dest path should be used as-is."""
    # --- setup ---
    file_path = tmp_path / "a" / "b.py"
    file_path.parent.mkdir(parents=True)
    include_root = tmp_path
    include_pattern = "a/*.py"
    dest = Path("/absolute/custom")

    # --- execute ---
    result = mod_utils._interpret_dest_for_module_name(
        file_path, include_root, include_pattern, dest
    )

    # --- verify ---
    assert result == Path("/absolute/custom").resolve()
