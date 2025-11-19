# src/apathetic_utils/ci.py
"""CI environment detection utilities."""

import os


# CI environment variable names that indicate CI environment
CI_ENV_VARS = ("CI", "GITHUB_ACTIONS", "GIT_TAG", "GITHUB_REF")


def is_ci() -> bool:
    """Check if running in a CI environment.

    Returns True if any of the following environment variables are set:
    - CI: Generic CI indicator (set by most CI systems)
    - GITHUB_ACTIONS: GitHub Actions specific
    - GIT_TAG: Indicates a tagged build
    - GITHUB_REF: GitHub Actions ref (branch/tag)

    Returns:
        True if running in CI, False otherwise
    """
    return bool(any(os.getenv(var) for var in CI_ENV_VARS))
