# tests/5_core/test_process_comments.py

"""Tests for comment processing functionality."""

import serger.stitch as mod_stitch


def test_process_comments_keep() -> None:
    """Test that 'keep' mode preserves all comments."""
    code = """# This is a comment
def func():
    # Another comment
    return 42  # Inline comment
"""
    result = mod_stitch.process_comments(code, "keep")
    assert result == code


def test_process_comments_strip() -> None:
    """Test that 'strip' mode removes all comments but preserves docstrings."""
    code = """# This comment should be removed
def func():
    \"\"\"This docstring should be kept.\"\"\"
    # This comment should be removed
    return 42  # This inline comment should be removed
"""
    expected = """def func():
    \"\"\"This docstring should be kept.\"\"\"
    return 42
"""
    result = mod_stitch.process_comments(code, "strip")
    assert result == expected


def test_process_comments_strip_preserves_docstrings() -> None:
    """Test that 'strip' mode preserves docstrings."""
    code = '''def func():
    """This is a docstring with # inside it."""
    return 42
'''
    result = mod_stitch.process_comments(code, "strip")
    assert result == code


def test_process_comments_strip_preserves_strings() -> None:
    """Test that 'strip' mode preserves string literals with #."""
    code = """def func():
    msg = "This string has # a hash"
    return msg
"""
    result = mod_stitch.process_comments(code, "strip")
    assert result == code


def test_process_comments_inline() -> None:
    """Test that 'inline' mode keeps only inline comments."""
    code = """# This standalone comment should be removed
def func():
    # This standalone comment should be removed
    return 42  # This inline comment should be kept
"""
    expected = """def func():
    return 42  # This inline comment should be kept
"""
    result = mod_stitch.process_comments(code, "inline")
    assert result == expected


def test_process_comments_inline_preserves_code() -> None:
    """Test that 'inline' mode preserves all code lines."""
    code = """def func():
    x = 1
    y = 2
    return x + y
"""
    result = mod_stitch.process_comments(code, "inline")
    assert result == code


def test_process_comments_ignores_noqa() -> None:
    """Test that 'ignores' mode keeps noqa comments."""
    code = """def func():
    x = 1  # noqa: F401
    y = 2  # This comment should be removed
    return x + y  # noqa
"""
    expected = """def func():
    x = 1  # noqa: F401
    y = 2
    return x + y  # noqa
"""
    result = mod_stitch.process_comments(code, "ignores")
    assert result == expected


def test_process_comments_ignores_type_ignore() -> None:
    """Test that 'ignores' mode keeps type: ignore comments."""
    code = """def func():
    x: int = "bad"  # type: ignore[assignment]
    y = 2  # This comment should be removed
"""
    expected = """def func():
    x: int = "bad"  # type: ignore[assignment]
    y = 2
"""
    result = mod_stitch.process_comments(code, "ignores")
    assert result == expected


def test_process_comments_ignores_pyright() -> None:
    """Test that 'ignores' mode keeps pyright: ignore comments."""
    code = """def func():
    x = 1  # pyright: ignore[reportUnknownVariableType]
    y = 2  # This comment should be removed
"""
    expected = """def func():
    x = 1  # pyright: ignore[reportUnknownVariableType]
    y = 2
"""
    result = mod_stitch.process_comments(code, "ignores")
    assert result == expected


def test_process_comments_ignores_mypy() -> None:
    """Test that 'ignores' mode keeps mypy: ignore comments."""
    code = """def func():
    x = 1  # mypy: ignore[assignment]
    y = 2  # This comment should be removed
"""
    expected = """def func():
    x = 1  # mypy: ignore[assignment]
    y = 2
"""
    result = mod_stitch.process_comments(code, "ignores")
    assert result == expected


def test_process_comments_ignores_ruff() -> None:
    """Test that 'ignores' mode keeps ruff: noqa comments."""
    code = """def func():
    x = 1  # ruff: noqa: F401
    y = 2  # This comment should be removed
"""
    expected = """def func():
    x = 1  # ruff: noqa: F401
    y = 2
"""
    result = mod_stitch.process_comments(code, "ignores")
    assert result == expected


def test_process_comments_ignores_serger() -> None:
    """Test that 'ignores' mode keeps serger: no-move comments."""
    code = """from .module import func  # serger: no-move
from .other import other  # This comment should be removed
"""
    expected = """from .module import func  # serger: no-move
from .other import other
"""
    result = mod_stitch.process_comments(code, "ignores")
    assert result == expected


def test_process_comments_ignores_case_insensitive() -> None:
    """Test that ignore pattern matching is case-insensitive."""
    code = """def func():
    x = 1  # NOQA: F401
    y = 2  # Type: Ignore
    z = 3  # PYRIGHT: ignore
"""
    expected = """def func():
    x = 1  # NOQA: F401
    y = 2  # Type: Ignore
    z = 3  # PYRIGHT: ignore
"""
    result = mod_stitch.process_comments(code, "ignores")
    assert result == expected


def test_process_comments_ignores_standalone() -> None:
    """Test that 'ignores' mode keeps standalone ignore comments."""
    code = """# noqa: F401
def func():
    return 42
"""
    result = mod_stitch.process_comments(code, "ignores")
    assert result == code


def test_process_comments_ignores_removes_non_ignore() -> None:
    """Test that 'ignores' mode removes non-ignore comments."""
    code = """# This comment should be removed
def func():
    # This comment should be removed
    return 42  # This comment should be removed
"""
    expected = """def func():
    return 42
"""
    result = mod_stitch.process_comments(code, "ignores")
    assert result == expected


def test_process_comments_preserves_newlines() -> None:
    """Test that comment processing preserves newlines."""
    code = """def func():
    x = 1
    # Comment
    y = 2
"""
    result_strip = mod_stitch.process_comments(code, "strip")
    result_inline = mod_stitch.process_comments(code, "inline")
    result_ignores = mod_stitch.process_comments(code, "ignores")

    # All should preserve the structure
    assert "\n" in result_strip
    assert "\n" in result_inline
    assert "\n" in result_ignores


def test_process_comments_with_multiline_strings() -> None:
    """Test that comment processing handles multiline strings correctly."""
    code = '''def func():
    msg = """This is a
multiline string with # inside"""
    return msg  # This comment should be processed
'''
    result_strip = mod_stitch.process_comments(code, "strip")
    # The # inside the string should be preserved (but multiline strings
    # are split across lines, so we check for the string content)
    assert "multiline string with" in result_strip
    # The comment at the end should be removed
    assert "# This comment should be processed" not in result_strip
