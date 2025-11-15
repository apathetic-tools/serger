"""Tests for serger.module_actions.validate_no_conflicting_operations."""

import pytest

import serger.config.config_types as mod_types
import serger.module_actions as mod_module_actions


def test_validate_no_conflicting_operations_valid_success() -> None:
    """Test that validation passes for non-conflicting operations."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "move", "dest": "pkg1_new"},
        {"source": "pkg2", "action": "copy", "dest": "pkg2_new"},
        {"source": "pkg3", "action": "delete"},
    ]

    # Should not raise
    mod_module_actions.validate_no_conflicting_operations(actions)


def test_validate_no_conflicting_operations_delete_moved_error() -> None:
    """Test that deleting something being moved raises error."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "move", "dest": "pkg1_new"},
        {"source": "pkg1", "action": "delete"},  # Conflict
    ]

    with pytest.raises(ValueError, match="Cannot delete module 'pkg1'"):
        mod_module_actions.validate_no_conflicting_operations(actions)


def test_validate_no_conflicting_operations_delete_copied_error() -> None:
    """Test that deleting something being copied raises error."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "copy", "dest": "pkg1_new"},
        {"source": "pkg1", "action": "delete"},  # Conflict
    ]

    with pytest.raises(ValueError, match="Cannot delete module 'pkg1'"):
        mod_module_actions.validate_no_conflicting_operations(actions)


def test_validate_no_conflicting_operations_move_to_deleted_error() -> None:
    """Test that moving to something being deleted raises error."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "delete"},
        {"source": "pkg2", "action": "move", "dest": "pkg1"},  # Conflict
    ]

    with pytest.raises(ValueError, match="Cannot move to 'pkg1'"):
        mod_module_actions.validate_no_conflicting_operations(actions)


def test_validate_no_conflicting_operations_copy_to_deleted_error() -> None:
    """Test that copying to something being deleted raises error."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "delete"},
        {"source": "pkg2", "action": "copy", "dest": "pkg1"},  # Conflict
    ]

    with pytest.raises(ValueError, match="Cannot copy to 'pkg1'"):
        mod_module_actions.validate_no_conflicting_operations(actions)


def test_validate_no_conflicting_operations_move_to_moved_from_error() -> None:
    """Test that moving to something being moved from raises error."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "move", "dest": "pkg1_new"},
        {"source": "pkg2", "action": "move", "dest": "pkg1"},  # Conflict
    ]

    with pytest.raises(ValueError, match="Cannot move to 'pkg1'"):
        mod_module_actions.validate_no_conflicting_operations(actions)


def test_validate_no_conflicting_operations_move_to_copied_from_error() -> None:
    """Test that moving to something being copied from raises error."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "copy", "dest": "pkg1_new"},
        {"source": "pkg2", "action": "move", "dest": "pkg1"},  # Conflict
    ]

    with pytest.raises(ValueError, match="Cannot move to 'pkg1'"):
        mod_module_actions.validate_no_conflicting_operations(actions)


def test_validate_no_conflicting_operations_copy_to_moved_from_allowed() -> None:
    """Test that copying to something being moved from is allowed."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "move", "dest": "pkg1_new"},
        {"source": "pkg2", "action": "copy", "dest": "pkg1"},  # Allowed
    ]

    # Should not raise (copy can overwrite)
    mod_module_actions.validate_no_conflicting_operations(actions)


def test_validate_no_conflicting_operations_copy_to_copied_from_allowed() -> None:
    """Test that copying to something being copied from is allowed."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "copy", "dest": "pkg1_new"},
        {"source": "pkg2", "action": "copy", "dest": "pkg1"},  # Allowed
    ]

    # Should not raise (copy can overwrite)
    mod_module_actions.validate_no_conflicting_operations(actions)
