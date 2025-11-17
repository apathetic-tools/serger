"""Tests for serger.module_actions.validate_action_dest."""

import pytest

import serger.config.config_types as mod_types
import serger.module_actions as mod_module_actions
from tests.utils.buildconfig import make_module_action_full


def test_validate_action_dest_delete_no_dest_success() -> None:
    """Test that delete action without dest is valid."""
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "action": "delete",
    }
    existing_modules = {"pkg1", "pkg2"}

    # Should not raise
    mod_module_actions.validate_action_dest(action, existing_modules)


def test_validate_action_dest_delete_with_dest_error() -> None:
    """Test that delete action with dest raises error."""
    action = make_module_action_full("pkg1", action="delete", dest="pkg2")
    existing_modules = {"pkg1", "pkg2"}

    with pytest.raises(ValueError, match="must not have 'dest' field"):
        mod_module_actions.validate_action_dest(action, existing_modules)


def test_validate_action_dest_move_with_dest_success() -> None:
    """Test that move action with dest is valid."""
    action = make_module_action_full("pkg1", dest="pkg2_new")
    existing_modules = {"pkg1", "pkg2"}

    # Should not raise
    mod_module_actions.validate_action_dest(action, existing_modules)


def test_validate_action_dest_move_no_dest_error() -> None:
    """Test that move action without dest raises error."""
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "action": "move",
    }
    existing_modules = {"pkg1", "pkg2"}

    with pytest.raises(ValueError, match="requires 'dest' field"):
        mod_module_actions.validate_action_dest(action, existing_modules)


def test_validate_action_dest_move_conflict_error() -> None:
    """Test that move action with conflicting dest raises error."""
    action = make_module_action_full("pkg1", dest="pkg2")  # Conflicts with existing
    existing_modules = {"pkg1", "pkg2"}

    with pytest.raises(ValueError, match="conflicts with existing module"):
        mod_module_actions.validate_action_dest(action, existing_modules)


def test_validate_action_dest_copy_with_dest_success() -> None:
    """Test that copy action with dest is valid (even if conflicts)."""
    # Copy can overwrite
    action = make_module_action_full("pkg1", action="copy", dest="pkg2")
    existing_modules = {"pkg1", "pkg2"}

    # Should not raise (copy allows overwriting)
    mod_module_actions.validate_action_dest(action, existing_modules)


def test_validate_action_dest_copy_no_dest_error() -> None:
    """Test that copy action without dest raises error."""
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "action": "copy",
    }
    existing_modules = {"pkg1", "pkg2"}

    with pytest.raises(ValueError, match="requires 'dest' field"):
        mod_module_actions.validate_action_dest(action, existing_modules)
