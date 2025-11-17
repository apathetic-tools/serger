"""Tests for serger.module_actions.validate_action_source_exists."""

import pytest

import serger.config.config_types as mod_types
import serger.module_actions as mod_module_actions


def test_validate_action_source_exists_success() -> None:
    """Test that validation passes when source exists."""
    action: mod_types.ModuleActionFull = {"source": "pkg1"}
    available_modules = {"pkg1", "pkg2", "pkg3"}

    # Should not raise
    mod_module_actions.validate_action_source_exists(action, available_modules)


def test_validate_action_source_exists_error() -> None:
    """Test that validation fails when source doesn't exist."""
    action: mod_types.ModuleActionFull = {"source": "nonexistent"}
    available_modules = {"pkg1", "pkg2", "pkg3"}

    with pytest.raises(ValueError, match="does not exist"):
        mod_module_actions.validate_action_source_exists(action, available_modules)
