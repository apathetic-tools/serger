# tests/90_integration/test_comments_mode.py

"""Integration tests for comments_mode setting."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import serger.meta as mod_meta
from tests.utils.buildconfig import make_build_input, make_config_content


def test_comments_mode_keep() -> None:
    """Test that 'keep' mode preserves all comments in stitched output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        src_dir = tmp_path / "src" / "testpkg"
        src_dir.mkdir(parents=True)
        out_dir = tmp_path / "dist"
        out_dir.mkdir()

        # Create source file with various comments
        (src_dir / "__init__.py").write_text("")
        (src_dir / "module.py").write_text(
            """# This is a standalone comment
def func():
    # This is another comment
    return 42  # This is an inline comment
"""
        )

        config_content = make_config_content(
            builds=make_build_input(
                include=[str(src_dir / "**/*.py")],
                out=str(out_dir / "output.py"),
                package="testpkg",
                comments_mode="keep",
            )
        )

        config_path = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
        config_path.write_text(config_content)

        # Run serger
        env = os.environ.copy()
        env["LOG_LEVEL"] = "test"
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-m",
                mod_meta.PROGRAM_PACKAGE,
                "--config",
                str(config_path),
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        # Print stderr if it contains trace output (for debugging)
        if result.stderr and (
            "TRACE" in result.stderr or "Processing comments" in result.stderr
        ):
            print(f"\nSubprocess stderr:\n{result.stderr}\n", file=sys.stderr)

        # Check output file exists
        output_file = out_dir / "output.py"
        assert output_file.exists()

        # Check that comments are preserved
        output_content = output_file.read_text()
        assert "# This is a standalone comment" in output_content
        assert "# This is another comment" in output_content
        assert "# This is an inline comment" in output_content

        # Verify the file executes correctly
        subprocess.run(  # noqa: S603
            [sys.executable, str(output_file)],
            capture_output=True,
            text=True,
            check=True,
            env=os.environ.copy(),
        )


def test_comments_mode_strip() -> None:
    """Test that 'strip' mode removes all comments but preserves docstrings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        src_dir = tmp_path / "src" / "testpkg"
        src_dir.mkdir(parents=True)
        out_dir = tmp_path / "dist"
        out_dir.mkdir()

        # Create source file with comments and docstrings
        (src_dir / "__init__.py").write_text("")
        (src_dir / "module.py").write_text(
            """# This comment should be removed
def func():
    \"\"\"This docstring should be kept.\"\"\"
    # This comment should be removed
    return 42  # This comment should be removed
"""
        )

        config_content = make_config_content(
            builds=make_build_input(
                include=[str(src_dir / "**/*.py")],
                out=str(out_dir / "output.py"),
                package="testpkg",
                comments_mode="strip",
            )
        )

        config_path = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
        config_path.write_text(config_content)

        # Run serger
        env = os.environ.copy()
        env["LOG_LEVEL"] = "test"
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-m",
                mod_meta.PROGRAM_PACKAGE,
                "--config",
                str(config_path),
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        # Print stderr if it contains trace output (for debugging)
        if result.stderr and (
            "TRACE" in result.stderr or "Processing comments" in result.stderr
        ):
            print(f"\nSubprocess stderr:\n{result.stderr}\n", file=sys.stderr)

        # Check output file exists
        output_file = out_dir / "output.py"
        assert output_file.exists()

        # Check that comments are removed but docstrings are preserved
        output_content = output_file.read_text()
        assert "# This comment should be removed" not in output_content
        assert '"""This docstring should be kept."""' in output_content

        # Verify the file executes correctly
        subprocess.run(  # noqa: S603
            [sys.executable, str(output_file)],
            capture_output=True,
            text=True,
            check=True,
            env=os.environ.copy(),
        )


def test_comments_mode_ignores() -> None:
    """Test that 'ignores' mode keeps only ignore comments."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        src_dir = tmp_path / "src" / "testpkg"
        src_dir.mkdir(parents=True)
        out_dir = tmp_path / "dist"
        out_dir.mkdir()

        # Create source file with various comments
        (src_dir / "__init__.py").write_text("")
        (src_dir / "module.py").write_text(
            """# This comment should be removed
def func():
    x = 1  # noqa: F401
    y = 2  # This comment should be removed
    return x + y  # type: ignore[assignment]
"""
        )

        config_content = make_config_content(
            builds=make_build_input(
                include=[str(src_dir / "**/*.py")],
                out=str(out_dir / "output.py"),
                package="testpkg",
                comments_mode="ignores",
            )
        )

        config_path = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
        config_path.write_text(config_content)

        # Run serger
        env = os.environ.copy()
        env["LOG_LEVEL"] = "test"
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-m",
                mod_meta.PROGRAM_PACKAGE,
                "--config",
                str(config_path),
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        # Print stderr if it contains trace output (for debugging)
        if result.stderr and (
            "TRACE" in result.stderr or "Processing comments" in result.stderr
        ):
            print(f"\nSubprocess stderr:\n{result.stderr}\n", file=sys.stderr)

        # Check output file exists
        output_file = out_dir / "output.py"
        assert output_file.exists()

        # Check that only ignore comments are kept
        output_content = output_file.read_text()
        assert "# This comment should be removed" not in output_content
        assert "# noqa: F401" in output_content
        assert "# This comment should be removed" not in output_content
        assert "# type: ignore[assignment]" in output_content

        # Verify the file executes correctly
        subprocess.run(  # noqa: S603
            [sys.executable, str(output_file)],
            capture_output=True,
            text=True,
            check=True,
            env=os.environ.copy(),
        )


def test_comments_mode_inline() -> None:
    """Test that 'inline' mode keeps only inline comments."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        src_dir = tmp_path / "src" / "testpkg"
        src_dir.mkdir(parents=True)
        out_dir = tmp_path / "dist"
        out_dir.mkdir()

        # Create source file with various comments
        (src_dir / "__init__.py").write_text("")
        (src_dir / "module.py").write_text(
            """# This standalone comment should be removed
def func():
    # This standalone comment should be removed
    return 42  # This inline comment should be kept
"""
        )

        config_content = make_config_content(
            builds=make_build_input(
                include=[str(src_dir / "**/*.py")],
                out=str(out_dir / "output.py"),
                package="testpkg",
                comments_mode="inline",
            )
        )

        config_path = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
        config_path.write_text(config_content)

        # Run serger
        env = os.environ.copy()
        env["LOG_LEVEL"] = "test"
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-m",
                mod_meta.PROGRAM_PACKAGE,
                "--config",
                str(config_path),
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        # Print stderr if it contains trace output (for debugging)
        if result.stderr and (
            "TRACE" in result.stderr or "Processing comments" in result.stderr
        ):
            print(f"\nSubprocess stderr:\n{result.stderr}\n", file=sys.stderr)

        # Check output file exists
        output_file = out_dir / "output.py"
        assert output_file.exists()

        # Check that only inline comments are kept
        output_content = output_file.read_text()
        assert "# This standalone comment should be removed" not in output_content
        assert "# This inline comment should be kept" in output_content

        # Verify the file executes correctly
        subprocess.run(  # noqa: S603
            [sys.executable, str(output_file)],
            capture_output=True,
            text=True,
            check=True,
            env=os.environ.copy(),
        )
