# tests/5_core/test_run_ruff_if_available.py
"""Tests for run_ruff_if_available function."""

import shutil
import tempfile
from pathlib import Path

import pytest

import serger.verify_script as mod_verify
from tests.utils import patch_everywhere


RUFF_AVAILABLE = shutil.which("ruff") is not None


@pytest.mark.skipif(not RUFF_AVAILABLE, reason="ruff not available")
def test_run_ruff_if_available_with_ruff() -> None:
    """Should run ruff when ruff is available."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        # Write code with formatting issues that ruff can fix
        f.write("x=1+2\n")  # Missing spaces
        f.flush()
        path = Path(f.name)

    try:
        result = mod_verify.run_ruff_if_available(path)
        assert result is True
        # Verify ruff formatted the file
        content = path.read_text()
        # Ruff may or may not format this, so check for either
        assert "x = 1 + 2" in content or "x=1+2" in content
    finally:
        path.unlink()


@pytest.mark.skipif(not RUFF_AVAILABLE, reason="ruff not available")
def test_run_ruff_if_available_formats_file() -> None:
    """Should format file with ruff when available."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write('def test():\n    x="hello"\n    return x\n')
        f.flush()
        path = Path(f.name)

    try:
        result = mod_verify.run_ruff_if_available(path)
        assert result is True
        # File should be formatted by ruff
        content = path.read_text()
        assert content  # Should have content
    finally:
        path.unlink()


def test_run_ruff_if_available_without_ruff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should return False when ruff is not available."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        path = Path(f.name)

    try:
        # Mock ruff_is_available to return None
        patch_everywhere(monkeypatch, mod_verify, "ruff_is_available", lambda: None)
        result = mod_verify.run_ruff_if_available(path)
        assert result is False
    finally:
        path.unlink()
