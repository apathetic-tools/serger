"""Tests for serger.module_actions.validate_module_actions."""

import pytest

import serger.config.config_types as mod_types
import serger.module_actions as mod_module_actions


def test_validate_module_actions_valid_success() -> None:
    """Test that validation passes for valid actions."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "move", "dest": "pkg1_new"},
        {"source": "pkg2", "action": "copy", "dest": "pkg2_new"},
        {"source": "pkg3", "action": "delete"},
    ]
    original_modules = {"pkg1", "pkg2", "pkg3"}
    detected_packages = {"pkg1", "pkg2"}

    # Should not raise
    mod_module_actions.validate_module_actions(
        actions, original_modules, detected_packages
    )


def test_validate_module_actions_source_not_exists_error() -> None:
    """Test that validation fails when source doesn't exist."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "nonexistent", "action": "move", "dest": "pkg1_new"},
    ]
    original_modules = {"pkg1", "pkg2"}
    detected_packages = {"pkg1"}

    with pytest.raises(ValueError, match="does not exist"):
        mod_module_actions.validate_module_actions(
            actions, original_modules, detected_packages
        )


def test_validate_module_actions_scope_filter_original() -> None:
    """Test that scope filter works for 'original' scope."""
    actions: list[mod_types.ModuleActionFull] = [
        {
            "source": "pkg1",
            "action": "move",
            "dest": "pkg1_new",
            "scope": "original",
        },
        {
            "source": "nonexistent",
            "action": "move",
            "dest": "pkg2_new",
            "scope": "shim",  # Should be ignored
        },
    ]
    original_modules = {"pkg1", "pkg2"}
    detected_packages = {"pkg1"}

    # Should not raise (shim action with invalid source is ignored)
    mod_module_actions.validate_module_actions(
        actions, original_modules, detected_packages, scope="original"
    )


def test_validate_module_actions_scope_filter_shim() -> None:
    """Test that scope filter works for 'shim' scope."""
    actions: list[mod_types.ModuleActionFull] = [
        {
            "source": "nonexistent",
            "action": "move",
            "dest": "pkg1_new",
            "scope": "original",  # Should be ignored
        },
        {
            "source": "pkg2",
            "action": "move",
            "dest": "pkg2_new",
            "scope": "shim",
        },
    ]
    original_modules = {"pkg1", "pkg2"}
    detected_packages = {"pkg1"}

    # Should not raise (original action with invalid source is ignored)
    mod_module_actions.validate_module_actions(
        actions, original_modules, detected_packages, scope="shim"
    )


def test_validate_module_actions_empty_list_success() -> None:
    """Test that validation passes for empty action list."""
    actions: list[mod_types.ModuleActionFull] = []
    original_modules = {"pkg1", "pkg2"}
    detected_packages = {"pkg1"}

    # Should not raise
    mod_module_actions.validate_module_actions(
        actions, original_modules, detected_packages
    )


def test_validate_module_actions_scope_filter_no_matches_success() -> None:
    """Test that validation passes when scope filter matches no actions."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "move", "dest": "pkg1_new", "scope": "shim"},
    ]
    original_modules = {"pkg1", "pkg2"}
    detected_packages = {"pkg1"}

    # Should not raise (filtered to empty list)
    mod_module_actions.validate_module_actions(
        actions, original_modules, detected_packages, scope="original"
    )


def test_validate_module_actions_circular_move_error() -> None:
    """Test that validation fails for circular moves."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "move", "dest": "pkg2"},
        {"source": "pkg2", "action": "move", "dest": "pkg1"},
    ]
    original_modules = {"pkg1", "pkg2"}
    detected_packages = {"pkg1"}

    with pytest.raises(ValueError, match="Circular move chain detected"):
        mod_module_actions.validate_module_actions(
            actions, original_modules, detected_packages
        )


def test_validate_module_actions_conflicting_operations_error() -> None:
    """Test that validation fails for conflicting operations."""
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "action": "move", "dest": "pkg1_new"},
        {"source": "pkg1", "action": "delete"},  # Conflict
    ]
    original_modules = {"pkg1", "pkg2"}
    detected_packages = {"pkg1"}

    with pytest.raises(ValueError, match="Cannot delete module 'pkg1'"):
        mod_module_actions.validate_module_actions(
            actions, original_modules, detected_packages
        )


def test_validate_module_actions_mode_generated_actions() -> None:
    """Test that mode-generated actions pass validation."""
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"
    original_modules = {"pkg1", "pkg2", "target"}

    # Generate actions from mode
    actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    # Should pass validation
    mod_module_actions.validate_module_actions(
        actions, original_modules, detected_packages
    )


def test_validate_module_actions_mode_generated_with_scope_filter() -> None:
    """Test mode-generated actions with scope filter."""
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"
    original_modules = {"pkg1", "pkg2", "target"}

    actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    # All mode-generated actions have scope: "original"
    # Should pass with scope="original" filter
    mod_module_actions.validate_module_actions(
        actions, original_modules, detected_packages, scope="original"
    )

    # Should also pass with scope="shim" filter (filters to empty, but valid)
    mod_module_actions.validate_module_actions(
        actions, original_modules, detected_packages, scope="shim"
    )


def test_validate_module_actions_combine_mode_and_user() -> None:
    """Test validation of combined mode-generated and user actions."""
    detected_packages = {"pkg1", "pkg2", "pkg3", "target"}
    package_name = "target"
    original_modules = {"pkg1", "pkg2", "pkg3", "target"}

    # Mode-generated actions
    mode_actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    # User actions
    user_actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg3", "dest": "pkg3_new", "action": "move"}
    ]

    # Combined actions should pass validation
    combined = mode_actions + user_actions
    mod_module_actions.validate_module_actions(
        combined, original_modules, detected_packages
    )
