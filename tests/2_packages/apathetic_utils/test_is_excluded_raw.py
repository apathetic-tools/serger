# tests/0_independant/test_is_excluded_raw.py
"""Tests for is_excluded_raw and its wrapper is_excluded.

Checklist:
- matches_patterns — simple include/exclude match using relative glob patterns.
- relative_path — confirms relative path resolution against root.
- outside_root — verifies paths outside root never match (non-**/ patterns).
- absolute_pattern — ensures absolute patterns under the same root are matched.
- file_root_special_case — handles case where root itself is a file, not a directory.
- mixed_patterns — validates mixed matching and non-matching patterns.
- wrapper_delegates — checks that the wrapper forwards args correctly.
- gitignore_double_star_diff — '**' not recursive unlike gitignore in ≤Py3.10.
- double_star_outside_root_simple — **/ patterns match files outside root (simple).
- double_star_outside_root_complex — **/ patterns match files outside root (complex).
- double_star_inside_root — **/ patterns still work for files inside root.
- double_star_nested_pattern — nested **/ patterns work correctly.
- double_star_outside_root_negative — **/ patterns don't match when they shouldn't.
- double_star_mixed_patterns — mix of **/ and non-**/ patterns work correctly.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

import apathetic_utils.matching as amod_utils_matching
import apathetic_utils.system as amod_utils_system
from tests.utils import patch_everywhere


def test_is_excluded_raw_matches_patterns(tmp_path: Path) -> None:
    """Verify exclude pattern matching works correctly.

    Example:
      path:     /tmp/.../foo/bar.txt
      root:     /tmp/...
      pattern:  ["foo/*"]
      Result: True
      Explanation: pattern 'foo/*' matches 'foo/bar.txt' relative to root.

    """
    # --- setup ---
    root = tmp_path
    file = root / "foo/bar.txt"
    file.parent.mkdir(parents=True)
    file.touch()

    # --- execute + verify ---
    assert amod_utils_matching.is_excluded_raw(file, ["foo/*"], root)
    assert not amod_utils_matching.is_excluded_raw(file, ["baz/*"], root)


def test_is_excluded_raw_relative_path(tmp_path: Path) -> None:
    """Handles relative file path relative to given root.

    Example:
      path:     "src/file.txt"
      root:     /tmp/.../
      pattern:  ["src/*"]
      Result: True
      Explanation: path is relative; pattern matches within the same root.

    """
    # --- setup ---
    root = tmp_path
    (root / "src").mkdir()
    (root / "src/file.txt").touch()

    rel_path = Path("src/file.txt")

    # --- execute + verify ---
    assert amod_utils_matching.is_excluded_raw(rel_path, ["src/*"], root)
    assert not amod_utils_matching.is_excluded_raw(rel_path, ["dist/*"], root)


def test_is_excluded_raw_outside_root(tmp_path: Path) -> None:
    """Paths outside the root should never match.

    Example:
      path:     /tmp/outside.txt
      root:     /tmp/root/
      pattern:  ["*.txt"]
      Result: False
      Explanation: file is not under root; function skips comparison.

    """
    # --- setup ---
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.touch()

    # --- execute + verify ---
    assert not amod_utils_matching.is_excluded_raw(outside, ["*.txt"], root)


def test_is_excluded_raw_absolute_pattern(tmp_path: Path) -> None:
    """Absolute patterns matching under the same root should match.

    Example:
      path:     /tmp/.../a/b/c.txt
      root:     /tmp/.../
      pattern:  ["/tmp/.../a/b/*.txt"]
      Result: True
      Explanation: pattern is absolute but lies within root;
                   converted to relative 'a/b/*.txt'.

    """
    # --- setup ---
    root = tmp_path
    file = root / "a/b/c.txt"
    file.parent.mkdir(parents=True)
    file.touch()

    abs_pattern = str(root / "a/b/*.txt")

    # --- execute + verify ---
    assert amod_utils_matching.is_excluded_raw(file, [abs_pattern], root)
    assert not amod_utils_matching.is_excluded_raw(file, [str(root / "x/*.txt")], root)


def test_is_excluded_raw_file_root_special_case(tmp_path: Path) -> None:
    """If the root itself is a file, match it directly.

    Example:
      path:     data.csv
      root:     /tmp/.../data.csv
      pattern:  []
      Result: True
      Explanation: root is a file; function returns True
                   when path resolves to that file.

    """
    # --- setup ---
    root_file = tmp_path / "data.csv"
    root_file.touch()

    # path argument can be either relative or absolute
    rel_same = Path("data.csv")
    abs_same = root_file

    # --- execute + verify ---
    assert amod_utils_matching.is_excluded_raw(rel_same, [], root_file)
    assert amod_utils_matching.is_excluded_raw(abs_same, [], root_file)

    # unrelated file should not match
    other = tmp_path / "other.csv"
    other.touch()
    assert not amod_utils_matching.is_excluded_raw(other, [], root_file)


def test_is_excluded_raw_mixed_patterns(tmp_path: Path) -> None:
    """Mix of matching and non-matching patterns should behave predictably.

    Example:
      path:     /tmp/.../dir/sample.tmp
      root:     /tmp/.../
      pattern:  ["*.py", "dir/*.tmp", "ignore/*"]
      Result: True
      Explanation: second pattern matches; earlier and later do not.

    """
    # --- setup ---
    root = tmp_path
    file = root / "dir/sample.tmp"
    file.parent.mkdir(parents=True)
    file.touch()

    patterns = ["*.py", "dir/*.tmp", "ignore/*"]

    # --- execute + verify ---
    assert amod_utils_matching.is_excluded_raw(file, patterns, root)


def test_is_excluded_raw_gitignore_double_star(tmp_path: Path) -> None:
    """Document that gitignore's '**' recursion IS emulated.

    Example:
      path:     /tmp/.../dir/sub/file.py
      root:     /tmp/.../
      pattern:  ["dir/**/*.py"]
      Result:   True  (Python ≥3.11)
                True  (Python ≤3.10)
      Explanation:
        - In Python ≤3.10, we backport 3.11 behaviour.
        - In Python ≥3.11, fnmatch matches recursively across directories.
    """
    # --- setup ---
    root = tmp_path
    nested = root / "dir/sub/file.py"
    nested.parent.mkdir(parents=True)
    nested.touch()

    # --- execute ---
    result = amod_utils_matching.is_excluded_raw(nested, ["dir/**/*.py"], root)

    # --- verify ---
    assert result, "Expected True on Python ≥3.11 where '**' is recursive"


def test_gitignore_double_star_backport_py310(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # --- setup ---
    root = tmp_path
    nested = root / "dir/sub/file.py"
    nested.parent.mkdir(parents=True)
    nested.touch()

    # --- patch and execute ---
    # Force utils to think it's running on Python 3.10
    fake_sys = SimpleNamespace(version_info=(3, 10, 0))
    patch_everywhere(
        monkeypatch,
        amod_utils_system,
        "get_sys_version_info",
        lambda: fake_sys.version_info,
    )
    result = amod_utils_matching.is_excluded_raw(nested, ["dir/**/*.py"], root)

    # --- verify ---
    # Assert: backport should match recursively on 3.10
    assert result is True


def test_is_excluded_raw_double_star_outside_root_simple(tmp_path: Path) -> None:
    """**/ patterns should match files outside root (matching rsync/ruff behavior).

    Example:
      path:     /tmp/external/pkg/__init__.py
      root:     /tmp/project/
      pattern:  ["**/__init__.py"]
      Result: True
      Explanation: **/ patterns match against filename and absolute path,
                   even when file is outside the exclude root.
    """
    # --- setup ---
    root = tmp_path / "project"
    root.mkdir()
    outside_file = tmp_path / "external" / "pkg" / "__init__.py"
    outside_file.parent.mkdir(parents=True)
    outside_file.touch()

    # --- execute + verify ---
    assert amod_utils_matching.is_excluded_raw(outside_file, ["**/__init__.py"], root)
    # Non-matching filename should not match
    other_file = tmp_path / "external" / "pkg" / "module.py"
    other_file.touch()
    assert not amod_utils_matching.is_excluded_raw(other_file, ["**/__init__.py"], root)


def test_is_excluded_raw_double_star_outside_root_complex(tmp_path: Path) -> None:
    """**/ patterns with subdirectories should match files outside root.

    Example:
      path:     /tmp/external/pkg/subdir/__init__.py
      root:     /tmp/project/
      pattern:  ["**/subdir/__init__.py"]
      Result: True
      Explanation: Complex **/ patterns match against absolute path.
    """
    # --- setup ---
    root = tmp_path / "project"
    root.mkdir()
    outside_file = tmp_path / "external" / "pkg" / "subdir" / "__init__.py"
    outside_file.parent.mkdir(parents=True)
    outside_file.touch()

    # --- execute + verify ---
    assert amod_utils_matching.is_excluded_raw(
        outside_file, ["**/subdir/__init__.py"], root
    )
    # File in different subdirectory should not match
    other_file = tmp_path / "external" / "pkg" / "other" / "__init__.py"
    other_file.parent.mkdir(parents=True)
    other_file.touch()
    assert not amod_utils_matching.is_excluded_raw(
        other_file, ["**/subdir/__init__.py"], root
    )


def test_is_excluded_raw_double_star_inside_root(tmp_path: Path) -> None:
    """**/ patterns should still work for files inside root.

    Example:
      path:     /tmp/project/pkg/__init__.py
      root:     /tmp/project/
      pattern:  ["**/__init__.py"]
      Result: True
      Explanation: **/ patterns work for files both inside and outside root.
    """
    # --- setup ---
    root = tmp_path / "project"
    root.mkdir()
    inside_file = root / "pkg" / "__init__.py"
    inside_file.parent.mkdir(parents=True)
    inside_file.touch()

    # --- execute + verify ---
    assert amod_utils_matching.is_excluded_raw(inside_file, ["**/__init__.py"], root)
    # Nested file should also match
    nested_file = root / "pkg" / "subdir" / "__init__.py"
    nested_file.parent.mkdir(parents=True)
    nested_file.touch()
    assert amod_utils_matching.is_excluded_raw(nested_file, ["**/__init__.py"], root)


def test_is_excluded_raw_double_star_nested_pattern(tmp_path: Path) -> None:
    """Nested **/ patterns should work correctly.

    Example:
      path:     /tmp/project/pkg/subdir/file.py
      root:     /tmp/project/
      pattern:  ["**/subdir/**/*.py"]
      Result: True
      Explanation: Nested ** patterns should match recursively.
    """
    # --- setup ---
    root = tmp_path / "project"
    root.mkdir()
    nested_file = root / "pkg" / "subdir" / "deep" / "file.py"
    nested_file.parent.mkdir(parents=True)
    nested_file.touch()

    # --- execute + verify ---
    assert amod_utils_matching.is_excluded_raw(nested_file, ["**/subdir/**/*.py"], root)


def test_is_excluded_raw_double_star_outside_root_negative(tmp_path: Path) -> None:
    """**/ patterns should not match when pattern doesn't match.

    Example:
      path:     /tmp/external/pkg/module.py
      root:     /tmp/project/
      pattern:  ["**/__init__.py"]
      Result: False
      Explanation: **/ patterns only match when the pattern actually matches.
    """
    # --- setup ---
    root = tmp_path / "project"
    root.mkdir()
    outside_file = tmp_path / "external" / "pkg" / "module.py"
    outside_file.parent.mkdir(parents=True)
    outside_file.touch()

    # --- execute + verify ---
    assert not amod_utils_matching.is_excluded_raw(
        outside_file, ["**/__init__.py"], root
    )
    assert not amod_utils_matching.is_excluded_raw(
        outside_file, ["**/subdir/__init__.py"], root
    )


def test_is_excluded_raw_double_star_mixed_patterns(tmp_path: Path) -> None:
    """Mix of **/ and non-**/ patterns should work correctly.

    Example:
      path:     /tmp/external/pkg/__init__.py
      root:     /tmp/project/
      pattern:  ["*.py", "**/__init__.py", "ignore/*"]
      Result: True
      Explanation: **/ pattern should match even when other patterns don't.
    """
    # --- setup ---
    root = tmp_path / "project"
    root.mkdir()
    outside_file = tmp_path / "external" / "pkg" / "__init__.py"
    outside_file.parent.mkdir(parents=True)
    outside_file.touch()

    # --- execute + verify ---
    patterns = ["*.py", "**/__init__.py", "ignore/*"]
    assert amod_utils_matching.is_excluded_raw(outside_file, patterns, root)


def test_is_excluded_raw_relative_pattern_outside_root(tmp_path: Path) -> None:
    """Relative patterns with ../ should match files outside exclude root.

    Serger-specific behavior: Unlike rsync/ruff (which don't support '../'
    in exclude patterns), serger allows patterns with '../' to explicitly
    match files outside the exclude root.

    Rationale:
    - Config files can be in subdirectories (e.g., mode_verify/embedded_example/)
    - They need to exclude files elsewhere in the project (e.g., src/**/__init__.py)
    - Patterns with '../' explicitly signal intent to navigate outside the root
    - This is consistent with include patterns, which already support '../'
    - Enables more precise exclusions than '**/__init__.py' (which matches everywhere)

    When a pattern contains '../', it's resolved relative to the exclude root,
    then matched against the absolute file path.

    Example:
      path:     /tmp/src/pkg/__init__.py
      root:     /tmp/config_dir/
      pattern:  ["../src/**/__init__.py"]
      Result: True
      Explanation: Pattern resolves to /tmp/src/**/__init__.py, which matches
                   the file path /tmp/src/pkg/__init__.py.
    """
    # --- setup ---
    # Create structure: /tmp/.../config_dir/ and /tmp/.../src/pkg/
    # From config_dir, we need ../ to get to tmp_path, then src
    root = tmp_path / "config_dir"
    root.mkdir()
    outside_file = tmp_path / "src" / "pkg" / "__init__.py"
    outside_file.parent.mkdir(parents=True)
    outside_file.touch()

    # Pattern uses ../ to navigate from config_dir to src (one level up)
    pattern = "../src/**/__init__.py"

    # --- execute + verify ---
    # This should match because the pattern is designed to match files
    # outside the exclude root
    assert amod_utils_matching.is_excluded_raw(outside_file, [pattern], root)

    # Non-matching file should not be excluded
    other_file = tmp_path / "src" / "pkg" / "module.py"
    other_file.touch()
    assert not amod_utils_matching.is_excluded_raw(other_file, [pattern], root)


def test_is_excluded_raw_relative_pattern_outside_root_complex(tmp_path: Path) -> None:
    """Complex relative patterns with ../ should match files outside root.

    This test matches the bug report scenario where a config file in a
    subdirectory needs to exclude files outside the exclude root.

    Example:
      path:     /tmp/src/apathetic_logging/__init__.py
      root:     /tmp/mode_verify/embedded_example/
      pattern:  ["../../src/**/__init__.py"]
      Result: True
      Explanation: Pattern resolves from root (../../src/**/__init__.py) to
                   /tmp/src/**/__init__.py, which matches the file path
                   /tmp/src/apathetic_logging/__init__.py via glob matching.
    """
    # --- setup ---
    # Create structure matching bug report scenario
    root = tmp_path / "mode_verify" / "embedded_example"
    root.mkdir(parents=True)
    outside_file = tmp_path / "src" / "apathetic_logging" / "__init__.py"
    outside_file.parent.mkdir(parents=True)
    outside_file.touch()

    # Pattern from config_dir to src (two levels up)
    pattern = "../../src/**/__init__.py"

    # --- execute + verify ---
    assert amod_utils_matching.is_excluded_raw(outside_file, [pattern], root)

    # File in different location should not match
    other_file = tmp_path / "other" / "pkg" / "__init__.py"
    other_file.parent.mkdir(parents=True)
    other_file.touch()
    assert not amod_utils_matching.is_excluded_raw(other_file, [pattern], root)


def test_is_excluded_raw_relative_pattern_outside_root_specific_file(
    tmp_path: Path,
) -> None:
    """Relative patterns should match specific files outside root.

    Tests that patterns with '../' work even without '**/' globbing.
    Demonstrates that '../' patterns work for both glob and exact matches.

    Example:
      path:     /tmp/src/pkg/__init__.py
      root:     /tmp/config_dir/
      pattern:  ["../src/pkg/__init__.py"]
      Result: True
      Explanation: Pattern resolves to /tmp/src/pkg/__init__.py, which
                   exactly matches the file path.
    """
    # --- setup ---
    root = tmp_path / "config_dir"
    root.mkdir()
    outside_file = tmp_path / "src" / "pkg" / "__init__.py"
    outside_file.parent.mkdir(parents=True)
    outside_file.touch()

    # Specific file pattern (no **/) - one level up from config_dir
    pattern = "../src/pkg/__init__.py"

    # --- execute + verify ---
    assert amod_utils_matching.is_excluded_raw(outside_file, [pattern], root)
