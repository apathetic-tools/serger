# tests/95_integration_output/test_docstring_mode.py

"""Integration tests for docstring_mode setting."""

import os
import subprocess
import sys
from pathlib import Path

import serger.meta as mod_meta
from tests.utils.buildconfig import make_build_input, make_config_content


def test_docstring_mode_keep(tmp_path: Path) -> None:
    """Test that 'keep' mode preserves all docstrings in stitched output."""
    src_dir = tmp_path / "src" / "testpkg"
    src_dir.mkdir(parents=True)
    out_dir = tmp_path / "dist"
    out_dir.mkdir()

    # Create source file with various docstrings
    (src_dir / "__init__.py").write_text("")
    (src_dir / "module.py").write_text(
        '''"""Module docstring."""
def func():
    """Function docstring."""
    return 42
'''
    )

    config_content = make_config_content(
        builds=make_build_input(
            include=[str(src_dir / "**/*.py")],
            out=str(out_dir / "output.py"),
            package="testpkg",
            docstring_mode="keep",
        )
    )

    config_path = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config_path.write_text(config_content)

    # Run serger
    env = os.environ.copy()
    env["LOG_LEVEL"] = "test"
    subprocess.run(  # noqa: S603
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

    # Check output file exists
    output_file = out_dir / "output.py"
    assert output_file.exists()

    # Check that docstrings are preserved
    output_content = output_file.read_text()
    assert '"""Module docstring."""' in output_content
    assert '"""Function docstring."""' in output_content

    # Verify the file executes correctly
    subprocess.run(  # noqa: S603
        [sys.executable, str(output_file)],
        capture_output=True,
        text=True,
        check=True,
        env=os.environ.copy(),
    )


def test_docstring_mode_strip(tmp_path: Path) -> None:
    """Test that 'strip' mode removes all docstrings."""
    src_dir = tmp_path / "src" / "testpkg"
    src_dir.mkdir(parents=True)
    out_dir = tmp_path / "dist"
    out_dir.mkdir()

    # Create source file with docstrings
    (src_dir / "__init__.py").write_text("")
    (src_dir / "module.py").write_text(
        '''"""Module docstring."""
def func():
    """Function docstring."""
    return 42
'''
    )

    config_content = make_config_content(
        builds=make_build_input(
            include=[str(src_dir / "**/*.py")],
            out=str(out_dir / "output.py"),
            package="testpkg",
            docstring_mode="strip",
        )
    )

    config_path = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config_path.write_text(config_content)

    # Run serger
    env = os.environ.copy()
    env["LOG_LEVEL"] = "test"
    subprocess.run(  # noqa: S603
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

    # Check output file exists
    output_file = out_dir / "output.py"
    assert output_file.exists()

    # Check that docstrings are removed
    output_content = output_file.read_text()
    assert '"""Module docstring."""' not in output_content
    assert '"""Function docstring."""' not in output_content

    # Verify the file executes correctly
    subprocess.run(  # noqa: S603
        [sys.executable, str(output_file)],
        capture_output=True,
        text=True,
        check=True,
        env=os.environ.copy(),
    )


def test_docstring_mode_public(tmp_path: Path) -> None:
    """Test that 'public' mode keeps only public docstrings."""
    src_dir = tmp_path / "src" / "testpkg"
    src_dir.mkdir(parents=True)
    out_dir = tmp_path / "dist"
    out_dir.mkdir()

    # Create source file with public and private functions
    (src_dir / "__init__.py").write_text("")
    (src_dir / "module.py").write_text(
        '''"""Module docstring."""
def public_func():
    """Public function docstring."""
    return 42

def _private_func():
    """Private function docstring."""
    return 43
'''
    )

    config_content = make_config_content(
        builds=make_build_input(
            include=[str(src_dir / "**/*.py")],
            out=str(out_dir / "output.py"),
            package="testpkg",
            docstring_mode="public",
        )
    )

    config_path = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config_path.write_text(config_content)

    # Run serger
    env = os.environ.copy()
    env["LOG_LEVEL"] = "test"
    subprocess.run(  # noqa: S603
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

    # Check output file exists
    output_file = out_dir / "output.py"
    assert output_file.exists()

    # Check that only public docstrings are kept
    output_content = output_file.read_text()
    assert '"""Public function docstring."""' in output_content
    assert '"""Private function docstring."""' not in output_content

    # Verify the file executes correctly
    subprocess.run(  # noqa: S603
        [sys.executable, str(output_file)],
        capture_output=True,
        text=True,
        check=True,
        env=os.environ.copy(),
    )


def test_docstring_mode_dict(tmp_path: Path) -> None:
    """Test that dict mode allows per-location control."""
    src_dir = tmp_path / "src" / "testpkg"
    src_dir.mkdir(parents=True)
    out_dir = tmp_path / "dist"
    out_dir.mkdir()

    # Create source file with module, class, and function docstrings
    (src_dir / "__init__.py").write_text("")
    (src_dir / "module.py").write_text(
        '''"""Module docstring."""
class MyClass:
    """Class docstring."""
    def method(self):
        """Method docstring."""
        return 42

def func():
    """Function docstring."""
    return 43
'''
    )

    config_content = make_config_content(
        builds=make_build_input(
            include=[str(src_dir / "**/*.py")],
            out=str(out_dir / "output.py"),
            package="testpkg",
            docstring_mode={"module": "strip", "class": "keep"},
        )
    )

    config_path = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    config_path.write_text(config_content)

    # Run serger
    env = os.environ.copy()
    env["LOG_LEVEL"] = "test"
    subprocess.run(  # noqa: S603
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

    # Check output file exists
    output_file = out_dir / "output.py"
    assert output_file.exists()

    # Check that module docstring is removed but class is kept
    output_content = output_file.read_text()
    assert '"""Module docstring."""' not in output_content
    assert '"""Class docstring."""' in output_content
    # Function should default to keep
    assert '"""Function docstring."""' in output_content

    # Verify the file executes correctly
    subprocess.run(  # noqa: S603
        [sys.executable, str(output_file)],
        capture_output=True,
        text=True,
        check=True,
        env=os.environ.copy(),
    )
