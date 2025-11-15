"""Tests for serger.module_actions.generate_actions_from_mode."""

import pytest

import serger.module_actions as mod_module_actions


def test_generate_actions_from_mode_force() -> None:
    """Test that 'force' mode generates correct actions for root packages."""
    detected_packages = {"pkg1", "pkg2", "pkg3.sub", "target"}
    package_name = "target"

    actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    # Should generate actions for root packages only (pkg1, pkg2), not pkg3.sub
    # Should exclude package_name (target)
    assert len(actions) == 2  # noqa: PLR2004

    # Check pkg1 action
    pkg1_action = next(
        a
        for a in actions
        if a["source"] == "pkg1"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    )
    assert pkg1_action["dest"] == "target"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert pkg1_action["mode"] == "preserve"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert pkg1_action["scope"] == "original"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert pkg1_action["action"] == "move"  # pyright: ignore[reportTypedDictNotRequiredAccess]

    # Check pkg2 action
    pkg2_action = next(
        a
        for a in actions
        if a["source"] == "pkg2"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    )
    assert pkg2_action["dest"] == "target"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert pkg2_action["mode"] == "preserve"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert pkg2_action["scope"] == "original"  # pyright: ignore[reportTypedDictNotRequiredAccess]

    # Verify all actions have scope: "original"
    for action in actions:
        assert action["scope"] == "original"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_generate_actions_from_mode_force_flat() -> None:
    """Test that 'force_flat' mode generates correct actions with flatten mode."""
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"

    actions = mod_module_actions.generate_actions_from_mode(
        "force_flat", detected_packages, package_name
    )

    assert len(actions) == 2  # noqa: PLR2004

    # Check that all actions have mode: "flatten"
    for action in actions:
        assert action["mode"] == "flatten"  # pyright: ignore[reportTypedDictNotRequiredAccess]
        assert action["dest"] == "target"  # pyright: ignore[reportTypedDictNotRequiredAccess]
        assert action["scope"] == "original"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_generate_actions_from_mode_unify() -> None:
    """Test that 'unify' mode generates correct actions for all packages."""
    detected_packages = {"pkg1", "pkg2", "pkg3.sub", "target"}
    package_name = "target"

    actions = mod_module_actions.generate_actions_from_mode(
        "unify", detected_packages, package_name
    )

    # Should generate actions for all packages (pkg1, pkg2, pkg3.sub), not target
    assert len(actions) == 3  # noqa: PLR2004

    # Check pkg1 action
    pkg1_action = next(
        a
        for a in actions
        if a["source"] == "pkg1"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    )
    assert pkg1_action["dest"] == "target.pkg1"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert pkg1_action["mode"] == "preserve"  # pyright: ignore[reportTypedDictNotRequiredAccess]

    # Check pkg2 action
    pkg2_action = next(
        a
        for a in actions
        if a["source"] == "pkg2"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    )
    assert pkg2_action["dest"] == "target.pkg2"  # pyright: ignore[reportTypedDictNotRequiredAccess]

    # Check pkg3.sub action (subpackage)
    pkg3_sub_action = next(
        a
        for a in actions
        if a["source"] == "pkg3.sub"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    )
    assert pkg3_sub_action["dest"] == "target.pkg3.sub"  # pyright: ignore[reportTypedDictNotRequiredAccess]

    # Verify all actions have scope: "original"
    for action in actions:
        assert action["scope"] == "original"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_generate_actions_from_mode_unify_preserve() -> None:
    """Test that 'unify_preserve' mode is same as 'unify'."""
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"

    actions_unify = mod_module_actions.generate_actions_from_mode(
        "unify", detected_packages, package_name
    )
    actions_unify_preserve = mod_module_actions.generate_actions_from_mode(
        "unify_preserve", detected_packages, package_name
    )

    # Should produce same results
    assert len(actions_unify) == len(actions_unify_preserve) == 2  # noqa: PLR2004

    # Sort by source for comparison
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


def test_generate_actions_from_mode_multi() -> None:
    """Test that 'multi' mode returns empty list."""
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"

    actions = mod_module_actions.generate_actions_from_mode(
        "multi", detected_packages, package_name
    )

    assert actions == []


def test_generate_actions_from_mode_none() -> None:
    """Test that 'none' mode returns empty list."""
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"

    actions = mod_module_actions.generate_actions_from_mode(
        "none", detected_packages, package_name
    )

    assert actions == []


def test_generate_actions_from_mode_flat() -> None:
    """Test that 'flat' mode returns empty list (cannot be expressed as actions)."""
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"

    actions = mod_module_actions.generate_actions_from_mode(
        "flat", detected_packages, package_name
    )

    assert actions == []


def test_generate_actions_from_mode_excludes_package_name() -> None:
    """Test that package_name is excluded from generated actions."""
    detected_packages = {"pkg1", "pkg2", "target"}
    package_name = "target"

    # Test with force mode
    actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    # Should only have actions for pkg1 and pkg2, not target
    sources = {
        a["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        for a in actions
    }
    assert "target" not in sources
    assert sources == {"pkg1", "pkg2"}

    # Test with unify mode
    actions_unify = mod_module_actions.generate_actions_from_mode(
        "unify", detected_packages, package_name
    )

    sources_unify = {
        a["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        for a in actions_unify
    }
    assert "target" not in sources_unify
    assert sources_unify == {"pkg1", "pkg2"}


def test_generate_actions_from_mode_sorted_order() -> None:
    """Test that actions are generated in sorted order for determinism."""
    detected_packages = {"zebra", "alpha", "beta", "target"}
    package_name = "target"

    actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    # Actions should be in sorted order by source
    sources = [
        a["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        for a in actions
    ]
    assert sources == sorted(sources)
    assert sources == ["alpha", "beta", "zebra"]


def test_generate_actions_from_mode_all_actions_have_scope_original() -> None:
    """Test that all generated actions have scope: 'original'."""
    detected_packages = {"pkg1", "pkg2", "pkg3.sub"}
    package_name = "target"

    # Test all modes that generate actions
    for mode in ["force", "force_flat", "unify", "unify_preserve"]:
        actions = mod_module_actions.generate_actions_from_mode(
            mode, detected_packages, package_name
        )

        for action in actions:
            assert action["scope"] == "original"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_generate_actions_from_mode_all_actions_have_defaults() -> None:
    """Test that all generated actions have defaults applied."""
    detected_packages = {"pkg1", "pkg2"}
    package_name = "target"

    actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    for action in actions:
        # All fields should be present (defaults applied)
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


def test_generate_actions_from_mode_invalid_mode() -> None:
    """Test that invalid mode raises ValueError."""
    detected_packages = {"pkg1"}
    package_name = "target"

    with pytest.raises(ValueError, match="Invalid module_mode") as exc_info:
        mod_module_actions.generate_actions_from_mode(
            "invalid_mode", detected_packages, package_name
        )
    assert "invalid_mode" in str(exc_info.value)


def test_generate_actions_from_mode_empty_packages() -> None:
    """Test empty detected_packages returns empty list for action-generating modes."""
    detected_packages: set[str] = set()
    package_name = "target"

    # Modes that generate actions should return empty list
    for mode in ["force", "force_flat", "unify", "unify_preserve"]:
        actions = mod_module_actions.generate_actions_from_mode(
            mode, detected_packages, package_name
        )
        assert actions == []

    # Modes that don't generate actions should still return empty list
    for mode in ["multi", "none", "flat"]:
        actions = mod_module_actions.generate_actions_from_mode(
            mode, detected_packages, package_name
        )
        assert actions == []


def test_generate_actions_from_mode_only_package_name() -> None:
    """Test when only package_name is in detected_packages, no actions generated."""
    detected_packages = {"target"}
    package_name = "target"

    # All modes should return empty list (nothing to move/unify)
    modes = ["force", "force_flat", "unify", "unify_preserve", "multi", "none", "flat"]
    for mode in modes:
        actions = mod_module_actions.generate_actions_from_mode(
            mode, detected_packages, package_name
        )
        assert actions == []


def test_generate_actions_from_mode_force_only_root_packages() -> None:
    """Test that 'force' mode only operates on root packages (no dots)."""
    detected_packages = {"pkg1", "pkg2.sub", "pkg3.sub.nested", "target"}
    package_name = "target"

    actions = mod_module_actions.generate_actions_from_mode(
        "force", detected_packages, package_name
    )

    # Should only have action for pkg1 (root package), not subpackages
    assert len(actions) == 1
    assert actions[0]["source"] == "pkg1"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert "pkg2.sub" not in {
        a["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        for a in actions
    }
    assert "pkg3.sub.nested" not in {
        a["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        for a in actions
    }


def test_generate_actions_from_mode_unify_includes_subpackages() -> None:
    """Test that 'unify' mode includes subpackages (packages with dots)."""
    detected_packages = {"pkg1", "pkg2.sub", "pkg3.sub.nested", "target"}
    package_name = "target"

    actions = mod_module_actions.generate_actions_from_mode(
        "unify", detected_packages, package_name
    )

    # Should have actions for all packages including subpackages
    sources = {
        a["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        for a in actions
    }
    assert sources == {"pkg1", "pkg2.sub", "pkg3.sub.nested"}

    # Check destinations
    pkg1_action = next(
        a
        for a in actions
        if a["source"] == "pkg1"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    )
    assert pkg1_action["dest"] == "target.pkg1"  # pyright: ignore[reportTypedDictNotRequiredAccess]

    pkg2_sub_action = next(
        a
        for a in actions
        if a["source"] == "pkg2.sub"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    )
    assert pkg2_sub_action["dest"] == "target.pkg2.sub"  # pyright: ignore[reportTypedDictNotRequiredAccess]

    pkg3_sub_nested_action = next(
        a
        for a in actions
        if a["source"] == "pkg3.sub.nested"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    )
    assert pkg3_sub_nested_action["dest"] == "target.pkg3.sub.nested"  # pyright: ignore[reportTypedDictNotRequiredAccess]
