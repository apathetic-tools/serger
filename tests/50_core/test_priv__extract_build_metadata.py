# tests/50_core/test_priv__extract_build_metadata.py
"""Tests for internal _extract_build_metadata helper function."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

import re
from datetime import datetime, timezone
from pathlib import Path

import serger.build as mod_build
import serger.constants as mod_constants
from tests.utils.buildconfig import make_build_cfg


# Allow up to 2 seconds difference for timestamp comparisons
_MAX_TIMESTAMP_DIFF_SECONDS = 2


def test_extract_build_metadata_with_version() -> None:
    """Should extract version from resolved config when available."""
    tmp_path = Path.cwd()

    build_cfg = make_build_cfg(tmp_path, version="1.2.3")

    version, commit, build_date = mod_build._extract_build_metadata(
        build_cfg=build_cfg, project_root=tmp_path, git_root=tmp_path
    )

    assert version == "1.2.3"
    assert isinstance(commit, str)
    assert isinstance(build_date, str)
    # Verify build_date format
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC", build_date)


def test_extract_build_metadata_without_version_uses_timestamp(
    tmp_path: Path,
) -> None:
    """Should use timestamp as version when no version is found."""
    build_cfg = make_build_cfg(tmp_path)

    # Capture timestamp before and after to ensure it's recent
    before = datetime.now(timezone.utc)
    version, commit, build_date = mod_build._extract_build_metadata(
        build_cfg=build_cfg, project_root=tmp_path, git_root=tmp_path
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
    """Should use version from resolved config (resolved during config resolution)."""
    tmp_path = Path.cwd()

    build_cfg = make_build_cfg(tmp_path, version="3.0.0")

    version, _commit, _build_date = mod_build._extract_build_metadata(
        build_cfg=build_cfg, project_root=tmp_path
    )

    # Should use version from resolved config
    assert version == "3.0.0"


def test_extract_build_metadata_with_pyproject_version_fallback() -> None:
    """Should use version from resolved config (from pyproject if enabled)."""
    tmp_path = Path.cwd()

    build_cfg = make_build_cfg(tmp_path, version="2.0.0")

    version, _commit, _build_date = mod_build._extract_build_metadata(
        build_cfg=build_cfg, project_root=tmp_path
    )

    # Should use version from resolved config
    assert version == "2.0.0"


def test_extract_build_metadata_missing_pyproject(tmp_path: Path) -> None:
    """Should use timestamp when pyproject.toml doesn't exist."""
    # No pyproject.toml file

    build_cfg = make_build_cfg(tmp_path)

    before = datetime.now(timezone.utc)
    version, _commit, build_date = mod_build._extract_build_metadata(
        build_cfg=build_cfg, project_root=tmp_path
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


def test_extract_build_metadata_disable_timestamp_true() -> None:
    """Should use placeholder when disable_timestamp=True."""
    tmp_path = Path.cwd()

    build_cfg = make_build_cfg(tmp_path)

    version, commit, build_date = mod_build._extract_build_metadata(
        build_cfg=build_cfg,
        project_root=tmp_path,
        git_root=tmp_path,
        disable_timestamp=True,
    )

    # Should use placeholder for build_date
    assert build_date == mod_constants.BUILD_TIMESTAMP_PLACEHOLDER
    assert isinstance(commit, str)
    # Version should be placeholder if not set
    assert version == mod_constants.BUILD_TIMESTAMP_PLACEHOLDER


def test_extract_build_metadata_disable_timestamp_true_with_version() -> None:
    """Should use placeholder for build_date but keep version."""
    tmp_path = Path.cwd()

    build_cfg = make_build_cfg(tmp_path, version="1.2.3")

    version, commit, build_date = mod_build._extract_build_metadata(
        build_cfg=build_cfg,
        project_root=tmp_path,
        git_root=tmp_path,
        disable_timestamp=True,
    )

    # Should use placeholder for build_date
    assert build_date == mod_constants.BUILD_TIMESTAMP_PLACEHOLDER
    # Version should be preserved from config
    assert version == "1.2.3"
    assert isinstance(commit, str)


def test_extract_build_metadata_disable_timestamp_false(
    tmp_path: Path,
) -> None:
    """Should use real timestamp when disable_timestamp=False (default behavior)."""
    build_cfg = make_build_cfg(tmp_path)

    before = datetime.now(timezone.utc)
    version, commit, build_date = mod_build._extract_build_metadata(
        build_cfg=build_cfg,
        project_root=tmp_path,
        git_root=tmp_path,
        disable_timestamp=False,
    )
    after = datetime.now(timezone.utc)

    # Should use real timestamp
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC", build_date)
    assert version == build_date
    assert isinstance(commit, str)

    # Verify timestamp is recent
    version_without_tz = version.replace(" UTC", "")
    parsed_version = datetime.strptime(version_without_tz, "%Y-%m-%d %H:%M:%S")  # noqa: DTZ007
    parsed_version = parsed_version.replace(tzinfo=timezone.utc)
    assert (before - parsed_version).total_seconds() <= _MAX_TIMESTAMP_DIFF_SECONDS
    assert (parsed_version - after).total_seconds() <= _MAX_TIMESTAMP_DIFF_SECONDS
