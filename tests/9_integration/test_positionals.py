# tests/9_integration/test_positionals.py

"""Tests for positional argument and flag interaction in serger.cli.

Tests verify that positional arguments work correctly for stitching builds,
including interaction with --out, --include, and other flags.
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
# Basic shorthand: src dist
# ---------------------------------------------------------------------------


def test_positional_include_and_out_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """`mypkg dist` should treat mypkg as include and dist (directory) as out."""
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
    code = _run_cli(monkeypatch, tmp_path, ["mypkg/**/*.py", "dist"])

    # --- verify ---
    assert code == 0

    stitched_file = dist / "mypkg.py"
    assert stitched_file.exists()
    assert stitched_file.is_file()


def test_multiple_includes_and_out_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """`pkg1/** pkg2/** dist` should treat pkg1/pkg2 as includes and dist as out."""
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
    code = _run_cli(monkeypatch, tmp_path, ["pkg1/**/*.py", "pkg2/**/*.py", "dist"])

    # --- verify ---
    assert code == 0

    stitched_file = dist / "pkg1.py"
    assert stitched_file.exists()
    assert stitched_file.is_file()


def test_positional_include_and_out_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """`mypkg/** dist/output.py` should treat mypkg as include and output file."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    # Create minimal config with package field (required for stitching)
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(config, package="mypkg", include=[], out="dist/output.py")

    # --- patch and execute ---
    code = _run_cli(monkeypatch, tmp_path, ["mypkg/**/*.py", "dist/stitch_output.py"])

    # --- verify ---
    assert code == 0

    output_file = tmp_path / "dist" / "stitch_output.py"
    assert output_file.exists()
    assert output_file.is_file()


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


@pytest.mark.parametrize(
    "argv",
    [
        ["mypkg", "--include", "mypkg/**/*.py"],
        ["mypkg", "dist", "--include", "mypkg/**/*.py"],
    ],
)
def test_error_on_positional_with_include(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    argv: list[str],
) -> None:
    """Any positional args combined with --include should error."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    # Create minimal config
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(config, package="mypkg", include=[], out="dist")

    # --- patch, execute and verify ---
    with pytest.raises(SystemExit) as e:
        _run_cli(monkeypatch, tmp_path, argv)
    assert e.value.code == ARGPARSE_ERROR_EXIT_CODE


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
    code = _run_cli(monkeypatch, tmp_path, ["mypkg/**/*.py", "dist", "--dry-run"])

    # --- verify ---
    assert code == 0
    assert not (tmp_path / "dist").exists()


def test_trailing_slash_handled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Trailing slashes in paths should be handled correctly."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    # Create output directory so is_dir() check works
    dist = tmp_path / "dist"
    dist.mkdir()

    # Create minimal config with package field (required for stitching)
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(config, package="mypkg", include=[], out="dist/")

    # --- patch and execute ---
    code = _run_cli(monkeypatch, tmp_path, ["mypkg/**/*.py", "dist/"])

    # --- verify ---
    assert code == 0
    stitched_file = dist / "mypkg.py"
    assert stitched_file.exists()
    assert stitched_file.is_file()
