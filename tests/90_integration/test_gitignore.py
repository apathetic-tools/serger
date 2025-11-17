# tests/90_integration/test_gitignore.py
"""Tests for .gitignore handling and precedence in serger.cli."""

import shutil
from pathlib import Path

import pytest

import serger.cli as mod_cli
import serger.meta as mod_meta
from tests.utils import make_test_package, write_config_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def write_gitignore(tmp_path: Path, patterns: str) -> Path:
    """Helper to write a .gitignore file."""
    path = tmp_path / ".gitignore"
    path.write_text(patterns)
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_default_respects_gitignore(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """By default, .gitignore patterns are respected."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)
    # Add files: one should be excluded by gitignore, one should be kept
    (pkg_dir / "skip_tmp.py").write_text('def skip():\n    return "skip"\n')
    (pkg_dir / "keep.py").write_text('def keep():\n    return "ok"\n')

    write_gitignore(tmp_path, "*_tmp.py\n")
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
    stitched = tmp_path / "dist" / "mypkg.py"

    assert code == 0
    assert stitched.exists()
    stitched_content = stitched.read_text()
    # keep.py should be included
    assert "def keep()" in stitched_content
    # skip_tmp.py should be excluded by gitignore
    assert "def skip()" not in stitched_content
    assert "stitch completed" in out
    assert "✅ stitch completed" in out


def test_config_disables_gitignore(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Root config can globally disable .gitignore."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)
    # Add a Python file that matches gitignore pattern
    (pkg_dir / "test_tmp.py").write_text('def test():\n    return "test"\n')

    write_gitignore(tmp_path, "*_tmp.py\n")

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
        respect_gitignore=False,
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    out = capsys.readouterr().out.lower()
    stitched = tmp_path / "dist" / "mypkg.py"

    assert code == 0
    assert stitched.exists()
    # test_tmp.py should be included since gitignore is disabled
    stitched_content = stitched.read_text()
    assert "def test()" in stitched_content or "test_tmp" in stitched_content
    assert "stitch completed" in out
    assert "✅ stitch completed" in out


def test_build_enables_gitignore_even_if_root_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A specific build can override root and re-enable .gitignore."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)
    # Add files: one should be excluded, one should be kept
    (pkg_dir / "skip_tmp.py").write_text('def skip():\n    return "skip"\n')
    (pkg_dir / "keep.py").write_text('def keep():\n    return "keep"\n')

    write_gitignore(tmp_path, "*_tmp.py\n")

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
        respect_gitignore=True,
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    out = capsys.readouterr().out.lower()
    stitched = tmp_path / "dist" / "mypkg.py"

    assert code == 0
    assert stitched.exists()
    stitched_content = stitched.read_text()
    # keep.py should be included
    assert "def keep()" in stitched_content
    # skip_tmp.py should be excluded by gitignore (even though root disables it)
    assert "def skip()" not in stitched_content
    assert "stitch completed" in out
    assert "✅ stitch completed" in out


def test_cli_disables_gitignore_even_if_enabled_in_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--no-gitignore should always take precedence over config."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)
    # Add a file that matches gitignore pattern
    (pkg_dir / "ignore_tmp.py").write_text('def ignore():\n    return "ignore"\n')
    (pkg_dir / "keep.py").write_text('def keep():\n    return "keep"\n')

    write_gitignore(tmp_path, "*_tmp.py\n")
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--no-gitignore"])

    # --- verify ---
    out = capsys.readouterr().out.lower()
    stitched = tmp_path / "dist" / "mypkg.py"

    assert code == 0
    assert stitched.exists()
    stitched_content = stitched.read_text()
    # Both files should be included since --no-gitignore was used
    assert "def keep()" in stitched_content
    assert "def ignore()" in stitched_content
    assert "stitch completed" in out
    assert "✅ stitch completed" in out


def test_cli_enables_gitignore_even_if_config_disables_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--gitignore should re-enable even if config disables it."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)
    # Add files: one should be excluded, one should be kept
    (pkg_dir / "skip_tmp.py").write_text('def skip():\n    return "skip"\n')
    (pkg_dir / "keep.py").write_text('def keep():\n    return "keep"\n')

    write_gitignore(tmp_path, "*_tmp.py\n")

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
        respect_gitignore=False,
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--gitignore"])

    # --- verify ---
    out = capsys.readouterr().out.lower()
    stitched = tmp_path / "dist" / "mypkg.py"

    assert code == 0
    assert stitched.exists()
    stitched_content = stitched.read_text()
    # keep.py should be included
    assert "def keep()" in stitched_content
    # skip_tmp.py should be excluded by gitignore (CLI overrides config)
    assert "def skip()" not in stitched_content
    assert "stitch completed" in out
    assert "✅ stitch completed" in out


def test_gitignore_patterns_append_to_existing_excludes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Patterns from .gitignore should merge with config exclude list."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)
    # Add files that should be excluded by different mechanisms
    (pkg_dir / "foo_tmp.py").write_text('def foo():\n    return "tmp"\n')
    (pkg_dir / "bar_log.py").write_text('def bar():\n    return "log"\n')
    (pkg_dir / "baz.py").write_text('def baz():\n    return "ok"\n')

    write_gitignore(tmp_path, "*_log.py\n")

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        exclude=["*_tmp.py"],
        out="dist/mypkg.py",
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    out = capsys.readouterr().out.lower()
    stitched = tmp_path / "dist" / "mypkg.py"

    assert code == 0
    assert stitched.exists()
    stitched_content = stitched.read_text()
    # foo_tmp.py excluded by config exclude
    assert "def foo()" not in stitched_content
    # bar_log.py excluded by gitignore
    assert "def bar()" not in stitched_content
    # baz.py should be included
    assert "def baz()" in stitched_content
    assert "stitch completed" in out
    assert "✅ stitch completed" in out


def test_cli_gitignore_disable_then_enable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that CLI flags can toggle gitignore behavior between runs."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)
    # Add a file that matches gitignore pattern
    (pkg_dir / "a_tmp.py").write_text('def a():\n    return "x"\n')
    (pkg_dir / "b.py").write_text('def b():\n    return "y"\n')
    write_gitignore(tmp_path, "*_tmp.py\n")
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
    )

    # --- patch, execute and verify ---
    monkeypatch.chdir(tmp_path)
    # First run with --no-gitignore: a_tmp.py should be included
    mod_cli.main(["--no-gitignore"])
    stitched1 = tmp_path / "dist" / "mypkg.py"
    assert stitched1.exists()
    content1 = stitched1.read_text()
    assert "def a()" in content1

    # Clean up and run again with --gitignore: a_tmp.py should be excluded
    shutil.rmtree(tmp_path / "dist")
    mod_cli.main(["--gitignore"])
    stitched2 = tmp_path / "dist" / "mypkg.py"
    assert stitched2.exists()
    content2 = stitched2.read_text()
    assert "def a()" not in content2
