# tests/50_core/test_priv__apply_copy_action.py
"""Tests for serger.module_actions._apply_copy_action."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

import pytest

import serger.config.config_types as mod_types
import serger.module_actions as mod_module_actions


def test_apply_copy_action_preserve() -> None:
    """Test copy action with preserve mode (source remains)."""
    module_names = ["apathetic_logs", "apathetic_logs.utils", "other_pkg"]
    action: mod_types.ModuleActionFull = {
        "source": "apathetic_logs",
        "dest": "grinch",
        "action": "copy",
        "mode": "preserve",
    }
    result = mod_module_actions._apply_copy_action(module_names, action)

    assert result == [
        "apathetic_logs",
        "grinch",
        "apathetic_logs.utils",
        "grinch.utils",
        "other_pkg",
    ]


def test_apply_copy_action_flatten() -> None:
    """Test copy action with flatten mode (source remains)."""
    module_names = [
        "apathetic_logs",
        "apathetic_logs.utils",
        "apathetic_logs.utils.text",
        "other_pkg",
    ]
    action: mod_types.ModuleActionFull = {
        "source": "apathetic_logs",
        "dest": "grinch",
        "action": "copy",
        "mode": "flatten",
    }
    result = mod_module_actions._apply_copy_action(module_names, action)

    assert result == [
        "apathetic_logs",
        "grinch",
        "apathetic_logs.utils",
        "grinch.utils",
        "apathetic_logs.utils.text",
        "grinch.text",
        "other_pkg",
    ]


def test_apply_copy_action_no_dest_error() -> None:
    """Test that copy action without dest raises error."""
    module_names = ["pkg1"]
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "action": "copy",
    }
    with pytest.raises(ValueError, match="requires 'dest' field"):
        mod_module_actions._apply_copy_action(module_names, action)


def test_apply_copy_action_source_remains() -> None:
    """Test that copy action keeps source modules."""
    module_names = ["pkg1", "pkg1.sub"]
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "dest": "pkg2",
        "action": "copy",
    }
    result = mod_module_actions._apply_copy_action(module_names, action)

    # Source should remain, dest should be added
    assert "pkg1" in result
    assert "pkg1.sub" in result
    assert "pkg2" in result
    assert "pkg2.sub" in result
