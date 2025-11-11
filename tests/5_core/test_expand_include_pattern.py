# tests/5_core/test_expand_include_pattern.py
"""Tests for expand_include_pattern() file discovery logic.

Adapted from test_priv__compute_dest.py - focuses on file discovery
rather than destination computation.
"""

# we import `_` private for testing purposes only
# pyright: reportPrivateUsage=false

from pathlib import Path

import serger.build as mod_build
from tests.utils.buildconfig import make_include_resolved


def test_expand_trailing_slash_directory(tmp_path: Path) -> None:
    """Trailing slash directory should recursively find all .py files."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("A = 1")
    (src / "b.py").write_text("B = 2")
    sub = src / "sub"
    sub.mkdir()
    (sub / "c.py").write_text("C = 3")
    (sub / "not_py.txt").write_text("not python")

    include = make_include_resolved("src/", tmp_path)

    # --- execute ---
    result = mod_build.expand_include_pattern(include)

    # --- verify ---
    result_set = set(result)
    assert (src / "a.py").resolve() in result_set
    assert (src / "b.py").resolve() in result_set
    assert (sub / "c.py").resolve() in result_set
    assert (sub / "not_py.txt").resolve() not in result_set  # Only .py files


def test_expand_star_star_glob(tmp_path: Path) -> None:
    """'src/**' should recursively find all .py files."""
    # --- setup ---
    src = tmp_path / "src"
    deep = src / "deep" / "nested"
    deep.mkdir(parents=True)
    (deep / "x.py").write_text("X = 1")
    (deep / "y.txt").write_text("not python")

    include = make_include_resolved("src/**", tmp_path)

    # --- execute ---
    result = mod_build.expand_include_pattern(include)

    # --- verify ---
    result_set = set(result)
    assert (deep / "x.py").resolve() in result_set
    assert (deep / "y.txt").resolve() not in result_set  # Only .py files


def test_expand_top_level_glob(tmp_path: Path) -> None:
    """'*.py' should find top-level .py files."""
    # --- setup ---
    (tmp_path / "a.py").write_text("A = 1")
    (tmp_path / "b.py").write_text("B = 2")
    (tmp_path / "c.txt").write_text("not python")

    include = make_include_resolved("*.py", tmp_path)

    # --- execute ---
    result = mod_build.expand_include_pattern(include)

    # --- verify ---
    result_set = set(result)
    assert (tmp_path / "a.py").resolve() in result_set
    assert (tmp_path / "b.py").resolve() in result_set
    assert (tmp_path / "c.txt").resolve() not in result_set  # Only .py files


def test_expand_literal_file(tmp_path: Path) -> None:
    """Literal file path should return that file if it's a .py file."""
    # --- setup ---
    (tmp_path / "main.py").write_text("MAIN = 1")
    (tmp_path / "readme.txt").write_text("not python")

    include = make_include_resolved("main.py", tmp_path)

    # --- execute ---
    result = mod_build.expand_include_pattern(include)

    # --- verify ---
    assert len(result) == 1
    assert result[0] == (tmp_path / "main.py").resolve()


def test_expand_literal_non_py_file(tmp_path: Path) -> None:
    """Literal non-.py file should return empty list."""
    # --- setup ---
    (tmp_path / "readme.txt").write_text("not python")

    include = make_include_resolved("readme.txt", tmp_path)

    # --- execute ---
    result = mod_build.expand_include_pattern(include)

    # --- verify ---
    assert result == []


def test_expand_nonexistent_directory(tmp_path: Path) -> None:
    """Nonexistent directory should return empty list."""
    # --- setup ---
    include = make_include_resolved("nonexistent/", tmp_path)

    # --- execute ---
    result = mod_build.expand_include_pattern(include)

    # --- verify ---
    assert result == []


def test_expand_glob_pattern_with_subdir(tmp_path: Path) -> None:
    """Glob pattern 'src/*.py' should find .py files in src directory."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("A = 1")
    (src / "b.py").write_text("B = 2")
    (src / "c.txt").write_text("not python")

    include = make_include_resolved("src/*.py", tmp_path)

    # --- execute ---
    result = mod_build.expand_include_pattern(include)

    # --- verify ---
    result_set = set(result)
    assert (src / "a.py").resolve() in result_set
    assert (src / "b.py").resolve() in result_set
    assert (src / "c.txt").resolve() not in result_set  # Only .py files
