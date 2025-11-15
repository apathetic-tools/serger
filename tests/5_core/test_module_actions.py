"""Tests for serger.module_actions."""

import pytest

import serger.config.config_types as mod_types
import serger.module_actions as mod_module_actions


# ---------------------------------------------------------------------------
# Tests for set_mode_generated_action_defaults
# ---------------------------------------------------------------------------


def test_set_mode_generated_action_defaults_sets_all_defaults() -> None:
    """Test that all defaults are set correctly for minimal action."""
    action: mod_types.ModuleActionFull = {"source": "pkg1"}
    result = mod_module_actions.set_mode_generated_action_defaults(action)

    assert result["source"] == "pkg1"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert result["action"] == "move"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert result["mode"] == "preserve"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert result["scope"] == "original"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert result["affects"] == "shims"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert result["cleanup"] == "auto"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_set_mode_generated_action_defaults_always_sets_scope_original() -> None:
    """Test that scope is always set to 'original' for mode-generated actions."""
    # Even if scope is already set to something else, it should be overridden
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "scope": "shim",  # Should be overridden
    }
    result = mod_module_actions.set_mode_generated_action_defaults(action)

    assert result["scope"] == "original"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_set_mode_generated_action_defaults_preserves_existing_fields() -> None:
    """Test that existing fields are not overridden (except scope)."""
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "dest": "pkg2",
        "action": "copy",
        "mode": "flatten",
        "affects": "both",
        "cleanup": "error",
    }
    result = mod_module_actions.set_mode_generated_action_defaults(action)

    assert result["source"] == "pkg1"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert result["dest"] == "pkg2"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert result["action"] == "copy"  # pyright: ignore[reportTypedDictNotRequiredAccess]  # Preserved
    assert result["mode"] == "flatten"  # pyright: ignore[reportTypedDictNotRequiredAccess]  # Preserved
    assert result["scope"] == "original"  # pyright: ignore[reportTypedDictNotRequiredAccess]  # Always set
    assert result["affects"] == "both"  # pyright: ignore[reportTypedDictNotRequiredAccess]  # Preserved
    assert result["cleanup"] == "error"  # pyright: ignore[reportTypedDictNotRequiredAccess]  # Preserved


def test_set_mode_generated_action_defaults_with_source_path() -> None:
    """Test that source_path is preserved if present."""
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "source_path": "src/pkg1.py",
    }
    result = mod_module_actions.set_mode_generated_action_defaults(action)

    assert result["source"] == "pkg1"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert result["source_path"] == "src/pkg1.py"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert result["scope"] == "original"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_set_mode_generated_action_defaults_with_delete_action() -> None:
    """Test that delete action works correctly (no dest)."""
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "action": "delete",
    }
    result = mod_module_actions.set_mode_generated_action_defaults(action)

    assert result["source"] == "pkg1"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert result["action"] == "delete"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert result["scope"] == "original"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert "dest" not in result


def test_set_mode_generated_action_defaults_does_not_mutate_input() -> None:
    """Test that the input action is not mutated."""
    action: mod_types.ModuleActionFull = {"source": "pkg1"}
    original_action = dict(action)

    result = mod_module_actions.set_mode_generated_action_defaults(action)

    # Input should be unchanged
    assert action == original_action
    # Result should have defaults
    assert result["scope"] == "original"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert result["action"] == "move"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_set_mode_generated_action_defaults_all_fields_present() -> None:
    """Test that all required fields are present in result."""
    action: mod_types.ModuleActionFull = {"source": "pkg1"}
    result = mod_module_actions.set_mode_generated_action_defaults(action)

    # All fields should be present
    assert "source" in result
    assert "action" in result
    assert "mode" in result
    assert "scope" in result
    assert "affects" in result
    assert "cleanup" in result


# ---------------------------------------------------------------------------
# Tests for validate_action_source_exists
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Tests for validate_action_dest
# ---------------------------------------------------------------------------


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
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "action": "delete",
        "dest": "pkg2",
    }
    existing_modules = {"pkg1", "pkg2"}

    with pytest.raises(ValueError, match="must not have 'dest' field"):
        mod_module_actions.validate_action_dest(action, existing_modules)


def test_validate_action_dest_move_with_dest_success() -> None:
    """Test that move action with dest is valid."""
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "action": "move",
        "dest": "pkg2_new",
    }
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
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "action": "move",
        "dest": "pkg2",  # Conflicts with existing
    }
    existing_modules = {"pkg1", "pkg2"}

    with pytest.raises(ValueError, match="conflicts with existing module"):
        mod_module_actions.validate_action_dest(action, existing_modules)


def test_validate_action_dest_copy_with_dest_success() -> None:
    """Test that copy action with dest is valid (even if conflicts)."""
    action: mod_types.ModuleActionFull = {
        "source": "pkg1",
        "action": "copy",
        "dest": "pkg2",  # Copy can overwrite
    }
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


# ---------------------------------------------------------------------------
# Tests for validate_no_circular_moves
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Tests for validate_no_conflicting_operations
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Tests for validate_module_actions
# ---------------------------------------------------------------------------


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
