# tests/5_core/test_priv__apply_delete_action.py
"""Tests for serger.module_actions._apply_delete_action."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

import serger.config.config_types as mod_types
import serger.module_actions as mod_module_actions


def test_apply_delete_action_exact_match() -> None:
    """Test delete action removes exact match."""
    module_names = ["pkg1", "pkg2", "pkg3"]
    action: mod_types.ModuleActionFull = {
        "source": "pkg2",
        "action": "delete",
    }
    result = mod_module_actions._apply_delete_action(module_names, action)

    assert result == ["pkg1", "pkg3"]


def test_apply_delete_action_removes_submodules() -> None:
    """Test delete action removes module and all submodules."""
    module_names = [
        "pkg1",
        "pkg2",
        "pkg2.sub",
        "pkg2.sub.module",
        "pkg3",
    ]
    action: mod_types.ModuleActionFull = {
        "source": "pkg2",
        "action": "delete",
    }
    result = mod_module_actions._apply_delete_action(module_names, action)

    assert result == ["pkg1", "pkg3"]


def test_apply_delete_action_no_match() -> None:
    """Test delete action when source doesn't match."""
    module_names = ["pkg1", "pkg2"]
    action: mod_types.ModuleActionFull = {
        "source": "pkg3",
        "action": "delete",
    }
    result = mod_module_actions._apply_delete_action(module_names, action)

    assert result == ["pkg1", "pkg2"]


def test_apply_delete_action_prefix_but_not_match() -> None:
    """Test delete action doesn't match prefix without dot."""
    module_names = ["pkg1", "pkg1_extra", "pkg1.sub"]
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "action": "delete",
    }
    result = mod_module_actions._apply_delete_action(module_names, action)

    # pkg1_extra should remain (not a submodule)
    assert result == ["pkg1_extra"]
