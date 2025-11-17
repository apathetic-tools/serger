# tests/9_integration/test_configs.py
"""Tests for package.cli (package and standalone versions)."""

import json
from pathlib import Path

import pytest

import serger.cli as mod_cli
import serger.meta as mod_meta
from tests.utils import make_test_package, write_config_file


def test_main_no_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should print a warning and return exit code 1 when config is missing."""
    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    assert code == 1
    captured = capsys.readouterr()
    out = (captured.out + captured.err).lower()
    # After removing early bailout, configless builds proceed and fail later
    # with "no include patterns found" instead of "no build config found"
    assert "no include patterns found" in out or "no build config found" in out


def test_main_with_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should detect config, run one build, and exit cleanly."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    out = capsys.readouterr().out.lower()
    assert code == 0
    assert "stitch completed" in out
    assert "✅ stitch completed" in out


def test_dry_run_creates_no_files(tmp_path: Path) -> None:
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
    )

    # --- execute ---
    code = mod_cli.main(["--config", str(config), "--dry-run"])

    # --- verify ---
    assert code == 0
    assert not (tmp_path / "dist").exists()


def test_main_with_custom_config(tmp_path: Path) -> None:
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
    )

    # --- execute ---
    code = mod_cli.main(["--config", str(config)])

    # --- verify ---
    assert code == 0


def test_main_invalid_config(tmp_path: Path) -> None:
    # --- setup ---
    bad = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    bad.write_text("{not valid json}")

    # --- execute ---
    code = mod_cli.main(["--config", str(bad)])

    # --- verify ---
    assert code == 1


# --------------------------------------------------------------------------- #
# Missing includes warning/error tests (respecting strict_config)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("config_content", "cli_args", "expect_exit", "expect_msg", "description"),
    [  # pyright: ignore[reportUnknownArgumentType]
        # Explicit include:[] means intentional empty - no warning
        (
            {"include": [], "out": "dist"},
            [],
            0,
            None,
            "explicit_include_empty",
        ),
        # Empty list shorthand [] parses to None, triggers "no config" error
        (
            "[]",
            [],
            1,
            "no include patterns found",
            "empty_list_shorthand",
        ),
        # Empty builds with strict_config=false - should fail validation
        (
            # Should fail - builds not supported
            {"strict_config": False, "builds": []},
            [],
            1,
            "builds",
            "empty_builds_strict_false",
        ),
        # Empty builds with strict_config=true - should fail validation
        (
            # Should fail - builds not supported
            {"strict_config": True, "builds": []},
            [],
            1,
            "builds",
            "empty_builds_strict_true",
        ),
        # Build missing include, strict_config=false - warn only
        (
            {"strict_config": False, "out": "dist/mypkg.py"},
            [],
            0,
            "No include patterns found",
            "missing_include_strict_false",
        ),
        # Build missing include, strict_config=true - error
        (
            {"strict_config": True, "out": "dist/mypkg.py"},
            [],
            1,
            "No include patterns found",
            "missing_include_strict_true",
        ),
        # Build overrides root strict=true to false - warn only
        (
            {
                "strict_config": False,
                "out": "dist/mypkg.py",
            },
            [],
            0,
            "No include patterns found",
            "build_override_to_false",
        ),
        # Build overrides root strict=false to true - error
        (
            {
                "strict_config": True,
                "out": "dist/mypkg.py",
            },
            [],
            1,
            "No include patterns found",
            "build_override_to_true",
        ),
        # Missing include but CLI provides --include - no warning
        # Package will be inferred from include path
        (
            {"out": "dist/mypkg.py", "module_bases": ["."]},
            ["--include", "mypkg/**/*.py"],
            0,
            None,
            "cli_include_provided",
        ),
        # Missing include but CLI provides --add-include - no warning
        # Package will be inferred from include path
        (
            {"out": "dist/mypkg.py", "module_bases": ["."]},
            ["--add-include", "mypkg/**/*.py"],
            0,
            None,
            "cli_add_include_provided",
        ),
        # Empty object {} parses to None, triggers "no config" error
        (
            "{}",
            [],
            1,
            "no include patterns found",
            "empty_object_config",
        ),
        # Config with only log_level, no builds - error (default strict=true)
        (
            {"log_level": "debug"},
            [],
            1,
            "No include patterns found",
            "only_log_level",
        ),
        # Multiple builds - should fail validation
        (
            {
                "builds": [
                    {"include": ["mypkg/**/*.py"], "out": "dist1/mypkg.py"},
                    {"out": "dist2/mypkg.py"},
                ]
            },  # Should fail - multi-build not supported
            [],
            1,
            "builds",
            "mixed_builds_one_has_includes",
        ),
    ],
    ids=lambda x: x if isinstance(x, str) and not x.startswith("{") else "",
)
def test_missing_includes_behavior(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    config_content: dict[str, object] | str,
    cli_args: list[str],
    expect_exit: int,
    expect_msg: str | None,
    description: str,
) -> None:
    """Test missing includes warning/error with various configurations."""
    # --- setup ---
    # Create test package for tests that need actual files
    if "--include" in cli_args or "--add-include" in cli_args:
        pkg_dir = tmp_path / "mypkg"
        make_test_package(pkg_dir)
    elif isinstance(config_content, dict) and "include" in config_content:
        # Check if config has includes - if so, create package
        includes = config_content.get("include", [])
        if isinstance(includes, list) and includes:
            pkg_dir = tmp_path / "mypkg"
            make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    if isinstance(config_content, str):
        config.write_text(config_content)
    else:
        config.write_text(json.dumps(config_content))

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(cli_args)

    # --- verify ---
    assert code == expect_exit, f"Failed: {description}"
    captured = capsys.readouterr()
    combined = (captured.out + captured.err).lower()

    if expect_msg:
        assert expect_msg.lower() in combined, (
            f"Failed: {description} - expected message not found"
        )
    else:
        assert "no include patterns found" not in combined, (
            f"Failed: {description} - unexpected warning"
        )


def test_config_discovery_finds_closest_parent_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Config discovery should find closest config in parent directories."""
    # --- setup ---
    # Create directory structure: root/parent/child
    root = tmp_path / "root"
    parent = root / "parent"
    child = parent / "child"
    child.mkdir(parents=True)

    # Create test packages
    root_pkg = root / "root_pkg"
    parent_pkg = parent / "parent_pkg"
    make_test_package(root_pkg)
    make_test_package(parent_pkg)

    # Create config files with different package names and output paths
    root_config = root / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        root_config,
        package="root_pkg",
        include=["root_pkg/**/*.py"],
        out="root_dist/root_pkg.py",
    )

    parent_config = parent / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        parent_config,
        package="parent_pkg",
        include=["parent_pkg/**/*.py"],
        out="parent_dist/parent_pkg.py",
    )

    # --- execute from child directory ---
    monkeypatch.chdir(child)
    code = mod_cli.main([])

    # --- verify ---
    assert code == 0
    captured = capsys.readouterr()
    out = captured.out + captured.err

    # Should use parent config (closest), not root config
    # Verify parent config values are used
    assert "parent_pkg" in out
    assert "parent_dist" in out
    # Verify root config values are NOT used (proves no merging)
    # Both should be absent - if merging occurred, we'd see root values too
    assert "root_pkg" not in out
    assert "root_dist" not in out

    # Verify the correct output file was created
    parent_dist = parent / "parent_dist"
    assert parent_dist.exists()
    assert (parent_dist / "parent_pkg.py").exists()

    # Verify root output was NOT created (proves closest config wins)
    root_dist = root / "root_dist"
    assert not root_dist.exists()
