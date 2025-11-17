# tests/0_independant/test_load_jsonc.py
"""Tests for package.utils (package and standalone versions)."""

from pathlib import Path

import pytest

import apathetic_utils.files as amod_utils_files


def test_load_jsonc_empty_file(tmp_path: Path) -> None:
    """Empty JSONC file should return {} or raise clean error."""
    # --- setup ---
    cfg = tmp_path / "empty.jsonc"
    cfg.write_text("")

    # --- execute ---
    result = amod_utils_files.load_jsonc(cfg)

    # --- verify ---
    assert result is None


def test_load_jsonc_only_comments(tmp_path: Path) -> None:
    """File with only comments should behave like empty."""
    # --- setup ---
    cfg = tmp_path / "comments.jsonc"
    cfg.write_text("// comment only\n/* another */")

    # --- execute ---
    result = amod_utils_files.load_jsonc(cfg)

    # --- verify ---
    assert result is None


def test_load_jsonc_trailing_comma_in_list(tmp_path: Path) -> None:
    """Trailing commas in top-level lists should be handled."""
    # --- setup ---
    cfg = tmp_path / "list.jsonc"
    cfg.write_text('[ "a", "b", ]')

    # --- execute ---
    result = amod_utils_files.load_jsonc(cfg)

    # --- verify ---
    assert result == ["a", "b"]


@pytest.mark.parametrize("ext", ["json", "jsonc"])
def test_load_jsonc_happy_path_with_comments_and_trailing_commas(
    tmp_path: Path,
    ext: str,
) -> None:
    """Happy path: JSONC loader removes comments and trailing commas."""
    # --- setup ---
    cfg = tmp_path / f"config.{ext}"
    cfg.write_text(
        """
        // comment
        {
          "foo": 1,
          "bar": [2, 3,],  // trailing comma
          "nested": { "x": 10, },
        }
        """
    )

    # --- execute ---
    result = amod_utils_files.load_jsonc(cfg)

    # --- verify ---
    assert result == {
        "foo": 1,
        "bar": [2, 3],
        "nested": {"x": 10},
    }


def test_load_jsonc_preserves_urls(tmp_path: Path) -> None:
    """Ensure JSONC loader does not strip // inside string literals (e.g. URLs)."""
    # --- setup ---
    cfg = tmp_path / "config.jsonc"
    cfg.write_text(
        """
        {
          "url": "https://example.com/resource",
          "nested": {
            "comment_like": "http://localhost:8080/api"
          }
        }
        """
    )

    # --- execute ---
    result = amod_utils_files.load_jsonc(cfg)

    # --- verify ---
    assert result == {
        "url": "https://example.com/resource",
        "nested": {"comment_like": "http://localhost:8080/api"},
    }


def test_load_jsonc_invalid_json(tmp_path: Path) -> None:
    """Invalid JSONC should raise ValueError with file context."""
    # --- setup ---
    cfg = tmp_path / "bad.jsonc"
    cfg.write_text("{ unquoted_key: 1 }")

    # --- execute and verify ---
    with pytest.raises(ValueError, match=r"Invalid JSONC syntax") as e:
        amod_utils_files.load_jsonc(cfg)

    assert "bad.jsonc" in str(e.value)


def test_load_jsonc_rejects_scalar_root(tmp_path: Path) -> None:
    # --- setup ---
    cfg = tmp_path / "scalar.jsonc"
    cfg.write_text('"hello"')

    # --- execute and verify ---
    with pytest.raises(ValueError, match="Invalid JSONC root type"):
        amod_utils_files.load_jsonc(cfg)


def test_load_jsonc_missing_file_raises(tmp_path: Path) -> None:
    """Missing JSONC file should raise FileNotFoundError."""
    # --- setup ---
    cfg = tmp_path / "does_not_exist.jsonc"

    # --- execute and verify ---
    with pytest.raises(FileNotFoundError):
        amod_utils_files.load_jsonc(cfg)


def test_load_jsonc_directory_path_raises(tmp_path: Path) -> None:
    """Passing a directory instead of a file should raise ValueError."""
    # --- setup ---
    cfg_dir = tmp_path / "config_dir"
    cfg_dir.mkdir()

    # --- execute and verify ---
    with pytest.raises(ValueError, match="Expected a file"):
        amod_utils_files.load_jsonc(cfg_dir)
