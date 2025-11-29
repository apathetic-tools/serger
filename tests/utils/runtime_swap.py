# tests/utils/runtime_swap.py
"""Shared test setup for project.

Each pytest run now targets a single runtime mode:
- Normal mode (default): uses src/serger
- standalone mode: uses dist/serger.py when RUNTIME_MODE=singlefile
- zipapp mode: uses dist/serger.pyz when RUNTIME_MODE=zipapp

Switch mode with: RUNTIME_MODE=singlefile pytest or RUNTIME_MODE=zipapp pytest
"""

import importlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import apathetic_utils as mod_utils
import pytest
from apathetic_logging import makeSafeTrace

import serger.meta as mod_meta
from tests.utils import PROJ_ROOT


if TYPE_CHECKING:
    from types import ModuleType


# --- helpers --------------------------------------------------------------------

TEST_TRACE = makeSafeTrace("🧬")


def _mode() -> str:
    return os.getenv("RUNTIME_MODE", "installed")


# ------------------------------------------------------------
# ⚙️ Auto-build helper for standalone script
# ------------------------------------------------------------
def ensure_standalone_script_up_to_date(root: Path) -> Path:
    """Rebuild `dist/serger.py` if missing or outdated."""
    bin_path = root / "dist" / f"{mod_meta.PROGRAM_SCRIPT}.py"
    src_dir = root / "src" / f"{mod_meta.PROGRAM_PACKAGE}"

    # If the output file doesn't exist or is older than any source file → rebuild.
    needs_rebuild = not bin_path.exists()
    if not needs_rebuild:
        bin_mtime_ns = bin_path.stat().st_mtime_ns
        for src_file in src_dir.rglob("*.py"):
            if src_file.stat().st_mtime_ns > bin_mtime_ns:
                needs_rebuild = True
                break

    # Debug: log whether rebuild is needed
    ci_env = os.getenv("CI")
    github_ref = os.getenv("GITHUB_REF")
    git_tag = os.getenv("GIT_TAG")
    TEST_TRACE(
        "ensure_standalone_script_up_to_date",
        f"needs_rebuild={needs_rebuild}, bin_path={bin_path}, "
        f"CI={ci_env}, GITHUB_REF={github_ref}, GIT_TAG={git_tag}",
    )
    if ci_env:
        msg = (
            f"  ensure_standalone_script_up_to_date: "
            f"needs_rebuild={needs_rebuild}, bin_path={bin_path}, "
            f"CI={ci_env}, GITHUB_REF={github_ref}, GIT_TAG={git_tag}"
        )
        print(msg)  # Also print to stdout for visibility

    if needs_rebuild:
        print("⚙️  Rebuilding standalone bundle (python -m serger)...")
        # Log CI environment for debugging
        ci_env = os.getenv("CI")
        github_ref = os.getenv("GITHUB_REF")
        git_tag = os.getenv("GIT_TAG")
        env_copy = os.environ.copy()
        TEST_TRACE(
            "ensure_standalone_script_up_to_date REBUILDING",
            f"CI={ci_env}, GITHUB_REF={github_ref}, GIT_TAG={git_tag}, "
            f"sys.executable={sys.executable}, cwd={root}",
        )
        print(f"  CI env vars: CI={ci_env}, GITHUB_REF={github_ref}, GIT_TAG={git_tag}")
        print(f"  Running: {sys.executable} -m serger in {root}")
        print(f"  Environment keys: {sorted(env_copy.keys())}")
        subprocess.run(  # noqa: S603
            [sys.executable, "-m", "serger"],
            check=True,
            cwd=root,
            env=env_copy,
        )
        TEST_TRACE(
            "ensure_standalone_script_up_to_date Rebuild complete",
            f"bin_path.exists()={bin_path.exists()}",
        )
        # force mtime update in case contents identical
        bin_path.touch()
        assert bin_path.exists(), "❌ Failed to generate standalone script."

    return bin_path


def ensure_zipapp_up_to_date(root: Path) -> Path:
    """Rebuild `dist/serger.pyz` if missing or outdated."""
    zipapp_path = root / "dist" / f"{mod_meta.PROGRAM_SCRIPT}.pyz"
    src_dir = root / "src" / f"{mod_meta.PROGRAM_PACKAGE}"

    # If the output file doesn't exist or is older than any source file → rebuild.
    needs_rebuild = not zipapp_path.exists()
    if not needs_rebuild:
        zipapp_mtime_ns = zipapp_path.stat().st_mtime_ns
        for src_file in src_dir.rglob("*.py"):
            if src_file.stat().st_mtime_ns > zipapp_mtime_ns:
                needs_rebuild = True
                break

    if needs_rebuild:
        shiv_cmd = mod_utils.find_shiv()
        print("⚙️  Rebuilding zipapp (shiv)...")
        subprocess.run(  # noqa: S603
            [
                shiv_cmd,
                "-c",
                mod_meta.PROGRAM_PACKAGE,
                "-o",
                str(zipapp_path),
                ".",
            ],
            cwd=root,
            check=True,
        )
        # force mtime update in case contents identical
        zipapp_path.touch()
        assert zipapp_path.exists(), "❌ Failed to generate zipapp."

    return zipapp_path


# --- runtime_swap() ------------------------------------------------------------------


def runtime_swap() -> bool:
    """Pre-import hook — runs before any tests or plugins are imported.

    Swaps in the appropriate runtime module based on RUNTIME_MODE:
    - installed (default): uses src/serger (no swap needed)
    - singlefile: uses dist/serger.py (serger-built single file)
    - zipapp: uses dist/serger.pyz (shiv-built zipapp)

    This ensures all test imports work transparently regardless of runtime mode.
    """
    mode = _mode()
    if mode == "installed":
        return False  # Normal installed mode; nothing to do.

    # Nuke any already-imported modules from src/ to avoid stale refs.
    # Dynamically detect all packages under src/ instead of hardcoding names.
    src_dir = PROJ_ROOT / "src"
    packages_to_nuke = mod_utils.find_all_packages_under_path(src_dir)

    for name in list(sys.modules):
        # Check if module name matches any detected package or is a submodule
        for pkg_name in packages_to_nuke:
            if name == pkg_name or name.startswith(f"{pkg_name}."):
                del sys.modules[name]
                break

    if mode == "singlefile":
        return _load_singlefile_mode()
    if mode == "zipapp":
        return _load_zipapp_mode()

    # Unknown mode
    xmsg = f"Unknown RUNTIME_MODE={mode!r}. Valid modes: installed, singlefile, zipapp"
    raise pytest.UsageError(xmsg)


def _load_singlefile_mode() -> bool:
    """Load standalone single-file script mode."""
    bin_path = ensure_standalone_script_up_to_date(PROJ_ROOT)

    if not bin_path.exists():
        xmsg = (
            f"RUNTIME_MODE=singlefile but standalone script not found at {bin_path}.\n"
            f"Hint: run the bundler (e.g. `python -m serger` "
            f"or `poetry run poe build:script`)."
        )
        raise pytest.UsageError(xmsg)

    # Load standalone script as the serger package.
    spec = importlib.util.spec_from_file_location(mod_meta.PROGRAM_PACKAGE, bin_path)
    if not spec or not spec.loader:
        xmsg = f"Could not create import spec for {bin_path}"
        raise pytest.UsageError(xmsg)

    try:
        mod: ModuleType = importlib.util.module_from_spec(spec)
        sys.modules[mod_meta.PROGRAM_PACKAGE] = mod
        spec.loader.exec_module(mod)
        TEST_TRACE(f"Loaded standalone module from {bin_path}")
    except Exception as e:
        # Fail fast with context; this is a config/runtime problem.
        error_name = type(e).__name__
        xmsg = (
            f"Failed to import standalone module from {bin_path}.\n"
            f"Original error: {error_name}: {e}\n"
            f"Tip: rebuild the bundle and re-run."
        )
        raise pytest.UsageError(xmsg) from e

    TEST_TRACE(f"✅ Loaded standalone runtime early from {bin_path}")
    return True


def _load_zipapp_mode() -> bool:
    """Load zipapp mode."""
    zipapp_path = ensure_zipapp_up_to_date(PROJ_ROOT)

    if not zipapp_path.exists():
        xmsg = (
            f"RUNTIME_MODE=zipapp but zipapp not found at {zipapp_path}.\n"
            f"Hint: run `poetry run poe build:zipapp`."
        )
        raise pytest.UsageError(xmsg)

    # Add zipapp to sys.path so Python can import from it
    zipapp_str = str(zipapp_path)
    if zipapp_str not in sys.path:
        sys.path.insert(0, zipapp_str)

    try:
        # Import the module normally - Python's zipapp support handles this
        importlib.import_module(mod_meta.PROGRAM_PACKAGE)
        TEST_TRACE(f"Loaded zipapp module from {zipapp_path}")
    except Exception as e:
        # Fail fast with context; this is a config/runtime problem.
        error_name = type(e).__name__
        xmsg = (
            f"Failed to import zipapp module from {zipapp_path}.\n"
            f"Original error: {error_name}: {e}\n"
            f"Tip: rebuild the zipapp and re-run."
        )
        raise pytest.UsageError(xmsg) from e

    TEST_TRACE(f"✅ Loaded zipapp runtime early from {zipapp_path}")
    return True
