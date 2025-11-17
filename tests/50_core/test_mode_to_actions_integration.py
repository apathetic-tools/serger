"""Tests for mode-to-actions conversion integration.

Tests the full flow: mode → actions → validation → application,
and combining mode-generated actions with user actions.
"""

import serger.config.config_types as mod_types
import serger.module_actions as mod_module_actions


def test_mode_generated_actions_pass_validation() -> None:
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


def test_mode_generated_actions_can_be_applied() -> None:
    """Test that mode-generated actions can be applied."""
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"
    module_names = ["pkg1", "pkg1.sub", "pkg2", "target"]

    # Generate actions from mode
    actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    # Apply actions
    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )

    # Should have moved pkg1 and pkg2 to target
    assert "target" in result
    assert "target.sub" in result
    assert "pkg1" not in result
    assert "pkg2" not in result


def test_mode_generated_actions_have_scope_original() -> None:
    """Test that mode-generated actions have scope: 'original'."""
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"

    actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    for action in actions:
        assert action["scope"] == "original"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_combine_mode_generated_and_user_actions() -> None:
    """Test combining mode-generated actions with user actions."""
    # pkg3 is not in detected_packages so mode actions won't move it
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"
    original_modules = {"pkg1", "pkg2", "pkg3", "target"}

    # Generate actions from mode (force mode moves pkg1, pkg2 to target)
    mode_actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    # User actions (move pkg3 to pkg3_new)
    # User actions have scope: "shim" by default
    user_actions: list[mod_types.ModuleActionFull] = [
        {
            "source": "pkg3",
            "dest": "pkg3_new",
            "action": "move",
            "mode": "preserve",
            "scope": "shim",
            "affects": "shims",
            "cleanup": "auto",
        }
    ]

    # Combine: mode actions first, then user actions
    combined_actions = mode_actions + user_actions

    # Should pass validation
    mod_module_actions.validate_module_actions(
        combined_actions, original_modules, detected_packages
    )

    # Apply combined actions
    module_names = ["pkg1", "pkg1.sub", "pkg2", "pkg3", "target"]
    result = mod_module_actions.apply_module_actions(
        module_names, combined_actions, detected_packages
    )

    # Mode actions: pkg1, pkg2 -> target
    # User action: pkg3 -> pkg3_new
    assert "target" in result
    assert "target.sub" in result
    assert "pkg3_new" in result
    assert "pkg1" not in result
    assert "pkg2" not in result
    assert "pkg3" not in result


def test_full_flow_mode_to_application() -> None:
    """Test full flow: mode → actions → validation → application."""
    detected_packages = {"pkg1", "pkg2.sub", "target"}
    package_name = "target"
    original_modules = {"pkg1", "pkg2", "pkg2.sub", "target"}

    # Step 1: Generate actions from mode (unify mode)
    actions = mod_module_actions.generate_actions_from_mode(
        "unify", detected_packages, package_name
    )

    # Step 2: Validate actions
    mod_module_actions.validate_module_actions(
        actions, original_modules, detected_packages
    )

    # Step 3: Apply actions
    module_names = ["pkg1", "pkg1.sub", "pkg2", "pkg2.sub", "target"]
    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )

    # Unify mode: pkg1 -> target.pkg1, pkg2.sub -> target.pkg2.sub
    assert "target.pkg1" in result
    assert "target.pkg1.sub" in result
    assert "target.pkg2.sub" in result
    assert "pkg1" not in result
    assert "pkg2.sub" not in result


def test_mode_generated_actions_empty_detected_packages() -> None:
    """Test mode-generated actions with empty detected_packages."""
    detected_packages: set[str] = set()
    package_name = "target"
    original_modules = {"target"}

    # Generate actions from mode
    actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    # Should be empty
    assert actions == []

    # Should pass validation (empty list is valid)
    mod_module_actions.validate_module_actions(
        actions, original_modules, detected_packages
    )

    # Should be no-op when applied
    module_names = ["target"]
    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )
    assert result == ["target"]


def test_mode_generated_actions_package_name_in_detected() -> None:
    """Test when package_name is in detected_packages."""
    detected_packages = {"pkg1", "target"}
    package_name = "target"
    original_modules = {"pkg1", "target"}

    # Generate actions from mode
    actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    # Should only have action for pkg1, not target
    assert len(actions) == 1
    assert actions[0]["source"] == "pkg1"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert "target" not in {
        a["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        for a in actions
    }

    # Should pass validation
    mod_module_actions.validate_module_actions(
        actions, original_modules, detected_packages
    )


def test_mode_generated_actions_multiple_packages_same_root() -> None:
    """Test multiple packages with same root name."""
    detected_packages = {"pkg1", "pkg1.sub", "pkg1.nested", "target"}
    package_name = "target"
    original_modules = {"pkg1", "pkg1.sub", "pkg1.nested", "target"}

    # Force mode: only root packages (pkg1), not subpackages
    actions_force = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )
    assert len(actions_force) == 1
    assert actions_force[0]["source"] == "pkg1"  # pyright: ignore[reportTypedDictNotRequiredAccess]

    # Unify mode: all packages including subpackages
    actions_unify = mod_module_actions.generate_actions_from_mode(
        "unify", detected_packages, package_name
    )
    sources = {
        a["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        for a in actions_unify
    }
    assert sources == {"pkg1", "pkg1.sub", "pkg1.nested"}

    # Both should pass validation
    mod_module_actions.validate_module_actions(
        actions_force, original_modules, detected_packages
    )
    mod_module_actions.validate_module_actions(
        actions_unify, original_modules, detected_packages
    )


def test_mode_generated_actions_force_flat_mode() -> None:
    """Test force_flat mode generates actions with flatten mode."""
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"
    original_modules = {"pkg1", "pkg1.sub", "pkg2", "target"}

    actions = mod_module_actions.generate_actions_from_mode(
        "force_flat", detected_packages, package_name
    )

    # All actions should have mode: "flatten"
    for action in actions:
        assert action["mode"] == "flatten"  # pyright: ignore[reportTypedDictNotRequiredAccess]
        assert action["scope"] == "original"  # pyright: ignore[reportTypedDictNotRequiredAccess]

    # Should pass validation
    mod_module_actions.validate_module_actions(
        actions, original_modules, detected_packages
    )

    # Apply actions
    module_names = ["pkg1", "pkg1.sub", "pkg2", "target"]
    result = mod_module_actions.apply_module_actions(
        module_names, actions, detected_packages
    )

    # Flatten mode: pkg1.sub -> target.sub (not target.pkg1.sub)
    assert "target" in result
    assert "target.sub" in result
    assert "target.pkg1" not in result


def test_combine_mode_and_user_actions_sequence() -> None:
    """Test that mode actions come before user actions in sequence."""
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"
    original_modules = {"pkg1", "pkg2", "target"}

    # Mode actions: pkg1 -> target, pkg2 -> target
    mode_actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    # User action: target -> target_new (depends on mode action)
    # User actions have scope: "shim" by default
    user_actions: list[mod_types.ModuleActionFull] = [
        {
            "source": "target",
            "dest": "target_new",
            "action": "move",
            "mode": "preserve",
            "scope": "shim",
            "affects": "shims",
            "cleanup": "auto",
        }
    ]

    # Combine: mode first, then user
    combined = mode_actions + user_actions

    # Should pass validation
    mod_module_actions.validate_module_actions(
        combined, original_modules, detected_packages
    )

    # Apply: mode moves pkg1, pkg2 to target, then user moves target to target_new
    module_names = ["pkg1", "pkg2", "target"]
    result = mod_module_actions.apply_module_actions(
        module_names, combined, detected_packages
    )

    # Final result: target_new (contains pkg1, pkg2)
    assert "target_new" in result
    assert "target" not in result
    assert "pkg1" not in result
    assert "pkg2" not in result


def test_mode_generated_actions_all_have_defaults() -> None:
    """Test that all mode-generated actions have all required defaults."""
    detected_packages = {"pkg1", "pkg2"}
    package_name = "target"

    actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    for action in actions:
        # All fields should be present
        assert "source" in action
        assert "dest" in action
        assert "action" in action
        assert "mode" in action
        assert "scope" in action
        assert "affects" in action
        assert "cleanup" in action

        # Check default values
        assert action["action"] == "move"  # pyright: ignore[reportTypedDictNotRequiredAccess]
        assert action["scope"] == "original"  # pyright: ignore[reportTypedDictNotRequiredAccess]
        assert action["affects"] == "shims"  # pyright: ignore[reportTypedDictNotRequiredAccess]
        assert action["cleanup"] == "auto"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_mode_generated_actions_validation_scope_filter() -> None:
    """Test that mode-generated actions work with validation scope filter."""
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"
    original_modules = {"pkg1", "pkg2", "target"}

    actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    # All mode-generated actions have scope: "original"
    # Validation with scope="original" should include them
    mod_module_actions.validate_module_actions(
        actions, original_modules, detected_packages, scope="original"
    )

    # Validation with scope="shim" should filter them out (but still pass)
    mod_module_actions.validate_module_actions(
        actions, original_modules, detected_packages, scope="shim"
    )


def test_mode_generated_actions_unify_preserve_same_as_unify() -> None:
    """Test that unify_preserve generates same actions as unify."""
    detected_packages = {"pkg1", "pkg2.sub", "target"}
    package_name = "target"

    actions_unify = mod_module_actions.generate_actions_from_mode(
        "unify", detected_packages, package_name
    )
    actions_unify_preserve = mod_module_actions.generate_actions_from_mode(
        "unify_preserve", detected_packages, package_name
    )

    # Should be identical
    assert len(actions_unify) == len(actions_unify_preserve)

    # Sort for comparison
    actions_unify_sorted = sorted(
        actions_unify,
        key=lambda a: a["source"],  # pyright: ignore[reportTypedDictNotRequiredAccess]
    )
    actions_unify_preserve_sorted = sorted(
        actions_unify_preserve,
        key=lambda a: a["source"],  # pyright: ignore[reportTypedDictNotRequiredAccess]
    )

    for a1, a2 in zip(
        actions_unify_sorted, actions_unify_preserve_sorted, strict=False
    ):
        assert a1["source"] == a2["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        assert a1["dest"] == a2["dest"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        assert a1["mode"] == a2["mode"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        assert a1["scope"] == a2["scope"]  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_mode_generated_actions_multi_none_flat_empty() -> None:
    """Test that multi, none, flat modes return empty actions."""
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"

    for mode in ["multi", "none", "flat"]:
        actions = mod_module_actions.generate_actions_from_mode(
            mode, detected_packages, package_name
        )
        assert actions == []

        # Empty actions should pass validation
        original_modules = {"pkg1", "pkg2", "target"}
        mod_module_actions.validate_module_actions(
            actions, original_modules, detected_packages
        )
