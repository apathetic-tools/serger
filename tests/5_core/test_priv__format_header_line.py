# tests/5_core/test_priv__format_header_line.py
"""Tests for internal _format_header_line helper function."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

import serger.stitch as mod_stitch


class TestFormatHeaderLine:
    """Test header line formatting with display_name and description."""

    def test_both_provided(self) -> None:
        """Should format header with both name and description."""
        result = mod_stitch._format_header_line(
            display_name="MyProject",
            description="A test project",
            package_name="fallback",
        )
        assert result == "# MyProject — A test project"

    def test_only_display_name(self) -> None:
        """Should format header with only display name."""
        result = mod_stitch._format_header_line(
            display_name="MyProject",
            description="",
            package_name="fallback",
        )
        assert result == "# MyProject"

    def test_only_description(self) -> None:
        """Should format header with package name and description."""
        result = mod_stitch._format_header_line(
            display_name="",
            description="A test project",
            package_name="fallback",
        )
        assert result == "# fallback — A test project"

    def test_neither_provided(self) -> None:
        """Should use package name when neither field provided."""
        result = mod_stitch._format_header_line(
            display_name="",
            description="",
            package_name="fallback",
        )
        assert result == "# fallback"

    def test_whitespace_trimmed(self) -> None:
        """Should trim leading/trailing whitespace."""
        result = mod_stitch._format_header_line(
            display_name="  MyProject  ",
            description="  A test project  ",
            package_name="fallback",
        )
        assert result == "# MyProject — A test project"
