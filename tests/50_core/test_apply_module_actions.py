"""Tests for serger.module_actions.apply_module_actions."""

import serger.config.config_types as mod_types
import serger.module_actions as mod_module_actions
from tests.utils.buildconfig import make_module_action_full


def test_apply_module_actions_single_move() -> None:
    """Test applying a single move action."""
    module_names = ["pkg1", "pkg1.sub"]
    actions: list[mod_types.ModuleActionFull] = [
        make_module_action_full("pkg1", dest="pkg2")
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
        make_module_action_full("pkg1", dest="pkg1_new"),
        make_module_action_full("pkg2", action="delete"),
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
        make_module_action_full("pkg1", dest="pkg2"),
        make_module_action_full("pkg2.sub", dest="pkg2.renamed"),
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
        make_module_action_full("pkg1", dest="pkg2", action="copy"),
        make_module_action_full("pkg1", dest="pkg3"),
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
        make_module_action_full("apathetic_logs", dest="grinch", mode="flatten"),
        make_module_action_full("other_pkg.sub", action="delete"),
    ]
    detected_packages = {"apathetic_logs", "other_pkg"}
    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )

    # After move (flatten): [grinch, grinch.utils, grinch.text,
    #                        other_pkg, other_pkg.sub]
    # After delete: [grinch, grinch.utils, grinch.text, other_pkg]
    assert result == ["grinch", "grinch.utils", "grinch.text", "other_pkg"]


def test_apply_module_actions_mode_generated_force() -> None:
    """Test applying mode-generated actions from force mode."""
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"
    module_names = ["pkg1", "pkg1.sub", "pkg2", "target"]

    actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )

    # Force mode: pkg1, pkg2 -> target
    assert "target" in result
    assert "target.sub" in result
    assert "pkg1" not in result
    assert "pkg2" not in result


def test_apply_module_actions_mode_generated_unify() -> None:
    """Test applying mode-generated actions from unify mode."""
    detected_packages = {"pkg1", "pkg2.sub", "target"}
    package_name = "target"
    module_names = ["pkg1", "pkg1.sub", "pkg2", "pkg2.sub", "target"]

    actions = mod_module_actions.generate_actions_from_mode(
        "unify", detected_packages, package_name
    )

    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )

    # Unify mode: pkg1 -> target.pkg1, pkg2.sub -> target.pkg2.sub
    assert "target.pkg1" in result
    assert "target.pkg1.sub" in result
    assert "target.pkg2.sub" in result
    assert "pkg1" not in result
    assert "pkg2.sub" not in result


def test_apply_module_actions_mode_generated_force_flat() -> None:
    """Test applying mode-generated actions from force_flat mode."""
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"
    module_names = ["pkg1", "pkg1.sub", "pkg2", "target"]

    actions = mod_module_actions.generate_actions_from_mode(
        "force_flat", detected_packages, package_name
    )

    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )

    # Force_flat mode: pkg1, pkg2 -> target (flatten)
    # pkg1.sub -> target.sub (not target.pkg1.sub)
    assert "target" in result
    assert "target.sub" in result
    assert "target.pkg1" not in result
    assert "pkg1" not in result
    assert "pkg2" not in result


def test_apply_module_actions_combine_mode_and_user() -> None:
    """Test applying combined mode-generated and user actions."""
    # pkg3 is not in detected_packages so mode actions won't move it
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"
    module_names = ["pkg1", "pkg2", "pkg3", "target"]

    # Mode actions: pkg1, pkg2 -> target
    mode_actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    # User action: pkg3 -> pkg3_new
    user_actions: list[mod_types.ModuleActionFull] = [
        make_module_action_full("pkg3", dest="pkg3_new")
    ]

    # Combine: mode first, then user
    combined = mode_actions + user_actions
    result = mod_module_actions.apply_module_actions(
        module_names, combined, detected_packages
    )

    # Mode: pkg1, pkg2 -> target
    # User: pkg3 -> pkg3_new
    assert "target" in result
    assert "pkg3_new" in result
    assert "pkg1" not in result
    assert "pkg2" not in result
    assert "pkg3" not in result


def test_apply_module_actions_rename_top_level() -> None:
    """Test renaming a top-level module (pkg1 -> pkg2)."""
    module_names = ["pkg1", "pkg1.sub"]
    actions: list[mod_types.ModuleActionFull] = [
        make_module_action_full("pkg1", dest="pkg2", action="rename")
    ]
    detected_packages = {"pkg1"}
    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )

    # Rename pkg1 -> pkg2 (top-level rename)
    assert result == ["pkg2", "pkg2.sub"]


def test_apply_module_actions_rename_submodule() -> None:
    """Test renaming a submodule (pkg1.stuff -> pkg1.utils)."""
    module_names = ["pkg1", "pkg1.stuff", "pkg1.stuff.sub"]
    actions: list[mod_types.ModuleActionFull] = [
        make_module_action_full("pkg1.stuff", dest="utils", action="rename")
    ]
    detected_packages = {"pkg1"}
    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )

    # Rename pkg1.stuff -> pkg1.utils
    assert "pkg1" in result
    assert "pkg1.utils" in result
    assert "pkg1.utils.sub" in result
    assert "pkg1.stuff" not in result
    assert "pkg1.stuff.sub" not in result


def test_apply_module_actions_rename_with_submodules() -> None:
    """Test that rename preserves submodule structure."""
    module_names = [
        "pkg1",
        "pkg1.stuff",
        "pkg1.stuff.sub1",
        "pkg1.stuff.sub2",
        "pkg1.other",
    ]
    actions: list[mod_types.ModuleActionFull] = [
        make_module_action_full("pkg1.stuff", dest="utils", action="rename")
    ]
    detected_packages = {"pkg1"}
    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )

    # Rename pkg1.stuff -> pkg1.utils, preserving submodules
    assert "pkg1" in result
    assert "pkg1.utils" in result
    assert "pkg1.utils.sub1" in result
    assert "pkg1.utils.sub2" in result
    assert "pkg1.other" in result
    assert "pkg1.stuff" not in result
    assert "pkg1.stuff.sub1" not in result
    assert "pkg1.stuff.sub2" not in result
