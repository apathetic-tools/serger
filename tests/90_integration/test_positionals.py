# tests/90_integration/test_positionals.py

"""Tests for positional argument and flag interaction in serger.cli.

Tests verify that positional arguments work correctly for stitching builds,
including interaction with --include and other flags.
"""

from pathlib import Path

import pytest

import serger.cli as mod_cli
import serger.meta as mod_meta
from tests.utils import make_test_package, write_config_file


# --- constants --------------------------------------------------------------------

ARGPARSE_ERROR_EXIT_CODE = 2

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, argv: list[str]) -> int:
    """Helper to run CLI with a temporary working directory."""
    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    return mod_cli.main(argv)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Basic positional includes
# ---------------------------------------------------------------------------


def test_positional_include(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Positional arguments should be treated as includes."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    # Create output directory so is_dir() check works
    dist = tmp_path / "dist"
    dist.mkdir()

    # Create minimal config with package field (required for stitching)
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(config, package="mypkg", include=[], out="dist")

    # --- patch and execute ---
    code = _run_cli(monkeypatch, tmp_path, ["mypkg/**/*.py", "--out", "dist"])

    # --- verify ---
    assert code == 0

    stitched_file = dist / "mypkg.py"
    assert stitched_file.exists()
    assert stitched_file.is_file()


def test_multiple_positional_includes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Multiple positional arguments should all be treated as includes."""
    # --- setup ---
    pkg1_dir = tmp_path / "pkg1"
    pkg2_dir = tmp_path / "pkg2"
    # Use different function names to avoid collisions
    make_test_package(
        pkg1_dir,
        module_name="module1",
        module_content='def func1():\n    return "pkg1"\n',
    )
    make_test_package(
        pkg2_dir,
        module_name="module2",
        module_content='def func2():\n    return "pkg2"\n',
    )

    # Create output directory so is_dir() check works
    dist = tmp_path / "dist"
    dist.mkdir()

    # Create minimal config with package field (required for stitching)
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(config, package="pkg1", include=[], out="dist")

    # --- patch and execute ---
    code = _run_cli(
        monkeypatch, tmp_path, ["pkg1/**/*.py", "pkg2/**/*.py", "--out", "dist"]
    )

    # --- verify ---
    assert code == 0

    stitched_file = dist / "pkg1.py"
    assert stitched_file.exists()
    assert stitched_file.is_file()


# ---------------------------------------------------------------------------
# Explicit --out should make all positionals includes
# ---------------------------------------------------------------------------


def test_explicit_out_allows_many_includes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """If --out is given, all positionals become includes."""
    # --- setup ---
    pkg1_dir = tmp_path / "pkg1"
    pkg2_dir = tmp_path / "pkg2"
    # Use different function names to avoid collisions
    make_test_package(
        pkg1_dir,
        module_name="module1",
        module_content='def func1():\n    return "pkg1"\n',
    )
    make_test_package(
        pkg2_dir,
        module_name="module2",
        module_content='def func2():\n    return "pkg2"\n',
    )

    # Create output directory so is_dir() check works
    dist = tmp_path / "dist"
    dist.mkdir()

    # Create minimal config with package field (required for stitching)
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(config, package="pkg1", include=[], out="dist")

    # --- patch and execute ---
    code = _run_cli(
        monkeypatch, tmp_path, ["pkg1/**/*.py", "pkg2/**/*.py", "--out", "dist"]
    )

    # --- verify ---
    assert code == 0

    stitched_file = dist / "pkg1.py"
    assert stitched_file.exists()
    assert stitched_file.is_file()


# ---------------------------------------------------------------------------
# Explicit --include forbids any positionals
# ---------------------------------------------------------------------------


def test_positional_and_include_merge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Positional args and --include should merge together."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    # Create output directory so is_dir() check works
    dist = tmp_path / "dist"
    dist.mkdir()

    # Create minimal config
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(config, package="mypkg", include=[], out="dist")

    # --- patch and execute ---
    code = _run_cli(
        monkeypatch,
        tmp_path,
        ["mypkg/**/*.py", "--include", "mypkg/**/*.py", "--out", "dist"],
    )

    # --- verify ---
    assert code == 0
    stitched_file = dist / "mypkg.py"
    assert stitched_file.exists()
    assert stitched_file.is_file()


def test_positional_with_dry_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Dry-run should not create output files."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    # Create minimal config with package field (required for stitching)
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(config, package="mypkg", include=[], out="dist")

    # --- patch and execute ---
    code = _run_cli(
        monkeypatch, tmp_path, ["mypkg/**/*.py", "--out", "dist", "--dry-run"]
    )

    # --- verify ---
    assert code == 0
    assert not (tmp_path / "dist").exists()
