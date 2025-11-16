# tests/5_core/test_priv__extract_build_metadata.py
"""Tests for internal _extract_build_metadata helper function."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import serger.build as mod_build
from tests.utils.buildconfig import make_build_cfg


# Allow up to 2 seconds difference for timestamp comparisons
_MAX_TIMESTAMP_DIFF_SECONDS = 2


def test_extract_build_metadata_with_version() -> None:
    """Should extract version from _pyproject_version when available."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('version = "1.2.3"\n')

        build_cfg = make_build_cfg(tmp_path, include=[])
        # Simulate what happens during resolution when use_pyproject is enabled
        build_cfg["_pyproject_version"] = "1.2.3"

        version, commit, build_date = mod_build._extract_build_metadata(
            build_cfg, tmp_path, tmp_path
        )

        assert version == "1.2.3"
        assert isinstance(commit, str)
        assert isinstance(build_date, str)
        # Verify build_date format
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC", build_date)


def test_extract_build_metadata_without_version_uses_timestamp() -> None:
    """Should use timestamp as version when no version is found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create pyproject.toml without version
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("# no version here\n")

        build_cfg = make_build_cfg(tmp_path, include=[])

        # Capture timestamp before and after to ensure it's recent
        before = datetime.now(timezone.utc)
        version, commit, build_date = mod_build._extract_build_metadata(
            build_cfg, tmp_path, tmp_path
        )
        after = datetime.now(timezone.utc)

        # Version should be the build_date timestamp (not "unknown")
        assert version != "unknown"
        assert version == build_date
        # Verify it's a valid timestamp format
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC", version)

        # Verify the timestamp is recent (within 2 seconds)
        # Parse without timezone, then add it (DTZ007: format doesn't include %z)
        version_without_tz = version.replace(" UTC", "")
        parsed_version = datetime.strptime(version_without_tz, "%Y-%m-%d %H:%M:%S")  # noqa: DTZ007
        parsed_version = parsed_version.replace(tzinfo=timezone.utc)
        # Allow for small timing differences (parsed version has no microseconds)
        assert (before - parsed_version).total_seconds() <= _MAX_TIMESTAMP_DIFF_SECONDS
        assert (parsed_version - after).total_seconds() <= _MAX_TIMESTAMP_DIFF_SECONDS

        assert isinstance(commit, str)
        assert isinstance(build_date, str)


def test_extract_build_metadata_with_config_version() -> None:
    """Should prefer version from config over _pyproject_version."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create pyproject.toml with different version
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('version = "0.1.0"\n')

        build_cfg = make_build_cfg(tmp_path, include=[])
        # Add both version fields - version should take precedence
        build_cfg["version"] = "3.0.0"
        build_cfg["_pyproject_version"] = "2.0.0"

        version, _commit, _build_date = mod_build._extract_build_metadata(
            build_cfg, tmp_path
        )

        # Should use version from config, not _pyproject_version
        assert version == "3.0.0"
        assert version != "2.0.0"
        assert version != "0.1.0"


def test_extract_build_metadata_with_pyproject_version_fallback() -> None:
    """Should use _pyproject_version when version is not set."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create pyproject.toml with different version
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('version = "0.1.0"\n')

        build_cfg = make_build_cfg(tmp_path, include=[])
        # Only set _pyproject_version, not version
        build_cfg["_pyproject_version"] = "2.0.0"

        version, _commit, _build_date = mod_build._extract_build_metadata(
            build_cfg, tmp_path
        )

        # Should use _pyproject_version when version is not set
        assert version == "2.0.0"
        assert version != "0.1.0"


def test_extract_build_metadata_missing_pyproject() -> None:
    """Should use timestamp when pyproject.toml doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # No pyproject.toml file

        build_cfg = make_build_cfg(tmp_path, include=[])

        before = datetime.now(timezone.utc)
        version, _commit, build_date = mod_build._extract_build_metadata(
            build_cfg, tmp_path
        )
        after = datetime.now(timezone.utc)

        # Version should be timestamp, not "unknown"
        assert version != "unknown"
        assert version == build_date
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC", version)

        # Verify timestamp is recent
        # Parse without timezone, then add it (DTZ007: format doesn't include %z)
        version_without_tz = version.replace(" UTC", "")
        parsed_version = datetime.strptime(version_without_tz, "%Y-%m-%d %H:%M:%S")  # noqa: DTZ007
        parsed_version = parsed_version.replace(tzinfo=timezone.utc)
        # Allow for small timing differences (parsed version has no microseconds)
        assert (before - parsed_version).total_seconds() <= _MAX_TIMESTAMP_DIFF_SECONDS
        assert (parsed_version - after).total_seconds() <= _MAX_TIMESTAMP_DIFF_SECONDS
