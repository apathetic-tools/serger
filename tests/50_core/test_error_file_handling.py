# tests/50_core/test_error_file_handling.py
"""Tests for error file writing and cleanup functions."""

import contextlib
import datetime
from pathlib import Path

import pytest

import serger.verify_script as mod_verify


def test_write_error_file_creates_file_with_header(tmp_path: Path) -> None:
    """Should create error file with troubleshooting header."""
    out_path = tmp_path / "package.py"
    source_code = "def hello(\n    return 'world'\n"  # Invalid syntax
    error = SyntaxError("invalid syntax", ("<string>", 1, 5, "def hello("))

    error_path = mod_verify._write_error_file(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        out_path, source_code, error
    )

    assert error_path.exists()
    assert error_path.name.startswith("package_ERROR_")
    assert error_path.name.endswith(".py")

    content = error_path.read_text(encoding="utf-8")
    assert "COMPILATION ERROR - TROUBLESHOOTING FILE" in content
    assert "Error Details:" in content
    assert "Troubleshooting:" in content
    assert "def hello(" in content  # Original source code


def test_write_error_file_includes_error_details(tmp_path: Path) -> None:
    """Should include error details in header."""
    out_path = tmp_path / "mypkg.py"
    source_code = "x = 1\ninvalid\n"
    error = SyntaxError("invalid syntax", ("<string>", 2, 1, "invalid"))

    error_path = mod_verify._write_error_file(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        out_path, source_code, error
    )

    content = error_path.read_text(encoding="utf-8")
    assert "Type: SyntaxError" in content
    assert "Line: 2" in content
    assert "invalid syntax" in content
    assert str(out_path) in content


def test_write_error_file_uses_date_suffix(tmp_path: Path) -> None:
    """Should use date suffix in filename."""
    out_path = tmp_path / "testpkg.py"
    source_code = "invalid\n"
    error = SyntaxError("invalid syntax", ("<string>", 1, 1, "invalid"))

    error_path = mod_verify._write_error_file(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        out_path, source_code, error
    )

    now = datetime.datetime.now(datetime.timezone.utc)
    expected_suffix = now.strftime("%Y_%m_%d")
    assert f"_ERROR_{expected_suffix}.py" in error_path.name


def test_write_error_file_deletes_pre_existing_error_files(tmp_path: Path) -> None:
    """Should delete pre-existing error files before writing new one."""
    out_path = tmp_path / "mypkg.py"

    # Create old error files
    old_error1 = tmp_path / "mypkg_ERROR_2024_01_01.py"
    old_error1.write_text("old error 1")
    old_error2 = tmp_path / "mypkg_ERROR_2024_01_02.py"
    old_error2.write_text("old error 2")

    source_code = "invalid\n"
    error = SyntaxError("invalid syntax", ("<string>", 1, 1, "invalid"))

    error_path = mod_verify._write_error_file(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        out_path, source_code, error
    )

    # New error file should exist
    assert error_path.exists()

    # Old error files should be deleted
    assert not old_error1.exists()
    assert not old_error2.exists()


def test_write_error_file_does_not_delete_new_file(tmp_path: Path) -> None:
    """Should not delete the file we just wrote, even if it matches pattern."""
    out_path = tmp_path / "testpkg.py"

    # Create error file with today's date (will match pattern)
    now = datetime.datetime.now(datetime.timezone.utc)
    date_suffix = now.strftime("%Y_%m_%d")
    existing_today = tmp_path / f"testpkg_ERROR_{date_suffix}.py"
    existing_today.write_text("existing today")

    source_code = "invalid\n"
    error = SyntaxError("invalid syntax", ("<string>", 1, 1, "invalid"))

    error_path = mod_verify._write_error_file(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        out_path, source_code, error
    )

    # New error file should exist with new content
    assert error_path.exists()
    assert error_path == existing_today  # Same file
    content = error_path.read_text(encoding="utf-8")
    assert "COMPILATION ERROR" in content  # New content, not "existing today"


def test_cleanup_error_files_deletes_matching_files(tmp_path: Path) -> None:
    """Should delete all error files matching the pattern."""
    out_path = tmp_path / "mypkg.py"

    # Create multiple error files
    error1 = tmp_path / "mypkg_ERROR_2024_01_01.py"
    error1.write_text("error 1")
    error2 = tmp_path / "mypkg_ERROR_2024_01_02.py"
    error2.write_text("error 2")
    error3 = tmp_path / "mypkg_ERROR_2024_01_03.py"
    error3.write_text("error 3")

    # Create non-matching file (should not be deleted)
    other_file = tmp_path / "otherpkg_ERROR_2024_01_01.py"
    other_file.write_text("other error")

    mod_verify._cleanup_error_files(out_path)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # Matching error files should be deleted
    assert not error1.exists()
    assert not error2.exists()
    assert not error3.exists()

    # Non-matching file should still exist
    assert other_file.exists()


def test_cleanup_error_files_handles_no_files(tmp_path: Path) -> None:
    """Should handle case where no error files exist."""
    out_path = tmp_path / "mypkg.py"

    # Should not raise
    mod_verify._cleanup_error_files(out_path)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]


def test_cleanup_error_files_handles_permission_errors(tmp_path: Path) -> None:
    """Should handle permission errors gracefully when deleting files."""
    out_path = tmp_path / "mypkg.py"

    # Create error file
    error_file = tmp_path / "mypkg_ERROR_2024_01_01.py"
    error_file.write_text("error")

    # Make file read-only (on Unix-like systems)
    try:
        error_file.chmod(0o444)
        # Should not raise, should log and continue
        mod_verify._cleanup_error_files(out_path)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    except (OSError, PermissionError):
        # On Windows or if chmod fails, just skip this test
        pytest.skip("Cannot set file permissions on this system")
    finally:
        # Restore permissions for cleanup
        with contextlib.suppress(OSError):
            error_file.chmod(0o644)
