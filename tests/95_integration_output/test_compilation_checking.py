# tests/95_integration_output/test_compilation_checking.py
"""Integration tests for in-memory compilation checking and error file handling."""

import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

import serger.build as mod_build
import serger.config.config_types as mod_config_types
import serger.stitch as mod_stitch
import serger.verify_script as mod_verify
from tests.utils import is_serger_build_for_test
from tests.utils.buildconfig import make_include_resolved


def test_stitch_modules_compiles_in_memory_before_writing(tmp_path: Path) -> None:
    """Should compile code in-memory before writing to disk."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    out_path = tmp_path / "output.py"

    # Create valid source files
    (src_dir / "a.py").write_text("A = 1\n")
    (src_dir / "b.py").write_text("B = A + 1\n")

    # Set up test similar to _setup_stitch_test
    file_paths = [(src_dir / f"{name}.py").resolve() for name in ["a", "b"]]
    package_root = mod_build.find_package_root(file_paths)
    file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
    include = make_include_resolved(str(src_dir.name), src_dir.parent)
    for file_path in file_paths:
        file_to_include[file_path] = include

    config: dict[str, object] = {
        "package": "testpkg",
        "order": file_paths,  # Order as Path objects
        "exclude_names": [],
        "stitch_mode": "raw",
    }

    # Track if verify_compiles_string was called
    verify_called = False
    original_verify = mod_verify.verify_compiles_string

    def mock_verify_compiles_string(source: str, filename: str = "<string>") -> None:
        nonlocal verify_called
        verify_called = True
        # Call original function (not through mod_verify to avoid recursion)
        original_verify(source, filename)

    with patch.object(
        mod_stitch,
        "verify_compiles_string",
        side_effect=mock_verify_compiles_string,
    ):
        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

    assert verify_called, "verify_compiles_string should have been called"
    assert out_path.exists(), "Output file should exist after successful compilation"


def test_stitch_modules_writes_error_file_on_compilation_failure(
    tmp_path: Path,
) -> None:
    """Should write error file when compilation fails, then raise RuntimeError."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    out_path = tmp_path / "output.py"

    # Create valid source files
    (src_dir / "a.py").write_text("A = 1\n")
    (src_dir / "b.py").write_text("B = A + 1\n")

    # Set up test similar to _setup_stitch_test
    file_paths = [(src_dir / f"{name}.py").resolve() for name in ["a", "b"]]
    package_root = mod_build.find_package_root(file_paths)
    file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
    include = make_include_resolved(str(src_dir.name), src_dir.parent)
    for file_path in file_paths:
        file_to_include[file_path] = include

    config: dict[str, object] = {
        "package": "testpkg",
        "order": file_paths,  # Order as Path objects
        "exclude_names": [],
        "stitch_mode": "raw",
    }

    # Mock verify_compiles_string to raise SyntaxError
    error_msg = "invalid syntax"
    error_tuple = ("<string>", 42, 1, "invalid")

    def mock_verify_compiles_string(source: str, filename: str = "<string>") -> None:
        # Accept both positional and keyword args
        _ = source, filename  # Unused but needed for signature
        raise SyntaxError(error_msg, error_tuple)

    with (
        patch.object(
            mod_stitch,
            "verify_compiles_string",
            side_effect=mock_verify_compiles_string,
        ),
        pytest.raises(RuntimeError) as exc_info,
    ):
        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

    # Should raise with error details
    assert "syntax errors" in str(exc_info.value).lower()
    assert "Error file written to" in str(exc_info.value)

    # Error file should exist
    pattern = "output_ERROR_*.py"
    error_files = list(tmp_path.glob(pattern))
    assert len(error_files) == 1, f"Expected 1 error file, found {error_files}"
    error_file = error_files[0]

    # Error file should have troubleshooting header
    content = error_file.read_text(encoding="utf-8")
    assert "COMPILATION ERROR" in content
    assert "Troubleshooting:" in content

    # Output file should NOT exist (compilation failed)
    assert not out_path.exists()


def test_stitch_modules_cleans_up_error_files_on_success(tmp_path: Path) -> None:
    """Should delete old error files when build succeeds."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    out_path = tmp_path / "output.py"

    # Create old error files
    old_error1 = tmp_path / "output_ERROR_2024_01_01.py"
    old_error1.write_text("old error 1")
    old_error2 = tmp_path / "output_ERROR_2024_01_02.py"
    old_error2.write_text("old error 2")

    # Create valid source files
    (src_dir / "a.py").write_text("A = 1\n")
    (src_dir / "b.py").write_text("B = A + 1\n")

    # Set up test similar to _setup_stitch_test
    file_paths = [(src_dir / f"{name}.py").resolve() for name in ["a", "b"]]
    package_root = mod_build.find_package_root(file_paths)
    file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
    include = make_include_resolved(str(src_dir.name), src_dir.parent)
    for file_path in file_paths:
        file_to_include[file_path] = include

    config: dict[str, object] = {
        "package": "testpkg",
        "order": file_paths,  # Order as Path objects
        "exclude_names": [],
        "stitch_mode": "raw",
    }

    mod_stitch.stitch_modules(
        config=config,
        file_paths=file_paths,
        package_root=package_root,
        file_to_include=file_to_include,
        out_path=out_path,
        is_serger_build=is_serger_build_for_test(out_path),
    )

    # Old error files should be deleted
    assert not old_error1.exists()
    assert not old_error2.exists()

    # Output file should exist
    assert out_path.exists()


def test_stitch_modules_handles_actual_compilation_failure(tmp_path: Path) -> None:
    """Should handle real compilation failure from invalid stitched code."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    out_path = tmp_path / "output.py"

    # Create source file with syntax that might cause issues when stitched
    # We'll inject invalid code during stitching by mocking the final script
    (src_dir / "a.py").write_text("A = 1\n")
    (src_dir / "b.py").write_text("B = A + 1\n")

    # Set up test similar to _setup_stitch_test
    file_paths = [(src_dir / f"{name}.py").resolve() for name in ["a", "b"]]
    package_root = mod_build.find_package_root(file_paths)
    file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
    include = make_include_resolved(str(src_dir.name), src_dir.parent)
    for file_path in file_paths:
        file_to_include[file_path] = include

    config: dict[str, object] = {
        "package": "testpkg",
        "order": file_paths,  # Order as Path objects
        "exclude_names": [],
        "stitch_mode": "raw",
    }

    # Mock _build_final_script to return invalid code
    def mock_build_final_script(
        *_args: object, **_kwargs: object
    ) -> tuple[str, set[str]]:
        # Return code with syntax error
        invalid_code = "def hello(\n    return 'world'\n"  # Missing paren
        return (invalid_code, set())

    with (
        patch.object(
            mod_stitch,
            "_build_final_script",
            side_effect=mock_build_final_script,
        ),
        pytest.raises(RuntimeError) as exc_info,
    ):
        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

    # Should raise with error details
    assert "syntax errors" in str(exc_info.value).lower()

    # Error file should exist
    pattern = "output_ERROR_*.py"
    error_files = list(tmp_path.glob(pattern))
    assert len(error_files) == 1
    error_file = error_files[0]

    # Error file should contain the invalid code
    content = error_file.read_text(encoding="utf-8")
    assert "def hello(" in content
    assert "COMPILATION ERROR" in content

    # Output file should NOT exist
    assert not out_path.exists()


def test_stitch_modules_error_file_has_correct_date_format(tmp_path: Path) -> None:
    """Should use correct date format in error file name."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    out_path = tmp_path / "mypkg.py"

    (src_dir / "a.py").write_text("A = 1\n")

    # Set up test similar to _setup_stitch_test
    file_paths = [(src_dir / "a.py").resolve()]
    package_root = mod_build.find_package_root(file_paths)
    file_to_include: dict[Path, mod_config_types.IncludeResolved] = {}
    include = make_include_resolved(str(src_dir.name), src_dir.parent)
    for file_path in file_paths:
        file_to_include[file_path] = include

    config: dict[str, object] = {
        "package": "testpkg",
        "order": file_paths,  # Order as Path objects
        "exclude_names": [],
        "stitch_mode": "raw",
    }

    # Mock to fail compilation
    error_msg = "invalid syntax"
    error_tuple = ("<string>", 1, 1, "invalid")

    def mock_verify_compiles_string(source: str, filename: str = "<string>") -> None:
        # Accept both positional and keyword args
        _ = source, filename  # Unused but needed for signature
        raise SyntaxError(error_msg, error_tuple)

    with (
        patch.object(
            mod_stitch,
            "verify_compiles_string",
            side_effect=mock_verify_compiles_string,
        ),
        pytest.raises(RuntimeError),
    ):
        mod_stitch.stitch_modules(
            config=config,
            file_paths=file_paths,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            is_serger_build=is_serger_build_for_test(out_path),
        )

    # Check error file name format
    now = datetime.datetime.now(datetime.timezone.utc)
    expected_date = now.strftime("%Y_%m_%d")
    pattern = f"mypkg_ERROR_{expected_date}.py"
    error_files = list(tmp_path.glob(pattern))
    assert len(error_files) == 1, f"Expected error file with date {expected_date}"
