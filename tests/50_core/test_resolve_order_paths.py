# tests/50_core/test_resolve_order_paths.py
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


def test_resolve_wildcard_pattern(tmp_path: Path) -> None:
    """Should expand wildcard patterns to match remaining files."""
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
    order = ["src/*"]  # Wildcard pattern
    config_root = tmp_path

    # --- execute ---
    result = mod_build.resolve_order_paths(order, included_files, config_root)

    # --- verify ---
    assert len(result) == 3  # noqa: PLR2004
    # Should be sorted alphabetically
    assert result[0] == (src / "a.py").resolve()
    assert result[1] == (src / "b.py").resolve()
    assert result[2] == (src / "c.py").resolve()


def test_resolve_explicit_then_wildcard(tmp_path: Path) -> None:
    """Should order explicit files first, then expand wildcard for remaining files."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("A = 1")
    (src / "b.py").write_text("B = 2")
    (src / "c.py").write_text("C = 3")
    (src / "d.py").write_text("D = 4")

    included_files = [
        (src / "a.py").resolve(),
        (src / "b.py").resolve(),
        (src / "c.py").resolve(),
        (src / "d.py").resolve(),
    ]
    order = ["src/c.py", "src/*"]  # Explicit first, then wildcard
    config_root = tmp_path

    # --- execute ---
    result = mod_build.resolve_order_paths(order, included_files, config_root)

    # --- verify ---
    assert len(result) == 4  # noqa: PLR2004
    # c.py should be first (explicit)
    assert result[0] == (src / "c.py").resolve()
    # Rest should be sorted alphabetically (a, b, d)
    assert result[1] == (src / "a.py").resolve()
    assert result[2] == (src / "b.py").resolve()
    assert result[3] == (src / "d.py").resolve()


def test_resolve_wildcard_excludes_already_ordered(tmp_path: Path) -> None:
    """Wildcard should not include files already explicitly ordered."""
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
    order = ["src/a.py", "src/b.py", "src/*"]  # Explicit a, b, then wildcard
    config_root = tmp_path

    # --- execute ---
    result = mod_build.resolve_order_paths(order, included_files, config_root)

    # --- verify ---
    assert len(result) == 3  # noqa: PLR2004
    assert result[0] == (src / "a.py").resolve()
    assert result[1] == (src / "b.py").resolve()
    # Wildcard should only match c.py (a and b already ordered)
    assert result[2] == (src / "c.py").resolve()


def test_resolve_wildcard_no_matches(tmp_path: Path) -> None:
    """Wildcard that matches no files should not error."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("A = 1")

    included_files = [(src / "a.py").resolve()]
    order = ["src/a.py", "src/nonexistent/*"]  # Wildcard that won't match
    config_root = tmp_path

    # --- execute ---
    result = mod_build.resolve_order_paths(order, included_files, config_root)

    # --- verify ---
    assert len(result) == 1
    assert result[0] == (src / "a.py").resolve()


def test_resolve_multiple_wildcards(tmp_path: Path) -> None:
    """Should handle multiple wildcard patterns."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    subdir = src / "subdir"
    subdir.mkdir()
    (src / "a.py").write_text("A = 1")
    (src / "b.py").write_text("B = 2")
    (subdir / "c.py").write_text("C = 3")

    included_files = [
        (src / "a.py").resolve(),
        (src / "b.py").resolve(),
        (subdir / "c.py").resolve(),
    ]
    order = ["src/a.py", "src/*", "src/subdir/*"]  # Explicit, then wildcards
    config_root = tmp_path

    # --- execute ---
    result = mod_build.resolve_order_paths(order, included_files, config_root)

    # --- verify ---
    assert len(result) == 3  # noqa: PLR2004
    assert result[0] == (src / "a.py").resolve()
    # src/* should match b.py (a already ordered)
    assert result[1] == (src / "b.py").resolve()
    # src/subdir/* should match c.py
    assert result[2] == (subdir / "c.py").resolve()


def test_resolve_trailing_slash_directory(tmp_path: Path) -> None:
    """Should treat trailing slash as recursive directory match."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    subdir = src / "subdir"
    subdir.mkdir()
    (src / "a.py").write_text("A = 1")
    (subdir / "b.py").write_text("B = 2")

    included_files = [
        (src / "a.py").resolve(),
        (subdir / "b.py").resolve(),
    ]
    order = ["src/"]  # Trailing slash = recursive
    config_root = tmp_path

    # --- execute ---
    result = mod_build.resolve_order_paths(order, included_files, config_root)

    # --- verify ---
    assert len(result) == 2  # noqa: PLR2004
    # Should be sorted alphabetically
    assert result[0] == (src / "a.py").resolve()
    assert result[1] == (subdir / "b.py").resolve()


def test_resolve_recursive_pattern(tmp_path: Path) -> None:
    """Should treat /** as explicit recursive pattern."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    subdir = src / "subdir"
    subdir.mkdir()
    (src / "a.py").write_text("A = 1")
    (subdir / "b.py").write_text("B = 2")

    included_files = [
        (src / "a.py").resolve(),
        (subdir / "b.py").resolve(),
    ]
    order = ["src/**"]  # Explicit recursive pattern
    config_root = tmp_path

    # --- execute ---
    result = mod_build.resolve_order_paths(order, included_files, config_root)

    # --- verify ---
    assert len(result) == 2  # noqa: PLR2004
    # Should be sorted alphabetically
    assert result[0] == (src / "a.py").resolve()
    assert result[1] == (subdir / "b.py").resolve()


def test_resolve_directory_without_slash(tmp_path: Path) -> None:
    """Should treat directory without slash as recursive match."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    subdir = src / "subdir"
    subdir.mkdir()
    (src / "a.py").write_text("A = 1")
    (subdir / "b.py").write_text("B = 2")

    included_files = [
        (src / "a.py").resolve(),
        (subdir / "b.py").resolve(),
    ]
    order = ["src"]  # Directory without slash = recursive
    config_root = tmp_path

    # --- execute ---
    result = mod_build.resolve_order_paths(order, included_files, config_root)

    # --- verify ---
    assert len(result) == 2  # noqa: PLR2004
    # Should be sorted alphabetically
    assert result[0] == (src / "a.py").resolve()
    assert result[1] == (subdir / "b.py").resolve()


def test_resolve_non_recursive_vs_recursive(tmp_path: Path) -> None:
    """Should distinguish between non-recursive (*) and recursive (/, **) patterns."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    subdir = src / "subdir"
    subdir.mkdir()
    (src / "a.py").write_text("A = 1")
    (subdir / "b.py").write_text("B = 2")

    included_files = [
        (src / "a.py").resolve(),
        (subdir / "b.py").resolve(),
    ]
    order = ["src/*"]  # Non-recursive glob
    config_root = tmp_path

    # --- execute ---
    result = mod_build.resolve_order_paths(order, included_files, config_root)

    # --- verify ---
    assert len(result) == 1  # Only matches direct children, not subdir
    assert result[0] == (src / "a.py").resolve()
