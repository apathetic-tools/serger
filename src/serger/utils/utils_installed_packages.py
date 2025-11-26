# src/serger/utils/utils_installed_packages.py


import contextlib
import shutil
import site
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Sequence


def discover_installed_packages_roots() -> list[str]:
    """Discover installed packages root directories.

    Searches for site-packages directories in priority order:
    1. Poetry environment: `poetry env info --path` →
       `{path}/lib/python*/site-packages`
    2. Virtualenv/pip: Check `sys.path` for `site-packages` or
       `dist-packages` in virtualenv paths
    3. User site-packages: `~/.local/lib/python*/site-packages`
       (or platform-specific)
    4. System site-packages: Check `sys.path` for system
       `site-packages` or `dist-packages`

    Handles both `site-packages` and `dist-packages` (Debian/Ubuntu).

    Returns:
        List of absolute paths to site-packages directories in priority order.
        Returns empty list if nothing found (does not error).

    Note:
        Paths are deduplicated and returned in priority order.
    """
    discovered: list[str] = []
    seen: set[str] = set()

    # 1. Poetry environment (highest priority)
    poetry_paths = _discover_poetry_site_packages()
    for path in poetry_paths:
        if path not in seen:
            discovered.append(path)
            seen.add(path)

    # 2. Virtualenv/pip from sys.path
    venv_paths = _discover_venv_site_packages()
    for path in venv_paths:
        if path not in seen:
            discovered.append(path)
            seen.add(path)

    # 3. User site-packages
    user_paths = _discover_user_site_packages()
    for path in user_paths:
        if path not in seen:
            discovered.append(path)
            seen.add(path)

    # 4. System site-packages from sys.path
    system_paths = _discover_system_site_packages()
    for path in system_paths:
        if path not in seen:
            discovered.append(path)
            seen.add(path)

    return discovered


def _discover_poetry_site_packages() -> list[str]:
    """Discover Poetry environment site-packages directories.

    Returns:
        List of absolute paths to Poetry site-packages directories.
        Returns empty list if Poetry is not available or not in use.
    """
    poetry_cmd = shutil.which("poetry")
    if not poetry_cmd:
        return []

    try:
        result = subprocess.run(  # noqa: S603
            [poetry_cmd, "env", "info", "--path"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        venv_path = Path(result.stdout.strip())
        if not venv_path.exists():
            return []

        # Look for lib/python*/site-packages or lib/python*/dist-packages
        site_packages_paths: list[str] = []
        lib_dir = venv_path / "lib"
        if lib_dir.exists():
            for python_dir in lib_dir.iterdir():
                if python_dir.is_dir() and python_dir.name.startswith("python"):
                    for pkg_dir_name in ("site-packages", "dist-packages"):
                        pkg_dir = python_dir / pkg_dir_name
                        if pkg_dir.exists() and pkg_dir.is_dir():
                            site_packages_paths.append(str(pkg_dir.resolve()))

        return sorted(site_packages_paths)
    except Exception:  # noqa: BLE001
        # Poetry command failed or venv path invalid - return empty
        return []


def _discover_venv_site_packages() -> list[str]:
    """Discover virtualenv/pip site-packages from sys.path.

    Returns:
        List of absolute paths to virtualenv site-packages directories.
        Returns empty list if no virtualenv is detected.
    """
    discovered: list[str] = []
    seen: set[str] = set()

    # Check if we're in a virtualenv
    if not (
        hasattr(sys, "real_prefix")
        or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
    ):
        # Not in a virtualenv
        return []

    # Check sys.path for site-packages or dist-packages in virtualenv
    for path_str in sys.path:
        path = Path(path_str).resolve()
        if not path.exists():
            continue

        # Check if this path is a site-packages or dist-packages directory
        if path.name in ("site-packages", "dist-packages"):
            path_str_abs = str(path)
            if path_str_abs not in seen:
                discovered.append(path_str_abs)
                seen.add(path_str_abs)
        # Also check if path is inside a site-packages or dist-packages directory
        elif "site-packages" in path.parts or "dist-packages" in path.parts:
            # Find the site-packages or dist-packages parent
            for parent in path.parents:
                if parent.name in ("site-packages", "dist-packages"):
                    parent_str = str(parent.resolve())
                    if parent_str not in seen:
                        discovered.append(parent_str)
                        seen.add(parent_str)
                    break

    return sorted(discovered)


def _discover_user_site_packages() -> list[str]:
    """Discover user site-packages directories.

    Returns:
        List of absolute paths to user site-packages directories.
        Returns empty list if none found.
    """
    discovered: list[str] = []

    # Use site.getusersitepackages() if available (Python 3.11+)
    # For Python 3.10, we'll construct it manually
    try:
        user_site = site.getusersitepackages()
        if user_site:
            user_path = Path(user_site).resolve()
            if user_path.exists() and user_path.is_dir():
                discovered.append(str(user_path))
    except AttributeError:
        # Python 3.10 doesn't have getusersitepackages()
        # Construct it manually: ~/.local/lib/python*/site-packages
        home = Path.home()
        local_lib = home / ".local" / "lib"
        if local_lib.exists():
            for python_dir in local_lib.iterdir():
                if python_dir.is_dir() and python_dir.name.startswith("python"):
                    for pkg_dir_name in ("site-packages", "dist-packages"):
                        pkg_dir = python_dir / pkg_dir_name
                        if pkg_dir.exists() and pkg_dir.is_dir():
                            discovered.append(str(pkg_dir.resolve()))

    return sorted(discovered)


def _discover_system_site_packages() -> list[str]:
    """Discover system site-packages directories from sys.path.

    Returns:
        List of absolute paths to system site-packages directories.
        Returns empty list if none found.
    """
    discovered: list[str] = []
    seen: set[str] = set()

    # Get system site-packages
    system_sites: Sequence[str] = []
    with contextlib.suppress(AttributeError):
        # Python 3.10 doesn't have getsitepackages()
        # Fall back to checking sys.path for system paths
        system_sites = site.getsitepackages()

    # Add from getsitepackages() if available
    for site_path_str in system_sites:
        site_path = Path(site_path_str).resolve()
        if site_path.exists() and site_path.is_dir():
            site_str = str(site_path)
            if site_str not in seen:
                discovered.append(site_str)
                seen.add(site_str)

    # Also check sys.path for system site-packages/dist-packages
    # (not in virtualenv, not user site)
    for path_str in sys.path:
        path = Path(path_str).resolve()
        if not path.exists():
            continue

        # Skip if this looks like a virtualenv path
        if "site-packages" in path.parts or "dist-packages" in path.parts:
            # Check if it's a system path (not in home, not in venv)
            path_str_abs = str(path)
            if (
                path_str_abs not in seen
                and not path_str_abs.startswith(str(Path.home()))
                and not (
                    hasattr(sys, "real_prefix")
                    or (
                        hasattr(sys, "base_prefix")
                        and sys.base_prefix != sys.prefix
                        and path_str_abs.startswith(sys.prefix)
                    )
                )
            ):
                # Find the site-packages or dist-packages parent
                for parent in path.parents:
                    if parent.name in ("site-packages", "dist-packages"):
                        parent_str = str(parent.resolve())
                        if parent_str not in seen:
                            discovered.append(parent_str)
                            seen.add(parent_str)
                        break

    return sorted(discovered)
