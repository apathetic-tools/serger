# tests/50_core/test_priv__apply_move_action.py
"""Tests for serger.module_actions._apply_move_action."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

import pytest

import serger.config.config_types as mod_types
import serger.module_actions as mod_module_actions


def test_apply_move_action_preserve() -> None:
    """Test move action with preserve mode."""
    module_names = ["apathetic_logs", "apathetic_logs.utils", "other_pkg"]
    action: mod_types.ModuleActionFull = {
        "source": "apathetic_logs",
        "dest": "grinch",
        "action": "move",
        "mode": "preserve",
    }
    result = mod_module_actions._apply_move_action(module_names, action)

    assert result == ["grinch", "grinch.utils", "other_pkg"]


def test_apply_move_action_flatten() -> None:
    """Test move action with flatten mode."""
    module_names = [
        "apathetic_logs",
        "apathetic_logs.utils",
        "apathetic_logs.utils.text",
        "other_pkg",
    ]
    action: mod_types.ModuleActionFull = {
        "source": "apathetic_logs",
        "dest": "grinch",
        "action": "move",
        "mode": "flatten",
    }
    result = mod_module_actions._apply_move_action(module_names, action)

    assert result == ["grinch", "grinch.utils", "grinch.text", "other_pkg"]


def test_apply_move_action_no_dest_error() -> None:
    """Test that move action without dest raises error."""
    module_names = ["pkg1"]
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "action": "move",
    }
    with pytest.raises(ValueError, match="requires 'dest' field"):
        mod_module_actions._apply_move_action(module_names, action)


def test_apply_move_action_invalid_mode_error() -> None:
    """Test that move action with invalid mode raises error."""
    module_names = ["pkg1"]
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "dest": "pkg2",
        "action": "move",
        "mode": "invalid",  # type: ignore[typeddict-item]
    }
    with pytest.raises(ValueError, match="Invalid mode"):
        mod_module_actions._apply_move_action(module_names, action)


def test_apply_move_action_default_mode_preserve() -> None:
    """Test that move action defaults to preserve mode."""
    module_names = ["pkg1", "pkg1.sub"]
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "dest": "pkg2",
        "action": "move",
    }
    result = mod_module_actions._apply_move_action(module_names, action)

    assert result == ["pkg2", "pkg2.sub"]
