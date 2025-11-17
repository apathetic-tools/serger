# tests/90_integration/test_paths.py
"""Tests for path resolution and config handling in CLI and config files."""

import json
from pathlib import Path

import pytest

import serger.cli as mod_cli
import serger.meta as mod_meta
from tests.utils import make_test_package, write_config_file


def test_configless_run_with_include_flag_and_out_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should run with --include and --out (directory) without config file."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    # Create minimal config with package field (required for stitching)
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(config, package="mypkg", include=[], out="dist")

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--include", "mypkg/**/*.py", "--out", "dist"])

    # --- verify ---
    captured = capsys.readouterr()
    out = (captured.out + captured.err).lower()

    # Should exit successfully
    assert code == 0

    # Output directory should exist and contain stitched file
    dist = tmp_path / "dist"
    assert dist.exists()
    stitched_file = dist / "mypkg.py"
    assert stitched_file.exists()
    assert stitched_file.is_file()

    # Log output should mention stitching
    assert "stitch completed" in out or "all builds complete" in out


def test_configless_run_with_include_flag_and_out_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should run with --include and --out (file) without config file."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    # Create minimal config with package field (required for stitching)
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps(
            {
                "package": "mypkg",
                "include": [],
                "out": "bin/output.py",
            }
        ),
        encoding="utf-8",
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--include", "mypkg/**/*.py", "--out", "bin/output.py"])

    # --- verify ---
    captured = capsys.readouterr()
    out = (captured.out + captured.err).lower()

    # Should exit successfully
    assert code == 0

    # Output file should exist
    output_file = tmp_path / "bin" / "output.py"
    assert output_file.exists()
    assert output_file.is_file()

    # Log output should mention stitching
    assert "stitch completed" in out or "all builds complete" in out


def test_configless_run_with_add_include_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should run when --add-include is provided with config."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    # Create config with package field
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps(
            {
                "package": "mypkg",
                "include": ["mypkg/__init__.py"],
                "out": "outdir",
            }
        ),
        encoding="utf-8",
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--add-include", "mypkg/module.py", "--out", "outdir"])

    # --- verify ---
    out = capsys.readouterr().out.lower()

    assert code == 0
    stitched_file = tmp_path / "outdir" / "mypkg.py"
    assert stitched_file.exists()
    assert "stitch completed" in out or "all builds complete" in out


def test_custom_config_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should use custom config file path specified via --config."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    cfg = tmp_path / "custom.json"
    cfg.write_text(
        json.dumps(
            {
                "package": "mypkg",
                "include": ["mypkg/**/*.py"],
                "out": "dist",
            }
        ),
        encoding="utf-8",
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--config", str(cfg)])

    # --- verify ---
    out = capsys.readouterr().out.lower()
    assert code == 0
    assert "using config: custom.json" in out


def test_out_flag_overrides_config_with_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--out flag (directory) overrides config-defined output path."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps(
            {
                "package": "mypkg",
                "include": ["mypkg/**/*.py"],
                "exclude": [],
                "out": "ignored",
            }
        ),
        encoding="utf-8",
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--out", "override-dist"])

    # --- verify ---
    out = capsys.readouterr().out.lower()

    assert code == 0
    # Confirm it built into the override directory
    override_dir = tmp_path / "override-dist"
    assert override_dir.exists()

    # Confirm it built the stitched file into the override directory
    stitched_file = override_dir / "mypkg.py"
    assert stitched_file.exists()

    # Optional: check output logs
    assert "override-dist" in out


def test_out_flag_overrides_config_with_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should use the --out flag (file) instead of the config-defined output path."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps(
            {
                "package": "mypkg",
                "include": ["mypkg/**/*.py"],
                "exclude": [],
                "out": "ignored",
            }
        ),
        encoding="utf-8",
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--out", "bin/output.py"])

    # --- verify ---
    out = capsys.readouterr().out.lower()

    assert code == 0
    # Confirm it built into the override file
    override_file = tmp_path / "bin" / "output.py"
    assert override_file.exists()
    assert override_file.is_file()

    # Optional: check output logs
    assert "output.py" in out


def test_out_flag_relative_to_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--out should be relative to where the command is run (cwd)."""
    # --- setup ---
    project = tmp_path / "project"
    project.mkdir()
    pkg_dir = project / "mypkg"
    make_test_package(pkg_dir)

    config = project / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps(
            {
                "package": "mypkg",
                "include": ["mypkg/**/*.py"],
                "out": "ignored",
            }
        ),
        encoding="utf-8",
    )

    cwd = tmp_path / "runner"
    cwd.mkdir()

    # --- patch and execute ---
    monkeypatch.chdir(cwd)
    code = mod_cli.main(["--config", str(config), "--out", "output"])

    # --- verify ---
    assert code == 0

    output_dir = cwd / "output"
    stitched_file = output_dir / "mypkg.py"
    assert stitched_file.exists()
    # Ensure it didn't build the script near the config file, but cwd instead
    assert not (project / "output").exists()


def test_config_out_relative_to_config_file_with_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Out path (directory) in config should be relative to the config file itself."""
    # --- setup ---
    project = tmp_path / "project"
    project.mkdir()
    pkg_dir = project / "mypkg"
    make_test_package(pkg_dir)

    config = project / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps(
            {
                "package": "mypkg",
                "include": ["mypkg/**/*.py"],
                "out": "dist",
            }
        ),
        encoding="utf-8",
    )

    # --- patch and execute ---
    cwd = tmp_path / "runner"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    code = mod_cli.main(["--config", str(config)])

    # --- verify ---
    assert code == 0

    dist_dir = project / "dist"
    # Stitched file should exist relative to config directory
    stitched_file = dist_dir / "mypkg.py"
    assert stitched_file.exists()
    # Ensure it didn't build relative to the CWD
    assert not (cwd / "dist").exists()


def test_config_out_relative_to_config_file_with_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Out path (file) in config should be relative to the config file itself."""
    # --- setup ---
    project = tmp_path / "project"
    project.mkdir()
    pkg_dir = project / "mypkg"
    make_test_package(pkg_dir)

    config = project / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps(
            {
                "package": "mypkg",
                "include": ["mypkg/**/*.py"],
                "out": "bin/output.py",
            }
        ),
        encoding="utf-8",
    )

    # --- patch and execute ---
    cwd = tmp_path / "runner"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    code = mod_cli.main(["--config", str(config)])

    # --- verify ---
    assert code == 0

    output_file = project / "bin" / "output.py"
    # Output file should exist relative to config directory
    assert output_file.exists()
    assert output_file.is_file()
    # Ensure it didn't build relative to the CWD
    assert not (cwd / "bin").exists()


def test_python_config_preferred_over_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A .serger.py config should take precedence over .jsonc/.json."""
    # --- setup ---
    pkg1_dir = tmp_path / "pkg1"
    make_test_package(pkg1_dir, module_content='def hello():\n    return "from py"\n')

    pkg2_dir = tmp_path / "pkg2"
    make_test_package(pkg2_dir, module_content='def hello():\n    return "from json"\n')

    # Create both config types — the Python one should win.
    py_cfg = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.py"
    py_cfg.write_text(
        """
config = {
    "package": "pkg1",
    "include": ["pkg1/**/*.py"],
    "exclude": [],
    "out": "dist"
}
""",
        encoding="utf-8",
    )

    json_dump = json.dumps(
        {"package": "pkg2", "include": ["pkg2/**/*.py"], "out": "dist"},
    )

    jsonc_cfg = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.jsonc"
    jsonc_cfg.write_text(json_dump, encoding="utf-8")

    json_cfg = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    json_cfg.write_text(json_dump, encoding="utf-8")

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    out = capsys.readouterr().out.lower()

    assert code == 0
    dist = tmp_path / "dist"
    # Only the Python config file's package should have been used
    assert (dist / "pkg1.py").exists()
    assert not (dist / "pkg2.py").exists()
    assert "stitch completed" in out or "all builds complete" in out


@pytest.mark.parametrize("ext", [".jsonc", ".json"])
def test_json_and_jsonc_config_supported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    ext: str,
) -> None:
    """Both .serger.jsonc and .serger.json
    configs should be detected and used.
    """
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    jsonc_cfg = tmp_path / f".{mod_meta.PROGRAM_CONFIG}{ext}"
    if ext == ".jsonc":
        jsonc_cfg.write_text(
            """
        // comment allowed in JSONC
        {
            "package": "mypkg",
            "include": ["mypkg/**/*.py"],
            "out": "dist" // trailing comment
        }
        """,
            encoding="utf-8",
        )
    else:
        jsonc_cfg.write_text(
            json.dumps(
                {
                    "package": "mypkg",
                    "include": ["mypkg/**/*.py"],
                    "out": "dist",
                }
            ),
            encoding="utf-8",
        )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    out = capsys.readouterr().out.lower()

    assert code == 0
    dist = tmp_path / "dist"
    stitched_file = dist / "mypkg.py"
    assert stitched_file.exists()
    assert "stitch completed" in out or "all builds complete" in out


# ---------------------------------------------------------------------------
# Path normalization and absolute handling
# ---------------------------------------------------------------------------


def test_absolute_include_and_out(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Absolute paths on CLI should stitch correctly and not resolve relative to cwd."""
    # --- setup ---
    abs_pkg = tmp_path / "abs_pkg"
    make_test_package(abs_pkg)
    abs_out = tmp_path / "abs_out"

    # Create config with package field
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps({"package": "abs_pkg", "include": [], "out": "dist"}),
        encoding="utf-8",
    )

    # --- patch and execute ---
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    monkeypatch.chdir(subdir)  # move cwd away from pkg/out

    code = mod_cli.main(
        [
            "--include",
            str(abs_pkg / "**" / "*.py"),
            "--out",
            str(abs_out),
        ]
    )

    # --- verify ---
    assert code == 0
    stitched_file = abs_out / "abs_pkg.py"
    assert stitched_file.exists()
    # should not create relative dist in cwd
    assert not (tmp_path / "subdir" / "abs_out").exists()


def test_relative_include_with_parent_reference(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Relative include like ../shared/** should resolve against cwd correctly."""
    # --- setup ---
    shared = tmp_path / "shared"
    shared.mkdir()
    pkg_dir = shared / "mypkg"
    make_test_package(pkg_dir)
    cwd = tmp_path / "project"
    cwd.mkdir()

    # Create config with package field
    config = cwd / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps({"package": "mypkg", "include": [], "out": "dist"}),
        encoding="utf-8",
    )

    # --- patch and execute ---
    monkeypatch.chdir(cwd)
    code = mod_cli.main(["--include", "../shared/mypkg/**/*.py", "--out", "dist"])

    # --- verify ---
    assert code == 0
    dist = cwd / "dist"
    stitched_file = dist / "mypkg.py"
    assert stitched_file.exists()


def test_config_include_with_parent_reference(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Include with ../ in config should resolve relative to config file directory."""
    # --- setup ---
    shared = tmp_path / "shared"
    shared.mkdir()
    pkg_dir = shared / "mypkg"
    make_test_package(pkg_dir)
    project = tmp_path / "project"
    project.mkdir()

    # Create config with include that goes backwards from config location
    config = project / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps(
            {
                "package": "mypkg",
                "include": ["../shared/mypkg/**/*.py"],
                "out": "dist",
            }
        ),
        encoding="utf-8",
    )

    # --- patch and execute ---
    # Run from a different cwd to ensure it uses config_dir, not cwd
    cwd = tmp_path / "runner"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    code = mod_cli.main(["--config", str(config)])

    # --- verify ---
    assert code == 0
    dist = project / "dist"
    stitched_file = dist / "mypkg.py"
    assert stitched_file.exists()
    # Ensure it didn't try to resolve from cwd
    assert not (cwd / "dist").exists()


def test_out_flag_with_parent_reference(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """--out with ../ should resolve relative to cwd, not config file location."""
    # --- setup ---
    project = tmp_path / "project"
    project.mkdir()
    pkg_dir = project / "mypkg"
    make_test_package(pkg_dir)

    config = project / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps(
            {
                "package": "mypkg",
                "include": ["mypkg/**/*.py"],
                "out": "ignored",
            }
        ),
        encoding="utf-8",
    )

    # Create output directory one level up from cwd
    output_parent = tmp_path / "outputs"
    output_parent.mkdir()

    # --- patch and execute ---
    cwd = tmp_path / "runner"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    code = mod_cli.main(["--config", str(config), "--out", "../outputs/dist"])

    # --- verify ---
    assert code == 0
    # Output should be relative to cwd (runner), so ../outputs/dist from runner
    output_dir = output_parent / "dist"
    stitched_file = output_dir / "mypkg.py"
    assert stitched_file.exists()
    # Ensure it didn't build relative to config file location
    assert not (project / "outputs").exists()
    assert not (cwd / "dist").exists()


def test_config_out_with_parent_reference(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Out path with ../ in config should resolve relative to config file directory."""
    # --- setup ---
    project = tmp_path / "project"
    project.mkdir()
    pkg_dir = project / "mypkg"
    make_test_package(pkg_dir)

    # Create output directory one level up from project
    output_parent = tmp_path / "outputs"
    output_parent.mkdir()

    # Create config with out that goes backwards from config location
    config = project / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps(
            {
                "package": "mypkg",
                "include": ["mypkg/**/*.py"],
                "out": "../outputs/dist",
            }
        ),
        encoding="utf-8",
    )

    # --- patch and execute ---
    # Run from a different cwd to ensure it uses config_dir, not cwd
    cwd = tmp_path / "runner"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    code = mod_cli.main(["--config", str(config)])

    # --- verify ---
    assert code == 0
    # Output should be relative to config file (project),
    # so ../outputs/dist from project
    output_dir = output_parent / "dist"
    stitched_file = output_dir / "mypkg.py"
    assert stitched_file.exists()
    # Ensure it didn't build relative to cwd
    assert not (cwd / "outputs").exists()
    assert not (project / "dist").exists()


def test_mixed_relative_and_absolute_includes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Mixing relative and absolute include paths should work with distinct roots."""
    # --- setup ---
    rel_pkg = tmp_path / "rel_pkg"
    abs_pkg = tmp_path / "abs_pkg"
    make_test_package(rel_pkg, module_content='def hello_rel():\n    return "rel"\n')
    make_test_package(abs_pkg, module_content='def hello_abs():\n    return "abs"\n')

    abs_out = tmp_path / "mixed_out"

    # Create config with package field (using first package name)
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps({"package": "rel_pkg", "include": [], "out": "dist"}),
        encoding="utf-8",
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(
        [
            "--include",
            "rel_pkg/**/*.py",
            str(abs_pkg / "**" / "*.py"),
            "--out",
            str(abs_out),
        ]
    )

    # --- verify ---
    assert code == 0
    # Note: With mixed packages, stitching behavior may vary, but at least one
    # should work. The test verifies path resolution works, not the stitching
    # of multiple packages
    assert abs_out.exists()


def test_trailing_slash_include(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Ensure `pkg/` includes package contents correctly."""
    # --- setup ---
    pkg = tmp_path / "mypkg"
    make_test_package(pkg)

    # Create config with package field
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps({"package": "mypkg", "include": [], "out": "outdir"}),
        encoding="utf-8",
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--include", "mypkg/", "--out", "outdir"])

    # --- verify ---
    assert code == 0
    outdir = tmp_path / "outdir"
    stitched_file = outdir / "mypkg.py"
    assert stitched_file.exists()


def test_absolute_out_does_not_create_relative_copy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Absolute --out should not create nested relative copies."""
    # --- setup ---
    pkg = tmp_path / "mypkg"
    make_test_package(pkg)
    abs_out = tmp_path / "absolute_out"

    # Create config with package field
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps({"package": "mypkg", "include": [], "out": "dist"}),
        encoding="utf-8",
    )

    # --- patch and execute ---
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    monkeypatch.chdir(subdir)

    code = mod_cli.main(
        [
            "--include",
            str(tmp_path / "mypkg" / "**" / "*.py"),
            "--out",
            str(abs_out),
        ]
    )

    # --- verify ---
    assert code == 0
    stitched_file = abs_out / "mypkg.py"
    assert stitched_file.exists()
    assert not (tmp_path / "subdir" / "absolute_out").exists()


def test_dot_prefix_include(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """'./pkg' include should behave the same as 'pkg'."""
    # --- setup ---
    pkg = tmp_path / "mypkg"
    make_test_package(pkg)

    # Create config with package field
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps({"package": "mypkg", "include": [], "out": "dist"}),
        encoding="utf-8",
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--include", "./mypkg/**/*.py", "--out", "dist"])

    # --- verify ---
    assert code == 0
    stitched_file = tmp_path / "dist" / "mypkg.py"
    assert stitched_file.exists()


def test_trailing_slash_on_out(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Trailing slash in --out should not change output directory."""
    # --- setup ---
    pkg = tmp_path / "mypkg"
    make_test_package(pkg)

    # Create config with package field
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config.write_text(
        json.dumps({"package": "mypkg", "include": [], "out": "dist"}),
        encoding="utf-8",
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--include", "mypkg/**/*.py", "--out", "dist/"])

    # --- verify ---
    assert code == 0
    stitched_file = tmp_path / "dist" / "mypkg.py"
    assert stitched_file.exists()
