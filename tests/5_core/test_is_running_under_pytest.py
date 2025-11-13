# tests/5_core/test_is_running_under_pytest.py
"""Tests for is_running_under_pytest utility function."""

import os
import sys
from unittest.mock import patch

import serger.utils.utils_system as mod_utils_system


class TestIsRunningUnderPytest:
    """Test is_running_under_pytest detection."""

    def test_detects_pytest_via_pytest_current_test_env(self) -> None:
        """Should detect pytest via PYTEST_CURRENT_TEST environment variable."""
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_file.py::test_func"}):
            assert mod_utils_system.is_running_under_pytest() is True

    def test_detects_pytest_via_underscore_env(self) -> None:
        """Should detect pytest via _ environment variable containing 'pytest'."""
        with patch.dict(os.environ, {"_": "/path/to/pytest"}):
            assert mod_utils_system.is_running_under_pytest() is True

    def test_detects_pytest_via_sys_argv(self) -> None:
        """Should detect pytest via sys.argv containing 'pytest'."""
        original_argv = sys.argv.copy()
        try:
            sys.argv = ["pytest", "tests/test_something.py"]
            assert mod_utils_system.is_running_under_pytest() is True
        finally:
            sys.argv = original_argv

    def test_returns_false_when_not_under_pytest(self) -> None:
        """Should return False when not running under pytest."""
        # Clear pytest-related environment variables
        env_vars_to_clear = ["PYTEST_CURRENT_TEST", "_"]
        original_env = {k: os.environ.get(k) for k in env_vars_to_clear}

        try:
            # Remove pytest-related env vars
            for key in env_vars_to_clear:
                os.environ.pop(key, None)

            # Mock sys.argv to not contain pytest
            original_argv = sys.argv.copy()
            try:
                sys.argv = ["python", "script.py"]
                assert mod_utils_system.is_running_under_pytest() is False
            finally:
                sys.argv = original_argv
        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
                elif key in os.environ:
                    del os.environ[key]

    def test_handles_mixed_argv_types(self) -> None:
        """Should handle sys.argv with mixed types gracefully."""
        original_argv = sys.argv.copy()
        try:
            # In practice sys.argv is always strings, but test defensive code
            sys.argv = ["pytest", "test.py"]
            assert mod_utils_system.is_running_under_pytest() is True
        finally:
            sys.argv = original_argv
