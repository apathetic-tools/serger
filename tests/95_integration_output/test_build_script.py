# tests/95_integration_output/test_build_script.py
"""Integration tests for building `dist/serger.py`.

These verify that the standalone script (`dist/serger.py`)
embeds the correct commit information depending on environment variables.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.utils import PROJ_ROOT


# --- only for singlefile runs ---
__runtime_mode__ = "singlefile"


@pytest.mark.parametrize(
    ("env_vars", "expected_pattern"),
    argvalues=[
        ({}, r"\(unknown \(local build\)\)"),  # local dev
        ({"CI": "true"}, r"\([0-9a-f]{4,}\)"),  # simulated CI
    ],
)
def test_build_script_respects_ci_env(
    tmp_path: Path,
    env_vars: dict[str, str],
    expected_pattern: str,
) -> None:
    """Should embed either '(unknown (local build))' or a real hash depending on env."""
    # --- setup ---
    tmp_script = tmp_path / "script-test.py"

    # Ensure a clean rebuild every time -
    if tmp_script.exists():
        tmp_script.unlink()

    # Reset any pre-existing CI vars
    env = dict(os.environ)
    # Clear all CI-related environment variables
    for key in ("CI", "GITHUB_ACTIONS", "GIT_TAG", "GITHUB_REF"):
        env.pop(key, None)

    # Apply simulated environment
    env.update(env_vars)

    # --- execute and verify ---

    # 1) generate the bundle using python -m serger
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "serger", "--out", str(tmp_script)],
        capture_output=True,
        text=True,
        check=True,
        env=env,
        cwd=PROJ_ROOT,
    )
    # Filter out expected warnings about files outside project directory
    # (these occur when stitching installed packages like apathetic_logging)
    stderr_lines = [
        line
        for line in proc.stderr.strip().split("\n")
        if line and "Including file outside project directory" not in line
    ]
    assert not stderr_lines, f"Bundler stderr not empty: {proc.stderr}"

    # Confirm the bundle was created
    assert tmp_script.exists(), "Expected temporary script to be generated"

    # 2) Execute the generated script
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(tmp_script), "--version"],
        capture_output=True,
        text=True,
        check=True,
        cwd=PROJ_ROOT,
        env=os.environ.copy(),
    )

    out = result.stdout.strip()
    assert out.startswith("Serger"), f"Unexpected version output: {out}"
    assert re.search(r"\d+\.\d+\.\d+", out), f"No semantic version found: {out}"
    assert re.search(expected_pattern, out), f"Unexpected commit pattern: {out}"
