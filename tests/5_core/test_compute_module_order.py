"""Tests for compute_module_order function."""

import tempfile
from pathlib import Path

import pytest

import serger.stitch as mod_stitch


def test_simple_order() -> None:
    """Should return order for modules with no dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir)
        (src_dir / "a.py").write_text("# module a\n")
        (src_dir / "b.py").write_text("# module b\n")

        order = mod_stitch.compute_module_order(src_dir, ["a", "b"], "pkg")
        assert set(order) == {"a", "b"}


def test_dependency_order() -> None:
    """Should correct order based on import dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir)
        (src_dir / "base.py").write_text("# base\n")
        (src_dir / "derived.py").write_text("from pkg.base import something\n")

        order = mod_stitch.compute_module_order(src_dir, ["derived", "base"], "pkg")
        # base must come before derived
        assert order.index("base") < order.index("derived")


def test_circular_import_error() -> None:
    """Should raise RuntimeError on circular imports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir)
        (src_dir / "a.py").write_text("from pkg.b import x\n")
        (src_dir / "b.py").write_text("from pkg.a import y\n")

        with pytest.raises(RuntimeError):
            mod_stitch.compute_module_order(src_dir, ["a", "b"], "pkg")
