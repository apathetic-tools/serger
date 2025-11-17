"""Tests for serger.module_actions.apply_single_action."""

import pytest

import serger.config.config_types as mod_types
import serger.module_actions as mod_module_actions
from tests.utils.buildconfig import make_module_action_full


def test_apply_single_action_move() -> None:
    """Test apply_single_action routes to move handler."""
    module_names = ["pkg1", "pkg1.sub"]
    action = make_module_action_full("pkg1", dest="pkg2")
    detected_packages = {"pkg1"}
    result = mod_module_actions.apply_single_action(
        module_names, action, detected_packages
    )

    assert result == ["pkg2", "pkg2.sub"]


def test_apply_single_action_copy() -> None:
    """Test apply_single_action routes to copy handler."""
    module_names = ["pkg1"]
    action = make_module_action_full("pkg1", dest="pkg2", action="copy")
    detected_packages = {"pkg1"}
    result = mod_module_actions.apply_single_action(
        module_names, action, detected_packages
    )

    assert "pkg1" in result
    assert "pkg2" in result


def test_apply_single_action_delete() -> None:
    """Test apply_single_action routes to delete handler."""
    module_names = ["pkg1", "pkg2"]
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "action": "delete",
    }
    detected_packages = {"pkg1"}
    result = mod_module_actions.apply_single_action(
        module_names, action, detected_packages
    )

    assert result == ["pkg2"]


def test_apply_single_action_none() -> None:
    """Test apply_single_action with none action (no-op)."""
    module_names = ["pkg1", "pkg2"]
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "action": "none",
    }
    detected_packages = {"pkg1"}
    result = mod_module_actions.apply_single_action(
        module_names, action, detected_packages
    )

    assert result == ["pkg1", "pkg2"]


def test_apply_single_action_invalid_type_error() -> None:
    """Test apply_single_action with invalid action type raises error."""
    module_names = ["pkg1"]
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "action": "invalid",  # type: ignore[typeddict-item]
    }
    detected_packages = {"pkg1"}
    with pytest.raises(ValueError, match="Invalid action type"):
        mod_module_actions.apply_single_action(module_names, action, detected_packages)


def test_apply_single_action_default_move() -> None:
    """Test apply_single_action defaults to move."""
    module_names = ["pkg1"]
    action = make_module_action_full("pkg1", dest="pkg2")
    detected_packages = {"pkg1"}
    result = mod_module_actions.apply_single_action(
        module_names, action, detected_packages
    )

    assert result == ["pkg2"]
