# tests/50_core/test_verify_no_broken_imports.py
"""Tests for verify_no_broken_imports function."""

import pytest

import serger.stitch as mod_stitch


def test_no_broken_imports() -> None:
    """Should pass when all imports are resolved."""
    script = """
# === module_a.py ===
def func_a():
    pass

# === module_b.py ===
def func_b():
    pass
"""
    # Should not raise
    mod_stitch.verify_no_broken_imports(script, ["serger"])


def test_broken_import_detected() -> None:
    """Should raise RuntimeError for unresolved imports."""
    script = "import serger.missing_module"
    with pytest.raises(RuntimeError):
        mod_stitch.verify_no_broken_imports(script, ["serger"])
