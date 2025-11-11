# tests/5_core/test_verify_all_modules_listed.py
"""Tests for verify_all_modules_listed function."""

import tempfile
from pathlib import Path

import pytest

import serger.stitch as mod_stitch


def test_all_modules_listed() -> None:
    """Should pass when all modules are listed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir)
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


def test_unlisted_module() -> None:
    """Should raise when module not in order or exclude."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir)
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


def test_excluded_module() -> None:
    """Should pass when unlisted module is in exclude list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir)
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
