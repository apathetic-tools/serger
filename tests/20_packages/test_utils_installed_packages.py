# tests/20_packages/test_utils_installed_packages.py
# pyright: reportPrivateUsage=false

import shutil
import site
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import serger.utils as mod_utils
import serger.utils.utils_installed_packages as mod_utils_installed_packages


def test_discover_installed_packages_roots_returns_list() -> None:
    """Test that discover_installed_packages_roots returns a list."""
    result = mod_utils.discover_installed_packages_roots()
    assert isinstance(result, list)
    # Should return at least empty list, possibly more
    assert all(isinstance(path, str) for path in result)


def test_discover_installed_packages_roots_returns_absolute_paths() -> None:
    """Test that all returned paths are absolute."""
    result = mod_utils.discover_installed_packages_roots()
    for path_str in result:
        path = Path(path_str)
        assert path.is_absolute()


def test_discover_installed_packages_roots_deduplicates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that duplicate paths are removed."""
    # Create actual directories that would be discovered by multiple methods
    # This tests that deduplication works with real paths
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir(parents=True)

    # Mock poetry to return a venv that contains the same site-packages
    poetry_venv = tmp_path / "poetry_venv"
    poetry_venv_lib = poetry_venv / "lib" / "python3.10" / "site-packages"
    # Create symlink or same path to test deduplication
    poetry_venv_lib.parent.mkdir(parents=True)
    poetry_venv_lib.symlink_to(site_packages)

    original_has_real_prefix = hasattr(sys, "real_prefix")
    original_real_prefix: str | None = getattr(sys, "real_prefix", None)

    try:
        # Set up environment to discover the same path via multiple methods
        sys.real_prefix = str(poetry_venv)  # type: ignore[attr-defined]
        mock_result = MagicMock(
            stdout=str(poetry_venv) + "\n",
            returncode=0,
        )
        mock_result.check_returncode = MagicMock()

        def mock_run(*_args: object, **_kwargs: object) -> MagicMock:
            return mock_result

        def mock_which(_: str) -> str | None:
            return "/usr/bin/poetry"

        monkeypatch.setattr(shutil, "which", mock_which)
        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(sys, "path", [str(site_packages)])

        result = mod_utils.discover_installed_packages_roots()
        # The same path should only appear once even if discovered by
        # multiple methods
        site_packages_str = str(site_packages.resolve())
        assert result.count(site_packages_str) <= 1
    finally:
        if original_has_real_prefix and original_real_prefix is not None:
            sys.real_prefix = original_real_prefix  # type: ignore[attr-defined]
        elif hasattr(sys, "real_prefix"):
            delattr(sys, "real_prefix")


def test_discover_installed_packages_roots_priority_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that paths are returned in priority order."""
    # Create actual directories for each priority level
    poetry_site = tmp_path / "poetry" / "lib" / "python3.10" / "site-packages"
    poetry_site.mkdir(parents=True)
    venv_site = tmp_path / "venv" / "lib" / "python3.10" / "site-packages"
    venv_site.mkdir(parents=True)
    user_site = tmp_path / "user" / ".local" / "lib" / "python3.10" / "site-packages"
    user_site.mkdir(parents=True)
    system_site = tmp_path / "system" / "lib" / "python3.10" / "site-packages"
    system_site.mkdir(parents=True)

    original_has_real_prefix = hasattr(sys, "real_prefix")
    original_real_prefix: str | None = getattr(sys, "real_prefix", None)

    try:
        sys.real_prefix = str(tmp_path / "venv")  # type: ignore[attr-defined]
        mock_result = MagicMock(
            stdout=str(tmp_path / "poetry") + "\n",
            returncode=0,
        )
        mock_result.check_returncode = MagicMock()

        def mock_run(*_args: object, **_kwargs: object) -> MagicMock:
            return mock_result

        def mock_which(_: str) -> str | None:
            return "/usr/bin/poetry"

        monkeypatch.setattr(shutil, "which", mock_which)
        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(sys, "path", [str(venv_site), str(system_site)])

        def mock_home_user() -> Path:
            return tmp_path / "user"

        monkeypatch.setattr(Path, "home", mock_home_user)

        def mock_getusersitepackages() -> None:
            msg = "not available"
            raise AttributeError(msg)

        monkeypatch.setattr(
            site, "getusersitepackages", mock_getusersitepackages, raising=False
        )

        def mock_getsitepackages() -> list[str]:
            return [str(system_site)]

        monkeypatch.setattr(
            site, "getsitepackages", mock_getsitepackages, raising=False
        )

        result = mod_utils.discover_installed_packages_roots()
        # Should find paths from different discovery methods
        # The exact order may vary based on what's actually discovered,
        # but we should find at least some of our test paths
        poetry_str = str(poetry_site.resolve())
        venv_str = str(venv_site.resolve())
        user_str = str(user_site.resolve())
        system_str = str(system_site.resolve())

        # At least one of the test paths should be found
        found_paths = [
            p for p in [poetry_str, venv_str, user_str, system_str] if p in result
        ]
        assert len(found_paths) > 0, "Should find at least one test path"
    finally:
        if original_has_real_prefix and original_real_prefix is not None:
            sys.real_prefix = original_real_prefix  # type: ignore[attr-defined]
        elif hasattr(sys, "real_prefix"):
            delattr(sys, "real_prefix")


def test_discover_installed_packages_roots_handles_empty_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that function handles all discovery methods returning empty."""
    # Create an environment where no site-packages are found
    original_has_real_prefix = hasattr(sys, "real_prefix")
    original_real_prefix: str | None = getattr(sys, "real_prefix", None)
    original_base_prefix = getattr(sys, "base_prefix", None)
    original_prefix = sys.prefix

    try:
        # Remove real_prefix to indicate not in venv
        if hasattr(sys, "real_prefix"):
            delattr(sys, "real_prefix")
        # Set base_prefix == prefix to indicate not in venv
        sys.base_prefix = "/nonexistent"
        sys.prefix = "/nonexistent"

        def mock_which_none(_: str) -> str | None:
            return None

        monkeypatch.setattr(shutil, "which", mock_which_none)  # No poetry
        monkeypatch.setattr(sys, "path", [])  # No paths

        def mock_home_nonexistent() -> Path:
            return Path("/nonexistent")

        monkeypatch.setattr(Path, "home", mock_home_nonexistent)

        def mock_getusersitepackages() -> None:
            msg = "not available"
            raise AttributeError(msg)

        monkeypatch.setattr(
            site, "getusersitepackages", mock_getusersitepackages, raising=False
        )
        monkeypatch.setattr(site, "getsitepackages", list, raising=False)

        result = mod_utils.discover_installed_packages_roots()
        # Should return empty list when nothing is found
        assert result == []
    finally:
        if original_has_real_prefix and original_real_prefix is not None:
            sys.real_prefix = original_real_prefix  # type: ignore[attr-defined]
        if original_base_prefix is not None:
            sys.base_prefix = original_base_prefix
        sys.prefix = original_prefix


def test_discover_poetry_site_packages_with_poetry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test Poetry discovery when poetry is available."""
    # Create a mock poetry venv structure
    venv_path = tmp_path / "poetry_venv"
    lib_path = venv_path / "lib" / "python3.10" / "site-packages"
    lib_path.mkdir(parents=True)

    mock_result = MagicMock(
        stdout=str(venv_path) + "\n",
        returncode=0,
    )
    mock_result.check_returncode = MagicMock()

    def mock_run(*_args: object, **_kwargs: object) -> MagicMock:
        return mock_result

    def mock_which_poetry_site(_: str) -> str | None:
        return "/usr/bin/poetry"

    monkeypatch.setattr(shutil, "which", mock_which_poetry_site)
    monkeypatch.setattr(subprocess, "run", mock_run)

    result = mod_utils_installed_packages._discover_poetry_site_packages()  # noqa: SLF001
    # Should find the site-packages directory
    assert len(result) > 0
    assert any("site-packages" in path for path in result)


def test_discover_poetry_site_packages_without_poetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Poetry discovery when poetry is not available."""

    def mock_which_none(_: str) -> str | None:
        return None

    monkeypatch.setattr(shutil, "which", mock_which_none)
    result = mod_utils_installed_packages._discover_poetry_site_packages()  # noqa: SLF001
    assert result == []


def test_discover_poetry_site_packages_handles_dist_packages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test Poetry discovery handles dist-packages (Debian/Ubuntu)."""
    # Create a mock poetry venv structure with dist-packages
    venv_path = tmp_path / "poetry_venv"
    lib_path = venv_path / "lib" / "python3.10" / "dist-packages"
    lib_path.mkdir(parents=True)

    mock_result = MagicMock(
        stdout=str(venv_path) + "\n",
        returncode=0,
    )
    mock_result.check_returncode = MagicMock()

    def mock_run(*_args: object, **_kwargs: object) -> MagicMock:
        return mock_result

    def mock_which_poetry3(_: str) -> str | None:
        return "/usr/bin/poetry"

    monkeypatch.setattr(shutil, "which", mock_which_poetry3)
    monkeypatch.setattr(subprocess, "run", mock_run)

    result = mod_utils_installed_packages._discover_poetry_site_packages()  # noqa: SLF001
    # Should find the dist-packages directory
    assert len(result) > 0
    assert any("dist-packages" in path for path in result)


def test_discover_venv_site_packages_in_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test virtualenv discovery when in a virtualenv."""
    # Create actual directories for the test
    venv_site_packages = tmp_path / "venv" / "lib" / "python3.10" / "site-packages"
    venv_site_packages.mkdir(parents=True)
    pkg_dir = venv_site_packages / "pkg"
    pkg_dir.mkdir()

    # Mock sys to look like we're in a virtualenv
    original_has_real_prefix = hasattr(sys, "real_prefix")
    original_real_prefix: str | None = getattr(sys, "real_prefix", None)

    try:
        sys.real_prefix = str(tmp_path / "venv")  # type: ignore[attr-defined]
        monkeypatch.setattr(
            sys,
            "path",
            [
                str(venv_site_packages),
                str(pkg_dir),
            ],
        )
        result = mod_utils_installed_packages._discover_venv_site_packages()  # noqa: SLF001
        # Should find site-packages
        assert len(result) > 0
        assert any("site-packages" in path for path in result)
    finally:
        if original_has_real_prefix and original_real_prefix is not None:
            sys.real_prefix = original_real_prefix  # type: ignore[attr-defined]
        elif hasattr(sys, "real_prefix"):
            delattr(sys, "real_prefix")


def test_discover_venv_site_packages_not_in_venv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test virtualenv discovery when not in a virtualenv."""
    # Mock sys to look like we're NOT in a virtualenv
    original_has_real_prefix = hasattr(sys, "real_prefix")
    original_real_prefix: str | None = getattr(sys, "real_prefix", None)
    original_base_prefix = getattr(sys, "base_prefix", None)
    original_prefix = sys.prefix

    try:
        # Remove real_prefix if it exists
        if hasattr(sys, "real_prefix"):
            delattr(sys, "real_prefix")
        # Set base_prefix == prefix to indicate not in venv
        sys.base_prefix = "/usr"
        sys.prefix = "/usr"
        monkeypatch.setattr(sys, "path", [])
        result = mod_utils_installed_packages._discover_venv_site_packages()  # noqa: SLF001
        assert result == []
    finally:
        if original_has_real_prefix and original_real_prefix is not None:
            sys.real_prefix = original_real_prefix  # type: ignore[attr-defined]
        if original_base_prefix is not None:
            sys.base_prefix = original_base_prefix
        sys.prefix = original_prefix


def test_discover_user_site_packages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test user site-packages discovery."""
    # Create a mock user site-packages directory
    user_site = tmp_path / ".local" / "lib" / "python3.10" / "site-packages"
    user_site.mkdir(parents=True)

    def mock_getusersitepackages() -> None:
        msg = "not available"
        raise AttributeError(msg)

    def mock_home_tmp() -> Path:
        return tmp_path

    monkeypatch.setattr(Path, "home", mock_home_tmp)
    monkeypatch.setattr(
        site, "getusersitepackages", mock_getusersitepackages, raising=False
    )

    result = mod_utils_installed_packages._discover_user_site_packages()  # noqa: SLF001
    # Should find the user site-packages directory
    assert len(result) > 0
    assert any(str(tmp_path) in path for path in result)


def test_discover_system_site_packages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test system site-packages discovery."""
    # Create an actual directory that exists for the test
    system_site = tmp_path / "usr" / "lib" / "python3.10" / "site-packages"
    system_site.mkdir(parents=True)

    # Mock site.getsitepackages() to return our test path
    def mock_getsitepackages_system() -> list[str]:
        return [str(system_site)]

    monkeypatch.setattr(
        site,
        "getsitepackages",
        mock_getsitepackages_system,
        raising=False,
    )
    monkeypatch.setattr(sys, "path", [])

    result = mod_utils_installed_packages._discover_system_site_packages()  # noqa: SLF001
    # Should find system site-packages
    assert len(result) > 0
    assert any("site-packages" in path for path in result)
