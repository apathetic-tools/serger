# tests/9_integration/test_overrides.py
"""Tests for CLI flag overrides of config file settings.

Tests that --include, --exclude, --add-include, and --add-exclude
properly override or extend config file patterns.
"""

from pathlib import Path

import pytest

import serger.cli as mod_cli
import serger.meta as mod_meta
from tests.utils import make_test_package, write_config_file


def test_include_flag_overrides_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--include should override config include patterns."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(
        pkg_dir, module_name="foo", module_content='def foo():\n    return "ok"\n'
    )
    # Create a subdirectory with another module
    sub_dir = pkg_dir / "sub"
    sub_dir.mkdir()
    (sub_dir / "__init__.py").write_text("")
    (sub_dir / "bar.py").write_text('def bar():\n    return "nope"\n')

    # Config originally points to subdirectory only
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/sub/**/*.py"],
        out="dist/mypkg.py",
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    # Override include at CLI level to include all of mypkg
    code = mod_cli.main(["--include", "mypkg/**/*.py"])

    # --- verify ---
    out = capsys.readouterr().out.lower()

    assert code == 0
    # Should stitch all of mypkg, not just sub
    stitched_file = tmp_path / "dist" / "mypkg.py"
    assert stitched_file.exists()
    content = stitched_file.read_text()
    # Should include both foo and bar
    assert "def foo" in content
    assert "def bar" in content
    assert "stitch completed" in out
    assert "✅ stitch completed" in out


def test_exclude_flag_overrides_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--exclude should override config exclude patterns."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(
        pkg_dir,
        module_name="keep",
        module_content='def keep():\n    return "keep me"\n',
    )
    # Create a Python file that should be excluded
    (pkg_dir / "ignore.py").write_text('def ignore():\n    return "ignore me"\n')

    # Config has no exclude rules
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    # Pass exclude override on CLI
    code = mod_cli.main(["--exclude", "*ignore*.py"])

    # --- verify ---
    out = capsys.readouterr().out.lower()

    assert code == 0
    stitched_file = tmp_path / "dist" / "mypkg.py"
    assert stitched_file.exists()
    # The ignore.py file should be excluded
    content = stitched_file.read_text()
    assert "def keep" in content
    assert "def ignore" not in content
    assert "stitch completed" in out
    assert "✅ stitch completed" in out


def test_add_include_extends_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--add-include should extend config include patterns, not override them."""
    # --- setup ---
    src_pkg = tmp_path / "srcpkg"
    make_test_package(
        src_pkg, module_name="a", module_content='def a():\n    return "A"\n'
    )

    extra_pkg = tmp_path / "extrapkg"
    make_test_package(
        extra_pkg, module_name="b", module_content='def b():\n    return "B"\n'
    )

    # Config includes only srcpkg/**
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="srcpkg",
        include=["srcpkg/**/*.py"],
        out="dist/combined.py",
    )

    # --- patch and execute ---
    # Run with --add-include extrapkg/**
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--add-include", "extrapkg/**/*.py"])

    # --- verify ---
    out = capsys.readouterr().out.lower()

    assert code == 0
    stitched_file = tmp_path / "dist" / "combined.py"
    assert stitched_file.exists()

    # ✅ Both packages should be included in the stitched output
    content = stitched_file.read_text()
    assert "def a" in content
    assert "def b" in content

    # Output should confirm the build
    assert "stitch completed" in out
    assert "✅ stitch completed" in out


def test_add_exclude_extends_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--add-exclude should extend config exclude patterns, not override them."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(
        pkg_dir,
        module_name="keep",
        module_content='def keep():\n    return "keep"\n',
    )
    # Create Python files that should be excluded
    (pkg_dir / "ignore_tmp.py").write_text('def ignore_tmp():\n    return "ignore"\n')
    (pkg_dir / "ignore_log.py").write_text('def ignore_log():\n    return "ignore2"\n')

    # Config excludes *ignore_log*.py files
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        exclude=["*ignore_log*.py"],
        out="dist/mypkg.py",
    )

    # --- patch and execute ---
    # Add an extra exclude via CLI
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--add-exclude", "*ignore_tmp*.py"])

    # --- verify ---
    out = capsys.readouterr().out.lower()

    assert code == 0
    stitched_file = tmp_path / "dist" / "mypkg.py"
    assert stitched_file.exists()

    content = stitched_file.read_text()
    # ✅ keep module should survive
    assert "def keep" in content
    # 🚫 both excluded files should be missing
    assert "def ignore_tmp" not in content
    assert "def ignore_log" not in content

    assert "stitch completed" in out
    assert "✅ stitch completed" in out
