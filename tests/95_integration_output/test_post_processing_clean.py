# tests/95_integration_output/test_post_processing_clean.py
"""Integration test to verify post-processing passes cleanly when building serger.

This test ensures that when serger builds itself (dist/serger.py), the
post-processing step completes without warnings or failures.
"""

import logging
import subprocess
import sys

import pytest

import serger.meta as mod_meta
from tests.utils import PROJ_ROOT


def test_post_processing_clean_when_building_serger(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Post-processing should pass cleanly when building serger script."""
    # --- setup ---
    out_file = PROJ_ROOT / "dist" / "serger.py"

    # Ensure dist directory exists
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # --- execute ---
    # Configure caplog to capture warnings and errors from serger logger
    with caplog.at_level(logging.WARNING, logger=mod_meta.PROGRAM_PACKAGE):
        # Run serger build command (builds dist/serger.py using .serger.jsonc)
        proc = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "serger"],
            capture_output=True,
            text=True,
            check=True,
            cwd=PROJ_ROOT,
        )

    # --- verify ---
    # Build should succeed
    assert proc.returncode == 0, (
        f"Build failed with return code {proc.returncode}. stderr: {proc.stderr}"
    )

    # Output file should exist
    assert out_file.exists(), "Expected dist/serger.py to be generated"

    # Check captured log records for warnings/errors related to post-processing
    all_warnings = [
        record for record in caplog.records if record.levelname in ("WARNING", "ERROR")
    ]

    # Filter for post-processing related warnings/errors
    post_processing_warnings = [
        record
        for record in all_warnings
        if any(
            keyword in record.message.lower()
            for keyword in [
                "post-processing",
                "post_processing",
                "postprocessing",
                "post processing",
            ]
        )
    ]

    # Should have no post-processing warnings or errors
    assert not post_processing_warnings, (
        "Post-processing produced warnings/errors:\n"
        + "\n".join(
            f"  {record.levelname}: {record.message}"
            for record in post_processing_warnings
        )
    )

    # Also check stderr for any post-processing related warnings/errors
    post_processing_stderr = [
        line
        for line in proc.stderr.splitlines()
        if any(
            keyword in line.lower()
            for keyword in [
                "post-processing",
                "post_processing",
                "postprocessing",
                "post processing",
            ]
        )
        and any(
            keyword in line.lower()
            for keyword in [
                "warning",
                "error",
                "failed",
                "failure",
            ]
        )
    ]

    # Should have no post-processing related warnings/errors in stderr
    assert not post_processing_stderr, (
        "Post-processing warnings/errors in stderr:\n"
        + "\n".join(post_processing_stderr)
    )

    # Verify the generated file compiles (basic sanity check)
    compile_result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "py_compile", str(out_file)],
        check=False,
        capture_output=True,
        text=True,
        cwd=PROJ_ROOT,
    )
    assert compile_result.returncode == 0, (
        f"Generated file does not compile. stderr: {compile_result.stderr}"
    )
