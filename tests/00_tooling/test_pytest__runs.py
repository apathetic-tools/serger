# tests/00_tooling/test_pytest__runs.py
"""Verify pytest configuration and basic functionality.

This test verifies that pytest itself is functioning correctly with our project
configuration. It's a minimal smoke test that should always pass and does not
invoke any of our application code.

Use this test to troubleshoot pytest configuration issues when tests fail to
run or collect properly.

Run just this test:
    poetry run pytest tests/00_tooling/test_pytest__runs.py
"""


def test_pytest_runs() -> None:
    """Minimal test to confirm pytest is functioning with our configuration."""
    # This test does not use runtime_env and should always pass
    assert True
