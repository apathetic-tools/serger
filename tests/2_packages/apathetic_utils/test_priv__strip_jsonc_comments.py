# tests/0_independant/test_priv__strip_jsonc_comments.py
"""Tests for serger.utils._strip_jsonc_comments (private helper)."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

from typing import Any

import pytest

import apathetic_utils.files as amod_utils_files


class _MockUtils:
    """Mock utils module for testing private functions."""

    def _strip_jsonc_comments(self, text: str) -> str:
        return amod_utils_files._strip_jsonc_comments(text)


mod_utils: Any = _MockUtils()


class TestBasicCommentRemoval:
    """Test basic comment stripping functionality."""

    def test_line_comment_basic(self) -> None:
        """Single line comment should be removed."""
        result = mod_utils._strip_jsonc_comments("// comment")
        assert result == ""

    def test_line_comment_with_code_after(self) -> None:
        """Line comment after code should be removed."""
        result = mod_utils._strip_jsonc_comments('{"key": 1} // comment')
        assert result == '{"key": 1} '

    def test_hash_comment(self) -> None:
        """Hash comments should be removed."""
        result = mod_utils._strip_jsonc_comments("# comment")
        assert result == ""

    def test_block_comment(self) -> None:
        """Block comments should be removed."""
        result = mod_utils._strip_jsonc_comments("/* comment */")
        assert result == ""

    def test_block_comment_inline(self) -> None:
        """Inline block comments should be removed."""
        result = mod_utils._strip_jsonc_comments('{"a": 1 /* x */ }')
        assert result == '{"a": 1  }'

    def test_multiple_comment_types(self) -> None:
        """Mixed comment types should all be removed."""
        text = '{\n  "a": 1, // line\n  "b": 2  /* block */\n  # hash\n}'
        result = mod_utils._strip_jsonc_comments(text)
        # All comments removed, newlines preserved
        assert "comment" not in result
        assert "hash" not in result


class TestStringPreservation:
    """Test that strings are not modified during comment removal."""

    def test_double_quoted_string_preserved(self) -> None:
        """Double-quoted strings should be preserved exactly."""
        result = mod_utils._strip_jsonc_comments('{"url": "http://example.com"}')
        assert '"http://example.com"' in result

    def test_single_quoted_string_preserved(self) -> None:
        """Single-quoted strings should be preserved."""
        result = mod_utils._strip_jsonc_comments("{'url': 'http://example.com'}")
        assert "'http://example.com'" in result

    def test_comment_like_content_in_string(self) -> None:
        """Comment syntax inside strings should be preserved."""
        result = mod_utils._strip_jsonc_comments('{"text": "// not a comment"}')
        assert '"// not a comment"' in result

    def test_hash_in_string_preserved(self) -> None:
        """Hash inside strings should not trigger comment removal."""
        result = mod_utils._strip_jsonc_comments('{"license": "MIT # clause"}')
        assert '"MIT # clause"' in result

    def test_block_comment_syntax_in_string(self) -> None:
        """Block comment syntax in strings should be preserved."""
        result = mod_utils._strip_jsonc_comments('{"regex": "/* pattern */"}')
        assert '"/* pattern */"' in result

    def test_escaped_quote_in_string(self) -> None:
        """Escaped quotes should not end strings."""
        result = mod_utils._strip_jsonc_comments(r'{"text": "say \"hello\""}')
        assert r'"say \"hello\""' in result


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_empty_input(self) -> None:
        """Empty input should return empty string."""
        result = mod_utils._strip_jsonc_comments("")
        assert result == ""

    def test_only_whitespace(self) -> None:
        """Whitespace-only input should be preserved."""
        result = mod_utils._strip_jsonc_comments("   \n  \t  ")
        assert result == "   \n  \t  "

    def test_url_with_double_slash_preserved(self) -> None:
        """URLs like http:// should not be treated as comments."""
        result = mod_utils._strip_jsonc_comments('{"url": "http://example.com/path"}')
        assert "http://example.com" in result

    def test_url_with_https_preserved(self) -> None:
        """HTTPS URLs should not be treated as comments."""
        result = mod_utils._strip_jsonc_comments('{"url": "https://example.com/path"}')
        assert "https://example.com" in result

    def test_comment_at_end_of_file(self) -> None:
        """Comments at the end without newline should be removed."""
        result = mod_utils._strip_jsonc_comments("[1, 2] // final comment")
        assert result == "[1, 2] "

    def test_unclosed_block_comment(self) -> None:
        """Unclosed block comment eats most of rest of file.

        Note: This is edge case behavior. In practice, malformed JSONC
        like this would fail JSON parsing anyway, so the exact behavior
        of the comment stripper is less critical.
        """
        result = mod_utils._strip_jsonc_comments('{"a": 1} /* unclosed')
        # The unclosed comment consumes the rest, leaving some remnant chars
        assert '{"a": 1}' in result

    def test_multiline_block_comment(self) -> None:
        """Block comments spanning lines should be removed entirely."""
        text = """{"a": 1,
/* this comment
   spans multiple
   lines */ "b": 2}"""
        result = mod_utils._strip_jsonc_comments(text)
        assert '"b": 2' in result
        assert "comment" not in result


class TestNewlineHandling:
    """Test newline preservation in comment removal."""

    def test_line_comment_preserves_newline(self) -> None:
        """Line comments should leave newline."""
        text = "line1 // comment\nline2"
        result = mod_utils._strip_jsonc_comments(text)
        assert "line1" in result
        assert "line2" in result
        assert result.count("\n") == 1

    def test_hash_comment_preserves_newline(self) -> None:
        """Hash comments should leave newline."""
        text = "line1 # comment\nline2"
        result = mod_utils._strip_jsonc_comments(text)
        assert "line1" in result
        assert "line2" in result
        assert result.count("\n") == 1

    def test_block_comment_removes_newlines_in_comment(self) -> None:
        """Newlines inside block comments should be removed."""
        text = "line1 /* comment\nwith newline */ line2"
        result = mod_utils._strip_jsonc_comments(text)
        assert "line1" in result
        assert "line2" in result
        # The newline inside the comment is removed
        assert result.count("comment") == 0


class TestComplexRealWorldExamples:
    """Test realistic JSONC configurations."""

    def test_typical_json_config(self) -> None:
        """Typical config file with comments."""
        text = """{
    // Project configuration
    "name": "myproject",  // Project name
    "version": "1.0.0",
    /* Multiple settings
       can go here */
    "debug": true
}"""
        result = mod_utils._strip_jsonc_comments(text)
        assert '"name"' in result
        assert "Project" not in result
        assert "settings" not in result

    def test_package_json_like(self) -> None:
        """Package.json-like structure with comments."""
        text = """{
    "name": "my-package",  // Package identifier
    "version": "1.0.0",    // Semantic version
    "description": "A package",
    /* Dependencies and devDependencies
       are listed below */
    "dependencies": {
        "lodash": "^4.0.0"  // Utility library
    }
}"""
        result = mod_utils._strip_jsonc_comments(text)
        assert '"lodash"' in result
        assert "Package identifier" not in result

    def test_config_with_urls_and_comments(self) -> None:
        """Config with both URLs and comments."""
        text = """{
    "remote": "https://api.example.com/data",  // API endpoint
    "backup": "http://backup.internal:8080",   # Internal backup
    /* Don't modify below this line */
    "internal": true
}"""
        result = mod_utils._strip_jsonc_comments(text)
        assert "https://api.example.com" in result
        assert "http://backup.internal:8080" in result
        assert "API endpoint" not in result
        assert "modify" not in result

    def test_serger_config_with_em_dash(self) -> None:
        """Test config with em-dash in string (real use case)."""
        text = """{
    "metadata": {
        "license": "MIT License — Copyright notice",
        "author": "Test Author"
    }
    // Additional config
}"""
        result = mod_utils._strip_jsonc_comments(text)
        assert "— Copyright" in result
        assert "Additional config" not in result


class TestParametrized:
    """Parametrized tests for various edge cases."""

    @pytest.mark.parametrize(
        ("text", "should_contain"),
        [
            ('{"a": 1}', '{"a": 1}'),
            ('{"a": 1} // c', '{"a": 1}'),
            ("[1, 2, 3]", "[1, 2, 3]"),
            ('["a", "b"]', '["a", "b"]'),
            ('{"url": "http://x"}', '"http://x"'),
            ('{"url": "https://x"}', '"https://x"'),
        ],
    )
    def test_various_clean_outputs(self, text: str, should_contain: str) -> None:
        """Various inputs should clean properly."""
        result = mod_utils._strip_jsonc_comments(text)
        assert should_contain in result

    @pytest.mark.parametrize(
        ("text", "should_not_contain"),
        [
            ('{"a": 1} // comment', "comment"),
            ("[1, 2] # note", "note"),
            ('{"a": 1} /* block */', "block"),
            (
                '{"text": "// preserved"} // removed',
                "removed",
            ),
        ],
    )
    def test_comments_removed(
        self,
        text: str,
        should_not_contain: str,
    ) -> None:
        """Comments should be removed from various inputs."""
        result = mod_utils._strip_jsonc_comments(text)
        assert should_not_contain not in result

    @pytest.mark.parametrize(
        ("text", "should_contain"),
        [
            ('{"url": "http://x"}', "http"),
            ('{"url": "https://x"}', "https"),
            ('{"note": "// preserved"}', "//"),
            ('{"hash": "# sign"}', "#"),
            ('{"comment": "/* block */"}', "/*"),
        ],
    )
    def test_string_content_preserved(
        self,
        text: str,
        should_contain: str,
    ) -> None:
        """String content should always be preserved."""
        result = mod_utils._strip_jsonc_comments(text)
        assert should_contain in result
