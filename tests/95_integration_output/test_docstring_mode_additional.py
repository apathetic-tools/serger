# tests/95_integration_output/test_docstring_mode_additional.py

"""Additional integration tests for docstring_mode.

These tests verify compilation and execution of the output.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import serger.meta as mod_meta
from tests.utils.buildconfig import make_build_input, make_config_content


def test_docstring_mode_strip_with_classes() -> None:
    """Test 'strip' mode with classes/methods; verify output is executable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        src_dir = tmp_path / "src" / "testpkg"
        src_dir.mkdir(parents=True)
        out_dir = tmp_path / "dist"
        out_dir.mkdir()

        # Create source file with classes and methods
        (src_dir / "__init__.py").write_text("")
        (src_dir / "calculator.py").write_text(
            '''"""Calculator module."""
class Calculator:
    """A simple calculator class."""
    def add(self, a, b):
        """Add two numbers."""
        return a + b

    def multiply(self, a, b):
        """Multiply two numbers."""
        return a * b
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
        assert '"""Calculator module."""' not in output_content
        assert '"""A simple calculator class."""' not in output_content
        assert '"""Add two numbers."""' not in output_content
        assert '"""Multiply two numbers."""' not in output_content

        # Verify the file compiles and can be imported/used
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-c",
                f"import sys; sys.path.insert(0, '{out_dir}'); "
                "from output import Calculator; "
                "calc = Calculator(); "
                "assert calc.add(2, 3) == 5; "
                "assert calc.multiply(4, 5) == 20; "
                "print('OK')",
            ],
            capture_output=True,
            text=True,
            check=True,
            env=os.environ.copy(),
        )
        assert result.stdout.strip() == "OK"


def test_docstring_mode_public_complex() -> None:
    """Test 'public' mode with complex structure, verify output is executable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        src_dir = tmp_path / "src" / "testpkg"
        src_dir.mkdir(parents=True)
        out_dir = tmp_path / "dist"
        out_dir.mkdir()

        # Create source file with public and private functions/classes
        (src_dir / "__init__.py").write_text("")
        (src_dir / "api.py").write_text(
            '''"""Public API module."""
def public_function():
    """Public function that does something."""
    return _private_helper()

def _private_helper():
    """Private helper function."""
    return 42

class PublicClass:
    """Public class for users."""
    def public_method(self):
        """Public method."""
        return self._private_method()

    def _private_method(self):
        """Private method."""
        return 100

class _InternalClass:
    """Internal class, not for users."""
    def method(self):
        """Method in internal class."""
        return 200
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
        assert '"""Public API module."""' in output_content
        assert '"""Public function that does something."""' in output_content
        assert '"""Private helper function."""' not in output_content
        assert '"""Public class for users."""' in output_content
        assert '"""Public method."""' in output_content
        assert '"""Private method."""' not in output_content
        assert '"""Internal class, not for users."""' not in output_content

        # Verify the file compiles and executes correctly
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-c",
                f"import sys; sys.path.insert(0, '{out_dir}'); "
                "from output import public_function, PublicClass; "
                "assert public_function() == 42; "
                "obj = PublicClass(); "
                "assert obj.public_method() == 100; "
                "print('OK')",
            ],
            capture_output=True,
            text=True,
            check=True,
            env=os.environ.copy(),
        )
        assert result.stdout.strip() == "OK"
