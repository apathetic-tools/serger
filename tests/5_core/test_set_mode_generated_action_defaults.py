"""Tests for serger.module_actions.set_mode_generated_action_defaults."""

import serger.config.config_types as mod_types
import serger.module_actions as mod_module_actions


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
