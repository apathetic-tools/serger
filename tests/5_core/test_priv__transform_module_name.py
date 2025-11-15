# tests/5_core/test_priv__transform_module_name.py
"""Tests for serger.module_actions._transform_module_name."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

import serger.module_actions as mod_module_actions


def test_transform_module_name_exact_match_preserve() -> None:
    """Test exact match transformation with preserve mode."""
    result = mod_module_actions._transform_module_name(
        "apathetic_logs", "apathetic_logs", "grinch", "preserve"
    )
    assert result == "grinch"


def test_transform_module_name_exact_match_flatten() -> None:
    """Test exact match transformation with flatten mode."""
    result = mod_module_actions._transform_module_name(
        "apathetic_logs", "apathetic_logs", "grinch", "flatten"
    )
    assert result == "grinch"


def test_transform_module_name_submodule_preserve() -> None:
    """Test submodule transformation with preserve mode."""
    result = mod_module_actions._transform_module_name(
        "apathetic_logs.utils", "apathetic_logs", "grinch", "preserve"
    )
    assert result == "grinch.utils"


def test_transform_module_name_submodule_flatten() -> None:
    """Test submodule transformation with flatten mode."""
    result = mod_module_actions._transform_module_name(
        "apathetic_logs.utils", "apathetic_logs", "grinch", "flatten"
    )
    assert result == "grinch.utils"


def test_transform_module_name_nested_preserve() -> None:
    """Test nested submodule transformation with preserve mode."""
    result = mod_module_actions._transform_module_name(
        "apathetic_logs.utils.text", "apathetic_logs", "grinch", "preserve"
    )
    assert result == "grinch.utils.text"


def test_transform_module_name_nested_flatten() -> None:
    """Test nested submodule transformation with flatten mode."""
    result = mod_module_actions._transform_module_name(
        "apathetic_logs.utils.text", "apathetic_logs", "grinch", "flatten"
    )
    assert result == "grinch.text"


def test_transform_module_name_deeply_nested_flatten() -> None:
    """Test deeply nested submodule transformation with flatten mode."""
    result = mod_module_actions._transform_module_name(
        "apathetic_logs.utils.schema.validator",
        "apathetic_logs",
        "grinch",
        "flatten",
    )
    assert result == "grinch.validator"


def test_transform_module_name_no_match() -> None:
    """Test that non-matching module returns None."""
    result = mod_module_actions._transform_module_name(
        "other_pkg", "apathetic_logs", "grinch", "preserve"
    )
    assert result is None


def test_transform_module_name_prefix_but_not_match() -> None:
    """Test that prefix match without dot returns None."""
    # "apathetic_logs_extra" starts with "apathetic_logs" but isn't a match
    result = mod_module_actions._transform_module_name(
        "apathetic_logs_extra", "apathetic_logs", "grinch", "preserve"
    )
    assert result is None
