# tests/5_core/test_strip_redundant_blocks.py
"""Tests for strip_redundant_blocks function."""

import serger.stitch as mod_stitch


def test_strip_shebang() -> None:
    """Should remove shebang line."""
    code = """#!/usr/bin/env python3
def foo():
    pass
"""
    result = mod_stitch.strip_redundant_blocks(code)
    assert "#!/usr/bin/env python3" not in result
    assert "def foo():" in result


def test_strip_main_guard() -> None:
    """Should remove __main__ guard."""
    code = """def foo():
    pass

if __name__ == "__main__":
    print("hello")
"""
    result = mod_stitch.strip_redundant_blocks(code)
    assert "if __name__" not in result
    assert 'print("hello")' not in result
    assert "def foo():" in result


def test_strip_both() -> None:
    """Should remove both shebang and __main__."""
    code = """#!/usr/bin/env python3
def foo():
    pass

if __name__ == "__main__":
    foo()
"""
    result = mod_stitch.strip_redundant_blocks(code)
    assert "#!/usr/bin/env python3" not in result
    assert "if __name__" not in result
    assert "def foo():" in result
