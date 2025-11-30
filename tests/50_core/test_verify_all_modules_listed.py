# tests/50_core/test_verify_all_modules_listed.py
"""Tests for verify_all_modules_listed function."""

from pathlib import Path

import pytest

import serger.stitch as mod_stitch


def test_all_modules_listed(tmp_path: Path) -> None:
    """Should pass when all modules are listed."""
    src_dir = tmp_path
    (src_dir / "module_a.py").touch()
    (src_dir / "module_b.py").touch()

    file_paths = [
        (src_dir / "module_a.py").resolve(),
        (src_dir / "module_b.py").resolve(),
    ]
    order_paths = file_paths
    exclude_paths: list[Path] = []

    # Should not raise
    mod_stitch.verify_all_modules_listed(file_paths, order_paths, exclude_paths)


def test_unlisted_module(tmp_path: Path) -> None:
    """Should raise when module not in order or exclude."""
    src_dir = tmp_path
    (src_dir / "module_a.py").touch()
    (src_dir / "module_b.py").touch()

    file_paths = [
        (src_dir / "module_a.py").resolve(),
        (src_dir / "module_b.py").resolve(),
    ]
    order_paths = [(src_dir / "module_a.py").resolve()]
    exclude_paths: list[Path] = []

    with pytest.raises(RuntimeError):
        mod_stitch.verify_all_modules_listed(file_paths, order_paths, exclude_paths)


def test_excluded_module(tmp_path: Path) -> None:
    """Should pass when unlisted module is in exclude list."""
    src_dir = tmp_path
    (src_dir / "module_a.py").touch()
    (src_dir / "module_b.py").touch()

    file_paths = [
        (src_dir / "module_a.py").resolve(),
        (src_dir / "module_b.py").resolve(),
    ]
    order_paths = [(src_dir / "module_a.py").resolve()]
    exclude_paths = [(src_dir / "module_b.py").resolve()]

    # Should not raise (module_b is excluded)
    mod_stitch.verify_all_modules_listed(file_paths, order_paths, exclude_paths)
