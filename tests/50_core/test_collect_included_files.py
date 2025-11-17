# tests/50_core/test_collect_included_files.py
"""Tests for collect_included_files() file collection and exclude filtering.

Adapted from test_copy_item.py - focuses on file filtering rather than copying.
"""

# we import `_` private for testing purposes only
# pyright: reportPrivateUsage=false

from pathlib import Path

import serger.build as mod_build
import serger.config.config_types as mod_config_types
from tests.utils.buildconfig import make_include_resolved, make_resolved


def test_collect_respects_excludes(tmp_path: Path) -> None:
    """collect_included_files should honor exclusion patterns."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("A = 1")
    (src / "b.py").write_text("B = 2")
    (src / "skip.py").write_text("SKIP = 1")

    includes = [make_include_resolved("src/*.py", tmp_path)]
    excludes = [make_resolved("src/skip.py", tmp_path)]

    # --- execute ---
    files, _file_to_include = mod_build.collect_included_files(includes, excludes)

    # --- verify ---
    file_set = set(files)
    assert (src / "a.py").resolve() in file_set
    assert (src / "b.py").resolve() in file_set
    assert (src / "skip.py").resolve() not in file_set


def test_collect_respects_nested_excludes(tmp_path: Path) -> None:
    """collect_included_files should handle nested exclude patterns."""
    # --- setup ---
    src = tmp_path / "src"
    sub = src / "sub"
    sub.mkdir(parents=True)
    (src / "a.py").write_text("A = 1")
    (sub / "skip.py").write_text("SKIP = 1")
    (sub / "keep.py").write_text("KEEP = 1")

    includes = [make_include_resolved("src/**", tmp_path)]
    excludes = [make_resolved("**/skip.py", tmp_path)]

    # --- execute ---
    files, _file_to_include = mod_build.collect_included_files(includes, excludes)

    # --- verify ---
    file_set = set(files)
    assert (src / "a.py").resolve() in file_set
    assert (sub / "keep.py").resolve() in file_set
    assert (sub / "skip.py").resolve() not in file_set


def test_collect_respects_directory_excludes(tmp_path: Path) -> None:
    """collect_included_files should handle directory-wide excludes."""
    # --- setup ---
    src = tmp_path / "src"
    skip_dir = src / "skip"
    skip_dir.mkdir(parents=True)
    (src / "a.py").write_text("A = 1")
    (skip_dir / "b.py").write_text("B = 1")

    includes = [make_include_resolved("src/**", tmp_path)]
    excludes = [make_resolved("src/skip/", tmp_path)]

    # --- execute ---
    files, _file_to_include = mod_build.collect_included_files(includes, excludes)

    # --- verify ---
    file_set = set(files)
    assert (src / "a.py").resolve() in file_set
    assert (skip_dir / "b.py").resolve() not in file_set


def test_collect_multiple_includes(tmp_path: Path) -> None:
    """collect_included_files should handle multiple include patterns."""
    # --- setup ---
    src1 = tmp_path / "src1"
    src2 = tmp_path / "src2"
    src1.mkdir()
    src2.mkdir()
    (src1 / "a.py").write_text("A = 1")
    (src2 / "b.py").write_text("B = 2")

    includes = [
        make_include_resolved("src1/*.py", tmp_path),
        make_include_resolved("src2/*.py", tmp_path),
    ]
    excludes: list[mod_config_types.PathResolved] = []

    # --- execute ---
    files, file_to_include = mod_build.collect_included_files(includes, excludes)

    # --- verify ---
    file_set = set(files)
    assert (src1 / "a.py").resolve() in file_set
    assert (src2 / "b.py").resolve() in file_set
    # Verify file_to_include mapping
    assert file_to_include[(src1 / "a.py").resolve()] == includes[0]
    assert file_to_include[(src2 / "b.py").resolve()] == includes[1]


def test_collect_exclude_with_different_root(tmp_path: Path) -> None:
    """collect_included_files should use each exclude's root correctly."""
    # --- setup ---
    src = tmp_path / "src"
    other = tmp_path / "other"
    src.mkdir()
    other.mkdir()
    (src / "a.py").write_text("A = 1")
    (src / "skip.py").write_text("SKIP = 1")
    (other / "skip.py").write_text("OTHER SKIP")

    includes = [make_include_resolved("src/*.py", tmp_path)]
    # Exclude from 'other' root shouldn't affect 'src' files
    excludes = [make_resolved("skip.py", other)]

    # --- execute ---
    files, _file_to_include = mod_build.collect_included_files(includes, excludes)

    # --- verify ---
    file_set = set(files)
    # src/skip.py should NOT be excluded because exclude root is 'other'
    assert (src / "skip.py").resolve() in file_set
    assert (src / "a.py").resolve() in file_set


def test_collect_exclude_patterns_with_parent_directory_includes(
    tmp_path: Path,
) -> None:
    """Exclude patterns should work when includes reference files outside root.

    This test verifies that exclude patterns like `**/__init__.py` work correctly
    when include patterns reference files outside the project root (using `../`).
    This matches the behavior of tools like rsync and ruff, where exclude patterns
    match against the actual file paths, not just paths relative to the exclude root.

    Behavior:
    - rsync: Exclude patterns are evaluated relative to the source directory
    - ruff: Exclude patterns match against absolute paths
    - serger: Should match `**/__init__.py` patterns even for files outside exclude root
    """
    # --- setup ---
    # Create structure:
    #   tmp_path/
    #     project/          (config root)
    #       config.json
    #     external/         (outside project root)
    #       pkg/
    #         __init__.py   (should be excluded)
    #         module.py     (should be included)
    #         subdir/
    #           __init__.py (should be excluded)
    #           other.py    (should be included)
    project = tmp_path / "project"
    project.mkdir()
    external = tmp_path / "external"
    pkg = external / "pkg"
    subdir = pkg / "subdir"
    subdir.mkdir(parents=True)

    (pkg / "__init__.py").write_text("# Package init")
    (pkg / "module.py").write_text("def func(): pass")
    (subdir / "__init__.py").write_text("# Subdir init")
    (subdir / "other.py").write_text("def other(): pass")

    # Include pattern goes outside project root using ../
    # Exclude pattern uses **/__init__.py to match all __init__.py files
    includes = [make_include_resolved("../external/pkg/**", project)]
    excludes = [make_resolved("**/__init__.py", project)]

    # --- execute ---
    files, _file_to_include = mod_build.collect_included_files(includes, excludes)

    # --- verify ---
    file_set = set(files)
    # __init__.py files should be excluded even though they're outside exclude root
    assert (pkg / "__init__.py").resolve() not in file_set
    assert (subdir / "__init__.py").resolve() not in file_set
    # Other Python files should be included
    assert (pkg / "module.py").resolve() in file_set
    assert (subdir / "other.py").resolve() in file_set
