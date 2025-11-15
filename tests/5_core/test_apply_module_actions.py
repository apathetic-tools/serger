"""Tests for serger.module_actions.apply_module_actions."""

import serger.config.config_types as mod_types
import serger.module_actions as mod_module_actions


def test_apply_module_actions_single_move() -> None:
    """Test applying a single move action."""
    module_names = ["pkg1", "pkg1.sub"]
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "dest": "pkg2", "action": "move"}
    ]
    detected_packages = {"pkg1"}
    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )

    assert result == ["pkg2", "pkg2.sub"]


def test_apply_module_actions_multiple_actions() -> None:
    """Test applying multiple actions in sequence."""
    module_names = ["pkg1", "pkg1.sub", "pkg2", "pkg3"]
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "dest": "pkg1_new", "action": "move"},
        {"source": "pkg2", "action": "delete"},
    ]
    detected_packages = {"pkg1", "pkg2"}
    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )

    assert result == ["pkg1_new", "pkg1_new.sub", "pkg3"]


def test_apply_module_actions_sequence_matters() -> None:
    """Test that action sequence matters (later actions see transformed state)."""
    module_names = ["pkg1", "pkg1.sub"]
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "dest": "pkg2", "action": "move"},
        {"source": "pkg2.sub", "dest": "pkg2.renamed", "action": "move"},
    ]
    detected_packages = {"pkg1"}
    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )

    assert result == ["pkg2", "pkg2.renamed"]


def test_apply_module_actions_empty_list() -> None:
    """Test applying empty action list (no-op)."""
    module_names = ["pkg1", "pkg2"]
    actions: list[mod_types.ModuleActionFull] = []
    detected_packages = {"pkg1"}
    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )

    assert result == ["pkg1", "pkg2"]


def test_apply_module_actions_copy_then_move() -> None:
    """Test copy then move in sequence."""
    module_names = ["pkg1"]
    actions: list[mod_types.ModuleActionFull] = [
        {"source": "pkg1", "dest": "pkg2", "action": "copy"},
        {"source": "pkg1", "dest": "pkg3", "action": "move"},
    ]
    detected_packages = {"pkg1"}
    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )

    # After copy: [pkg1, pkg2]
    # After move: [pkg3, pkg2]
    assert "pkg3" in result
    assert "pkg2" in result
    assert "pkg1" not in result


def test_apply_module_actions_complex_scenario() -> None:
    """Test complex scenario with multiple action types."""
    module_names = [
        "apathetic_logs",
        "apathetic_logs.utils",
        "apathetic_logs.utils.text",
        "other_pkg",
        "other_pkg.sub",
    ]
    actions: list[mod_types.ModuleActionFull] = [
        {
            "source": "apathetic_logs",
            "dest": "grinch",
            "action": "move",
            "mode": "flatten",
        },
        {"source": "other_pkg.sub", "action": "delete"},
    ]
    detected_packages = {"apathetic_logs", "other_pkg"}
    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )

    # After move (flatten): [grinch, grinch.utils, grinch.text,
    #                        other_pkg, other_pkg.sub]
    # After delete: [grinch, grinch.utils, grinch.text, other_pkg]
    assert result == ["grinch", "grinch.utils", "grinch.text", "other_pkg"]
