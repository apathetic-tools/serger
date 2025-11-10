"""Tests for detect_name_collisions function."""

import pytest

import serger.stitch as mod_stitch


def test_no_collisions() -> None:
    """Should pass when no collisions exist."""
    sources = {
        "module_a.py": "def func_a(): pass",
        "module_b.py": "def func_b(): pass",
    }
    # Should not raise
    mod_stitch.detect_name_collisions(sources)


def test_collision_detected() -> None:
    """Should raise RuntimeError when collisions detected."""
    sources = {
        "module_a.py": "def foo(): pass",
        "module_b.py": "def foo(): pass",
    }
    with pytest.raises(RuntimeError):
        mod_stitch.detect_name_collisions(sources)


def test_ignore_dunder_names() -> None:
    """Should ignore special dunder names."""
    sources = {
        "module_a.py": "__version__ = '1.0'",
        "module_b.py": "__version__ = '2.0'",
    }
    # Should not raise (these are ignored)
    mod_stitch.detect_name_collisions(sources)
