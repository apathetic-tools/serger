# tests/90_integration/test_configs.py
"""Tests for package.cli (package and standalone versions)."""

import json
from pathlib import Path

import pytest

import serger.cli as mod_cli
import serger.meta as mod_meta
from tests.utils import make_test_package, write_config_file


# --- constants --------------------------------------------------------------------

ARGPARSE_ERROR_EXIT_CODE = 2


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


def test_dry_run_creates_no_files(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dry-run should not create output files and should show comprehensive summary."""
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
    captured = capsys.readouterr()
    out = captured.out + captured.err

    # --- verify ---
    assert code == 0
    assert not (tmp_path / "dist").exists()
    # Should show comprehensive summary
    assert "dry-run" in out.lower() or "would stitch" in out.lower()
    assert "Package:" in out or "package:" in out.lower()
    assert "Files:" in out or "files:" in out.lower()


def test_validate_config_succeeds_with_valid_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--validate-config should succeed with valid configuration."""
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
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--validate-config"])

    # --- verify ---
    assert code == 0
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "✓ Configuration is valid" in out
    assert "file(s) collected" in out or "collected" in out
    # Should not create output files
    assert not (tmp_path / "dist").exists()


def test_validate_config_fails_with_invalid_path_format(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--validate-config should fail with invalid path format."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    # Create config with invalid output path type (should be string, not dict)
    config_data = {
        "package": "mypkg",
        "include": ["mypkg/**/*.py"],
        "out": {"invalid": "path"},  # Invalid: out should be a string, not dict
    }
    config.write_text(json.dumps(config_data))

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--validate-config"])

    # --- verify ---
    # Should fail during config resolution/validation
    assert code == 1
    captured = capsys.readouterr()
    out = captured.out + captured.err
    # May fail at schema validation or our custom validation
    assert (
        "validation failed" in out.lower()
        or "invalid" in out.lower()
        or "error" in out.lower()
    )


def test_validate_config_with_cli_args(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--validate-config should work with CLI arguments."""
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
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(
        ["--validate-config", "--include", "mypkg/**/*.py", "--out", "custom.py"]
    )

    # --- verify ---
    assert code == 0
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "✓ Configuration is valid" in out


def test_validate_config_with_module_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--validate-config should validate module actions syntax."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
        module_actions={"old_module": "new_module"},
    )

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--validate-config"])

    # --- verify ---
    assert code == 0
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "✓ Configuration is valid" in out


def test_validate_config_exits_early_no_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--validate-config should exit early without executing build."""
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
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--validate-config"])

    # --- verify ---
    assert code == 0
    # Should not create output files (exits before build)
    assert not (tmp_path / "dist").exists()


def test_validate_config_cli_only_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--validate-config should work in CLI-only mode (no config file)."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)
    # Create a pyproject.toml for package auto-detection
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "mypkg"\nversion = "1.0.0"\n')

    # --- execute ---
    # Package will be auto-detected from pyproject.toml
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(
        [
            "--validate-config",
            "--include",
            "mypkg/**/*.py",
            "--out",
            "dist/mypkg.py",
        ]
    )

    # --- verify ---
    assert code == 0
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "✓ Configuration is valid" in out
    assert "file(s) collected" in out or "collected" in out
    # Should not create output files
    assert not (tmp_path / "dist").exists()


def test_validate_config_no_files_collected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--validate-config should handle case where no files are collected."""
    # --- setup ---
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["nonexistent/**/*.py"],  # Pattern that matches nothing
        out="dist/mypkg.py",
    )

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--validate-config"])

    # --- verify ---
    assert code == 0  # Validation succeeds even if no files found
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "✓ Configuration is valid" in out
    assert "no files" in out or "not a stitch build" in out


def test_validate_config_with_excludes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--validate-config should work with exclude patterns."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)
    # Create a test file that should be excluded
    (pkg_dir / "test_file.py").write_text("# test file\n")

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        exclude=["**/test*.py"],
        out="dist/mypkg.py",
    )

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--validate-config"])

    # --- verify ---
    assert code == 0
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "✓ Configuration is valid" in out


def test_validate_config_with_multiple_includes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--validate-config should work with multiple include patterns."""
    # --- setup ---
    pkg_dir1 = tmp_path / "pkg1"
    pkg_dir1.mkdir()
    (pkg_dir1 / "__init__.py").write_text("# pkg1\n")
    (pkg_dir1 / "module1.py").write_text("# module1\n")

    pkg_dir2 = tmp_path / "pkg2"
    pkg_dir2.mkdir()
    (pkg_dir2 / "__init__.py").write_text("# pkg2\n")
    (pkg_dir2 / "module2.py").write_text("# module2\n")

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="pkg1",
        include=["pkg1/**/*.py", "pkg2/**/*.py"],
        out="dist/combined.py",
    )

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--validate-config"])

    # --- verify ---
    assert code == 0
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "✓ Configuration is valid" in out
    assert "file(s) collected" in out


def test_validate_config_fails_with_missing_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--validate-config should fail when package is missing for stitch build."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    # Write config directly without package (helper requires package)
    config_data = {
        "include": ["mypkg/**/*.py"],
        "out": "dist/mypkg.py",
    }
    config.write_text(json.dumps(config_data))

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--validate-config"])

    # --- verify ---
    # Should fail because package is required for stitch builds
    assert code == 1
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "package" in out.lower() or "error" in out.lower()


def test_validate_config_vs_dry_run_difference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--validate-config exits early; --dry-run simulates full pre-stitch pipeline."""
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

    # --- execute validate-config ---
    monkeypatch.chdir(tmp_path)
    code1 = mod_cli.main(["--validate-config"])
    captured1 = capsys.readouterr()
    out1 = captured1.out + captured1.err

    # --- execute dry-run ---
    code2 = mod_cli.main(["--dry-run"])
    captured2 = capsys.readouterr()
    out2 = captured2.out + captured2.err

    # --- verify ---
    assert code1 == 0
    assert code2 == 0
    # validate-config exits early after file collection
    assert "✓ Configuration is valid" in out1
    assert "file(s) collected" in out1
    # Dry-run goes further and shows comprehensive summary
    assert "dry-run" in out2.lower() or "would stitch" in out2.lower()
    # Dry-run should show comprehensive summary with package, files, output
    assert "Package:" in out2 or "package:" in out2.lower()
    assert "Files:" in out2 or "files:" in out2.lower()
    assert "Output:" in out2 or "output:" in out2.lower()


def test_validate_config_and_dry_run_mutually_exclusive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--validate-config and --dry-run should be mutually exclusive."""
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

    # --- execute (validate-config first) ---
    monkeypatch.chdir(tmp_path)
    # argparse should exit with SystemExit(2)
    with pytest.raises(SystemExit) as e:
        mod_cli.main(["--validate-config", "--dry-run"])

    # --- verify ---
    assert e.value.code == ARGPARSE_ERROR_EXIT_CODE
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "not allowed with" in out.lower()
    assert "--validate-config" in out
    assert "--dry-run" in out

    # --- execute (dry-run first) ---
    # argparse should exit with SystemExit(2) regardless of order
    with pytest.raises(SystemExit) as e2:
        mod_cli.main(["--dry-run", "--validate-config"])

    # --- verify ---
    assert e2.value.code == ARGPARSE_ERROR_EXIT_CODE
    captured2 = capsys.readouterr()
    out2 = captured2.out + captured2.err
    assert "not allowed with" in out2.lower()
    assert "--validate-config" in out2
    assert "--dry-run" in out2


def test_dry_run_processes_excludes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dry-run should process excludes and show correct file count."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)
    # Create an extra file that will be excluded
    (pkg_dir / "excluded.py").write_text("# excluded\n")

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        exclude=["**/excluded.py"],
        out="dist/mypkg.py",
    )

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--dry-run"])
    captured = capsys.readouterr()
    out = captured.out + captured.err

    # --- verify ---
    assert code == 0
    # Should show file count after exclusions (should not include excluded.py)
    assert "dry-run" in out.lower() or "would stitch" in out.lower()
    # File count should reflect excludes (typically 2 files: __init__.py and main.py)
    assert "Files:" in out or "files:" in out.lower()


def test_dry_run_detects_packages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dry-run should detect packages (visible in debug output)."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)
    # Create a subpackage
    subpkg_dir = pkg_dir / "subpkg"
    subpkg_dir.mkdir()
    (subpkg_dir / "__init__.py").write_text("# subpkg\n")

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
    )

    # --- execute with debug logging ---
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    code = mod_cli.main(["--dry-run"])
    captured = capsys.readouterr()
    out = captured.out + captured.err

    # --- verify ---
    assert code == 0
    # Debug output should show detected packages
    assert "Detected packages" in out or "detected packages" in out.lower()


def test_dry_run_resolves_order_explicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dry-run should process explicit order."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir, module_name="main")

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        order=["mypkg/__init__.py", "mypkg/main.py"],
        out="dist/mypkg.py",
    )

    # --- execute with debug logging ---
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    code = mod_cli.main(["--dry-run"])
    captured = capsys.readouterr()
    out = captured.out + captured.err

    # --- verify ---
    assert code == 0
    # Debug output should show explicit order
    assert "Using explicit order" in out or "explicit" in out.lower()


def test_dry_run_resolves_order_auto_discovered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dry-run should auto-discover order via topological sort."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        # No order specified - should auto-discover
        out="dist/mypkg.py",
    )

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--dry-run"])
    captured = capsys.readouterr()
    out = captured.out + captured.err

    # --- verify ---
    assert code == 0
    # Should show auto-discovery message
    assert "auto-discovering" in out.lower() or "auto-discovered" in out.lower()


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
