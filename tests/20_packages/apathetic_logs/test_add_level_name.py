# tests/20_packages/apathetic_logs/test_add_level_name.py
"""Tests for addLevelName() and level validation features."""

import logging

import pytest

import apathetic_logs.logs as mod_alogs


# ---------------------------------------------------------------------------
# Tests for _validate_level_positive()
# ---------------------------------------------------------------------------


def test_validate_level_positive_valid_level() -> None:
    """_validate_level_positive() should pass for valid levels (> 0)."""
    # Should not raise for valid levels
    mod_alogs.ApatheticCLILogger._validate_level_positive(1, "TEST")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    mod_alogs.ApatheticCLILogger._validate_level_positive(5, "TRACE")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    mod_alogs.ApatheticCLILogger._validate_level_positive(10, "DEBUG")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    mod_alogs.ApatheticCLILogger._validate_level_positive(100, "CUSTOM")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]


def test_validate_level_positive_zero_raises() -> None:
    """_validate_level_positive() should raise ValueError for level 0."""
    with pytest.raises(ValueError, match=r"<= 0.*NOTSET inheritance"):
        mod_alogs.ApatheticCLILogger._validate_level_positive(0, "TEST")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]


def test_validate_level_positive_negative_raises() -> None:
    """_validate_level_positive() should raise ValueError for negative levels."""
    with pytest.raises(ValueError, match=r"<= 0.*NOTSET inheritance"):
        mod_alogs.ApatheticCLILogger._validate_level_positive(-5, "NEGATIVE")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]


def test_validate_level_positive_auto_detects_name() -> None:
    """_validate_level_positive() should auto-detect level name if None."""
    with pytest.raises(ValueError, match=r"NOTSET.*<= 0"):
        mod_alogs.ApatheticCLILogger._validate_level_positive(0, None)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]


# ---------------------------------------------------------------------------
# Tests for addLevelName()
# ---------------------------------------------------------------------------


def test_add_level_name_success() -> None:
    """addLevelName() should successfully register a custom level."""
    # Use a unique level value to avoid conflicts
    level_value = 25
    level_name = "CUSTOM_TEST"

    # Clean up if it exists
    if hasattr(logging, level_name):
        delattr(logging, level_name)

    mod_alogs.ApatheticCLILogger.addLevelName(level_value, level_name)

    # Verify level name is registered
    assert logging.getLevelName(level_value) == level_name

    # Verify convenience attribute is set
    assert getattr(logging, level_name) == level_value

    # Clean up
    delattr(logging, level_name)


def test_add_level_name_sets_convenience_attribute() -> None:
    """addLevelName() should set logging.<LEVEL_NAME> attribute."""
    # Use a level value that doesn't conflict with built-in levels
    # Built-in levels: DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50
    level_value = 25  # Between INFO and WARNING
    level_name = "CONVENIENCE_TEST"

    # Clean up if it exists
    if hasattr(logging, level_name):
        delattr(logging, level_name)

    mod_alogs.ApatheticCLILogger.addLevelName(level_value, level_name)

    # Verify attribute exists and has correct value
    assert hasattr(logging, level_name)
    assert getattr(logging, level_name) == level_value

    # Can use it like built-in levels
    logger = logging.getLogger("test")
    logger.setLevel(getattr(logging, level_name))
    assert logger.level == level_value

    # Clean up
    delattr(logging, level_name)


def test_add_level_name_zero_raises() -> None:
    """addLevelName() should raise ValueError for level 0."""
    with pytest.raises(ValueError, match=r"<= 0.*NOTSET inheritance"):
        mod_alogs.ApatheticCLILogger.addLevelName(0, "ZERO_LEVEL")


def test_add_level_name_negative_raises() -> None:
    """addLevelName() should raise ValueError for negative levels."""
    with pytest.raises(ValueError, match=r"<= 0.*NOTSET inheritance"):
        mod_alogs.ApatheticCLILogger.addLevelName(-10, "NEGATIVE_LEVEL")


def test_add_level_name_idempotent() -> None:
    """addLevelName() should be idempotent (can call multiple times)."""
    level_value = 35
    level_name = "IDEMPOTENT_TEST"

    # Clean up if it exists
    if hasattr(logging, level_name):
        delattr(logging, level_name)

    # First call
    mod_alogs.ApatheticCLILogger.addLevelName(level_value, level_name)
    assert getattr(logging, level_name) == level_value

    # Second call with same value (should not raise)
    mod_alogs.ApatheticCLILogger.addLevelName(level_value, level_name)
    assert getattr(logging, level_name) == level_value

    # Clean up
    delattr(logging, level_name)


def test_add_level_name_rejects_invalid_existing_attribute_type() -> None:
    """addLevelName() should reject if attribute exists with non-integer value."""
    level_name = "INVALID_TYPE_TEST"

    # Set invalid attribute
    setattr(logging, level_name, "not_an_int")

    try:
        with pytest.raises(
            ValueError,
            match=r"non-integer value.*Level attributes must be integers",
        ):
            mod_alogs.ApatheticCLILogger.addLevelName(40, level_name)
    finally:
        # Clean up
        if hasattr(logging, level_name):
            delattr(logging, level_name)


def test_add_level_name_rejects_invalid_existing_attribute_value() -> None:
    """addLevelName() should reject if attribute exists with <= 0 value."""
    level_name = "INVALID_VALUE_TEST"

    # Set invalid attribute (zero)
    setattr(logging, level_name, 0)

    try:
        with pytest.raises(
            ValueError,
            match=r"<= 0.*NOTSET inheritance",
        ):
            mod_alogs.ApatheticCLILogger.addLevelName(45, level_name)
    finally:
        # Clean up
        if hasattr(logging, level_name):
            delattr(logging, level_name)


def test_add_level_name_rejects_different_existing_value() -> None:
    """addLevelName() should reject if attribute exists with different value."""
    level_name = "DIFFERENT_VALUE_TEST"
    existing_value = 50
    new_value = 55

    # Set existing attribute with different value
    setattr(logging, level_name, existing_value)

    try:
        with pytest.raises(
            ValueError,
            match=r"different value.*must match the level value",
        ):
            mod_alogs.ApatheticCLILogger.addLevelName(new_value, level_name)
    finally:
        # Clean up
        if hasattr(logging, level_name):
            delattr(logging, level_name)


def test_add_level_name_works_with_extend_logging_module() -> None:
    """addLevelName() should work correctly when used by extend_logging_module()."""
    # Reset extension flag
    mod_alogs.ApatheticCLILogger._logging_module_extended = False  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # Call extend_logging_module (uses addLevelName internally)
    result = mod_alogs.ApatheticCLILogger.extend_logging_module()

    assert result is True

    # Verify levels are registered
    assert logging.getLevelName(mod_alogs.TEST_LEVEL) == "TEST"
    assert logging.getLevelName(mod_alogs.TRACE_LEVEL) == "TRACE"
    assert logging.getLevelName(mod_alogs.SILENT_LEVEL) == "SILENT"

    # Verify convenience attributes are set
    assert logging.TEST == mod_alogs.TEST_LEVEL  # type: ignore[attr-defined]
    assert logging.TRACE == mod_alogs.TRACE_LEVEL  # type: ignore[attr-defined]
    assert logging.SILENT == mod_alogs.SILENT_LEVEL  # type: ignore[attr-defined]


def test_add_level_name_matches_builtin_level_pattern() -> None:
    """addLevelName() should create attributes matching built-in level pattern."""
    level_value = 60
    level_name = "PATTERN_TEST"

    # Clean up if it exists
    if hasattr(logging, level_name):
        delattr(logging, level_name)

    mod_alogs.ApatheticCLILogger.addLevelName(level_value, level_name)

    # Verify it matches built-in pattern
    assert hasattr(logging, "DEBUG")  # built-in
    assert hasattr(logging, level_name)  # custom (same pattern)

    # Both should be integers
    assert isinstance(logging.DEBUG, int)
    assert isinstance(getattr(logging, level_name), int)

    # Both should be usable in setLevel
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)
    assert logger.level == logging.DEBUG

    logger.setLevel(getattr(logging, level_name))
    assert logger.level == level_value

    # Clean up
    delattr(logging, level_name)


# ---------------------------------------------------------------------------
# Tests for setLevel() validation
# ---------------------------------------------------------------------------


def test_set_level_validates_custom_levels() -> None:
    """setLevel() should validate custom levels are not <= 0."""
    logger = mod_alogs.ApatheticCLILogger("test")

    # Valid custom levels should work
    logger.setLevel(mod_alogs.TEST_LEVEL)
    assert logger.level == mod_alogs.TEST_LEVEL

    logger.setLevel(mod_alogs.TRACE_LEVEL)
    assert logger.level == mod_alogs.TRACE_LEVEL

    logger.setLevel(mod_alogs.SILENT_LEVEL)
    assert logger.level == mod_alogs.SILENT_LEVEL


def test_set_level_allows_builtin_levels() -> None:
    """setLevel() should allow built-in levels (all are > 0)."""
    logger = mod_alogs.ApatheticCLILogger("test")

    # Built-in levels should work (they're all > 0, so pass validation)
    logger.setLevel(logging.DEBUG)
    assert logger.level == logging.DEBUG

    logger.setLevel(logging.INFO)
    assert logger.level == logging.INFO

    logger.setLevel(logging.WARNING)
    assert logger.level == logging.WARNING


def test_set_level_rejects_any_level_zero_or_negative() -> None:
    """setLevel() should reject ANY level <= 0, not just our custom levels."""
    logger = mod_alogs.ApatheticCLILogger("test")

    # Should reject level 0 (NOTSET)
    with pytest.raises(ValueError, match=r"<= 0.*NOTSET inheritance"):
        logger.setLevel(0)

    # Should reject negative levels
    with pytest.raises(ValueError, match=r"<= 0.*NOTSET inheritance"):
        logger.setLevel(-5)

    # Should reject user's custom level if <= 0
    logging.addLevelName(-10, "USER_BAD")
    with pytest.raises(ValueError, match=r"<= 0.*NOTSET inheritance"):
        logger.setLevel(-10)


def test_set_level_validates_custom_level_string() -> None:
    """setLevel() should validate custom levels when passed as string."""
    logger = mod_alogs.ApatheticCLILogger("test")

    # Valid custom level strings should work
    logger.setLevel("TEST")
    assert logger.level == mod_alogs.TEST_LEVEL

    logger.setLevel("TRACE")
    assert logger.level == mod_alogs.TRACE_LEVEL

    logger.setLevel("SILENT")
    assert logger.level == mod_alogs.SILENT_LEVEL
