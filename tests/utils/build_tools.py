# tests/utils/build_tools.py
"""Utilities for finding and working with build tools in tests."""

import shutil
import subprocess
from pathlib import Path


def find_shiv() -> str:
    """Find the shiv executable.

    Searches for shiv in:
    1. System PATH
    2. Poetry virtual environment (if poetry is available)

    Returns:
        Path to the shiv executable

    Raises:
        RuntimeError: If shiv is not found in PATH or poetry venv
    """
    shiv_path = shutil.which("shiv")
    if shiv_path:
        return shiv_path
    # If not in PATH, try to find it in the poetry venv
    poetry_cmd = shutil.which("poetry")
    if poetry_cmd:
        try:
            venv_path_result = subprocess.run(  # noqa: S603
                [poetry_cmd, "env", "info", "--path"],
                capture_output=True,
                text=True,
                check=True,
            )
            venv_path = Path(venv_path_result.stdout.strip())
            shiv_in_venv = venv_path / "bin" / "shiv"
            if shiv_in_venv.exists():
                return str(shiv_in_venv)
        except Exception:  # noqa: BLE001, S110
            # Poetry command failed or venv path invalid - continue to error
            pass
    msg = (
        "shiv not found in PATH or poetry venv. "
        "Ensure shiv is installed: poetry install --with dev"
    )
    raise RuntimeError(msg)
