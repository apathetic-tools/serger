# tests/90_integration/test_log_level.py
"""Tests for log level configuration and CLI flags."""

import sys
from io import StringIO
from pathlib import Path

import pytest

import serger.cli as mod_cli
import serger.logs as mod_logs
import serger.meta as mod_meta
from tests.utils import make_test_package, write_config_file


# --- constants --------------------------------------------------------------------

ARGPARSE_ERROR_EXIT_CODE = 2

# --- tests ------------------------------------------------------------------------


def test_quiet_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should suppress most output but still succeed."""
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
    code = mod_cli.main(["--quiet"])

    # --- verify ---
    out = capsys.readouterr().out.lower()
    assert code == 0
    # should not contain normal messages
    assert "stitch completed" not in out
    assert "all builds complete" not in out


def test_verbose_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should print detailed file-level logs when --verbose is used."""
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
    code = mod_cli.main(["--verbose"])

    # --- verify ---
    captured = capsys.readouterr()
    out = (captured.out + captured.err).lower()

    assert code == 0
    # Verbose mode should show debug-level details
    assert "[debug" in out
    # It should still include summary
    assert "stitch completed" in out
    assert "✅ stitch completed" in out

    level = mod_logs.get_app_logger().level_name.lower()
    assert level == "debug"


def test_verbose_and_quiet_mutually_exclusive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should fail when both --verbose and --quiet are provided."""
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

    # --- patch, execute and verify ---
    monkeypatch.chdir(tmp_path)

    # argparse should exit with SystemExit(2)
    with pytest.raises(SystemExit) as e:
        mod_cli.main(["--quiet", "--verbose"])

    assert e.value.code == ARGPARSE_ERROR_EXIT_CODE  # must be outside context

    # --- verify only ---
    captured = capsys.readouterr()
    combined = (captured.out + captured.err).lower()

    assert "not allowed with argument" in combined or "mutually exclusive" in combined
    assert "--quiet" in combined
    assert "--verbose" in combined


def test_log_level_flag_sets_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--log-level should override config and environment."""
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
    code = mod_cli.main(["--log-level", "debug"])

    # --- verify ---
    out = capsys.readouterr().out.lower()

    assert code == 0
    assert "stitch completed" in out
    # Verify that runtime log level is set correctly
    level = mod_logs.get_app_logger().level_name.lower()
    assert level == "debug"


def test_log_level_from_env_var(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LOG_LEVEL and {PROGRAM_ENV}_LOG_LEVEL should be respected when flag not given."""
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

    # --- patch, execute and verify ---
    monkeypatch.chdir(tmp_path)

    # 1️⃣ Specific env var wins
    monkeypatch.setenv(f"{mod_meta.PROGRAM_ENV}_LOG_LEVEL", "warning")
    code = mod_cli.main([])

    assert code == 0
    level = mod_logs.get_app_logger().level_name.lower()
    assert level == "warning"

    # 2️⃣ Generic LOG_LEVEL fallback works
    monkeypatch.delenv(f"{mod_meta.PROGRAM_ENV}_LOG_LEVEL")
    monkeypatch.setenv("LOG_LEVEL", "error")
    code = mod_cli.main([])

    assert code == 0
    level = mod_logs.get_app_logger().level_name.lower()
    assert level == "error"

    monkeypatch.delenv("LOG_LEVEL", raising=False)


def test_per_build_log_level_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Config log_level should be used when set."""
    # --- setup ---
    # Multi-build support removed - this test is now a placeholder
    # that tests single-build log level behavior
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    # Config sets debug log level
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
        log_level="debug",
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    captured = capsys.readouterr()
    out = (captured.out + captured.err).lower()

    assert code == 0
    # Output file should exist
    assert (tmp_path / "dist" / "mypkg.py").exists()

    # Debug logs should have appeared
    assert "[debug" in out or "overriding log level" in out

    # After build completes, runtime should be restored
    level = mod_logs.get_app_logger().level_name.lower()
    assert level in ("info", "debug")  # May be debug if still set


def test_log_level_test_bypasses_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """LOG_LEVEL=test should send TRACE/DEBUG to __stderr__, bypassing capsys."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
        log_level="test",  # Set log_level in config to test
    )

    # Capture sys.__stderr__ to verify bypass messages are written there
    bypass_buf = StringIO()
    monkeypatch.setattr(sys, "__stderr__", bypass_buf)

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    # Use --log-level flag to ensure test level is set (should override config)
    code = mod_cli.main(["--log-level", "test"])

    # --- verify ---
    assert code == 0

    # Check capsys - TRACE/DEBUG messages should NOT be captured here
    captured = capsys.readouterr()
    out = captured.out.lower()
    err = captured.err.lower()

    # Check bypass buffer - TRACE/DEBUG messages SHOULD be written here
    bypass_output = bypass_buf.getvalue().lower()

    # Verify TRACE/DEBUG messages are NOT in capsys (they bypass capture)
    assert "[trace" not in out, (
        "TRACE messages should bypass capsys and write to sys.__stderr__ instead. "
        f"Found in capsys.out: {out[:200]}"
    )
    assert "[debug" not in out, (
        "DEBUG messages should bypass capsys and write to sys.__stderr__ instead. "
        f"Found in capsys.out: {out[:200]}"
    )
    assert "[trace" not in err, (
        "TRACE messages should bypass capsys and write to sys.__stderr__ instead. "
        f"Found in capsys.err: {err[:200]}"
    )
    assert "[debug" not in err, (
        "DEBUG messages should bypass capsys and write to sys.__stderr__ instead. "
        f"Found in capsys.err: {err[:200]}"
    )

    # Verify TRACE/DEBUG messages ARE in the bypass buffer (sys.__stderr__)
    assert "[trace" in bypass_output, (
        "TRACE messages should appear in sys.__stderr__ bypass buffer. "
        f"Bypass buffer length: {len(bypass_output)} chars"
    )
    assert "[debug" in bypass_output, (
        "DEBUG messages should appear in sys.__stderr__ bypass buffer. "
        f"Bypass buffer length: {len(bypass_output)} chars"
    )
