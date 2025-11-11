# tests/5_core/test_resolve_order_paths.py
"""Tests for resolve_order_paths() order path resolution."""

# we import `_` private for testing purposes only
# pyright: reportPrivateUsage=false

from pathlib import Path

import pytest

import serger.build as mod_build


def test_resolve_relative_paths(tmp_path: Path) -> None:
    """Should resolve relative paths relative to config_root."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("A = 1")
    (src / "b.py").write_text("B = 2")

    included_files = [(src / "a.py").resolve(), (src / "b.py").resolve()]
    order = ["src/a.py", "src/b.py"]
    config_root = tmp_path

    # --- execute ---
    result = mod_build.resolve_order_paths(order, included_files, config_root)

    # --- verify ---
    assert len(result) == 2  # noqa: PLR2004
    assert result[0] == (src / "a.py").resolve()
    assert result[1] == (src / "b.py").resolve()


def test_resolve_absolute_paths(tmp_path: Path) -> None:
    """Should resolve absolute paths as-is."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("A = 1")

    included_files = [(src / "a.py").resolve()]
    order = [str((src / "a.py").resolve())]
    config_root = tmp_path

    # --- execute ---
    result = mod_build.resolve_order_paths(order, included_files, config_root)

    # --- verify ---
    assert len(result) == 1
    assert result[0] == (src / "a.py").resolve()


def test_resolve_missing_file_error(tmp_path: Path) -> None:
    """Should raise ValueError if order entry not in included files."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("A = 1")

    included_files = [(src / "a.py").resolve()]
    order = ["src/missing.py"]  # Not in included_files
    config_root = tmp_path

    # --- execute & verify ---
    with pytest.raises(ValueError, match="not in included files"):
        mod_build.resolve_order_paths(order, included_files, config_root)


def test_resolve_preserves_order(tmp_path: Path) -> None:
    """Should preserve the order of entries."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("A = 1")
    (src / "b.py").write_text("B = 2")
    (src / "c.py").write_text("C = 3")

    included_files = [
        (src / "a.py").resolve(),
        (src / "b.py").resolve(),
        (src / "c.py").resolve(),
    ]
    order = ["src/c.py", "src/a.py", "src/b.py"]  # Custom order
    config_root = tmp_path

    # --- execute ---
    result = mod_build.resolve_order_paths(order, included_files, config_root)

    # --- verify ---
    assert len(result) == 3  # noqa: PLR2004
    assert result[0] == (src / "c.py").resolve()
    assert result[1] == (src / "a.py").resolve()
    assert result[2] == (src / "b.py").resolve()
