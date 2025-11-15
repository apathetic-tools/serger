"""Tests for serger.module_actions.validate_no_circular_moves."""

import pytest

import serger.config.config_types as mod_types
import serger.module_actions as mod_module_actions


def test_validate_no_circular_moves_no_moves_success() -> None:
    """Test that validation passes when there are no moves."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "delete"},
        {"source": "pkg2", "action": "copy", "dest": "pkg3"},
    ]

    # Should not raise
    mod_module_actions.validate_no_circular_moves(actions)


def test_validate_no_circular_moves_valid_moves_success() -> None:
    """Test that validation passes for valid non-circular moves."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "move", "dest": "pkg1_new"},
        {"source": "pkg2", "action": "move", "dest": "pkg2_new"},
    ]

    # Should not raise
    mod_module_actions.validate_no_circular_moves(actions)


def test_validate_no_circular_moves_direct_circular_error() -> None:
    """Test that direct circular move (A -> B, B -> A) raises error."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "move", "dest": "pkg2"},
        {"source": "pkg2", "action": "move", "dest": "pkg1"},
    ]

    with pytest.raises(ValueError, match="Circular move chain detected"):
        mod_module_actions.validate_no_circular_moves(actions)


def test_validate_no_circular_moves_indirect_circular_error() -> None:
    """Test that indirect circular move (A -> B, B -> C, C -> A) raises error."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "move", "dest": "pkg2"},
        {"source": "pkg2", "action": "move", "dest": "pkg3"},
        {"source": "pkg3", "action": "move", "dest": "pkg1"},
    ]

    with pytest.raises(ValueError, match="Circular move chain detected"):
        mod_module_actions.validate_no_circular_moves(actions)


def test_validate_no_circular_moves_ignores_non_moves() -> None:
    """Test that non-move actions don't affect circular move detection."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "delete"},
        {"source": "pkg2", "action": "copy", "dest": "pkg3"},
        {"source": "pkg4", "action": "move", "dest": "pkg5"},
        {"source": "pkg5", "action": "move", "dest": "pkg4"},  # Circular
    ]

    with pytest.raises(ValueError, match="Circular move chain detected"):
        mod_module_actions.validate_no_circular_moves(actions)
