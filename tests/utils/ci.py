# tests/utils/ci.py
"""CI environment detection utilities for tests.

This module re-exports is_ci from apathetic_utils.ci for backward compatibility.
"""

import apathetic_utils.ci as mod_ci


__all__ = ["is_ci"]


def is_ci() -> bool:
    """Check if running in a CI environment.

    Re-exports apathetic_utils.ci.is_ci for backward compatibility.
    """
    return mod_ci.is_ci()
