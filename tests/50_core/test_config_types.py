# tests/50_core/test_config_types.py

"""Tests for serger.config.config_types module action types."""

from pathlib import Path

import serger.config.config_types as mod_types  # noqa: TC001


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_module_action_type_literal() -> None:
    """Test ModuleActionType literal values."""
    valid_values = {"move", "copy", "delete", "none"}
    # Type checking ensures only these values are valid
    assert "move" in valid_values
    assert "copy" in valid_values
    assert "delete" in valid_values
    assert "none" in valid_values


def test_module_action_mode_literal() -> None:
    """Test ModuleActionMode literal values."""
    valid_values = {"preserve", "flatten"}
    assert "preserve" in valid_values
    assert "flatten" in valid_values


def test_module_action_scope_literal() -> None:
    """Test ModuleActionScope literal values."""
    valid_values = {"original", "shim"}
    assert "original" in valid_values
    assert "shim" in valid_values


def test_module_action_affects_literal() -> None:
    """Test ModuleActionAffects literal values."""
    valid_values = {"shims", "stitching", "both"}
    assert "shims" in valid_values
    assert "stitching" in valid_values
    assert "both" in valid_values


def test_module_action_cleanup_literal() -> None:
    """Test ModuleActionCleanup literal values."""
    valid_values = {"auto", "error", "ignore"}
    assert "auto" in valid_values
    assert "error" in valid_values
    assert "ignore" in valid_values


def test_module_action_full_typeddict() -> None:
    """Test ModuleActionFull TypedDict structure."""
    # Minimal action with just source (required)
    action_minimal: mod_types.ModuleActionFull = {"source": "mymodule"}
    assert action_minimal["source"] == "mymodule"

    # Full action with all fields
    action_full: mod_types.ModuleActionFull = {
        "source": "oldmodule",
        "source_path": "/path/to/oldmodule.py",
        "dest": "newmodule",
        "action": "move",
        "mode": "preserve",
        "scope": "shim",
        "affects": "both",
        "cleanup": "auto",
    }
    assert action_full["source"] == "oldmodule"
    assert action_full["dest"] == "newmodule"
    assert action_full["action"] == "move"
    assert action_full["mode"] == "preserve"
    assert action_full["scope"] == "shim"
    assert action_full["affects"] == "both"
    assert action_full["cleanup"] == "auto"


def test_module_action_simple_type() -> None:
    """Test ModuleActionSimple type (dict[str, str | None])."""
    # Simple format: dict[str, str | None]
    simple: mod_types.ModuleActionSimple = {
        "oldmodule": "newmodule",
        "deleteme": None,
    }
    assert simple["oldmodule"] == "newmodule"
    assert simple["deleteme"] is None


def test_module_actions_union_type() -> None:
    """Test ModuleActions union type accepts both formats."""
    # Dict format (simple)
    actions_dict: mod_types.ModuleActions = {"old": "new"}
    assert isinstance(actions_dict, dict)

    # List format (full)
    actions_list: mod_types.ModuleActions = [
        {"source": "old", "dest": "new", "action": "move"}
    ]
    assert isinstance(actions_list, list)
    assert len(actions_list) == 1


def test_root_config_has_module_actions() -> None:
    """Test RootConfig includes module_actions field."""
    # Dict format
    root_cfg_dict: mod_types.RootConfig = {
        "include": ["src/**"],
        "module_actions": {"old": "new"},
    }
    assert "module_actions" in root_cfg_dict
    assert isinstance(root_cfg_dict["module_actions"], dict)

    # List format
    root_cfg_list: mod_types.RootConfig = {
        "include": ["src/**"],
        "module_actions": [{"source": "old", "dest": "new"}],
    }
    assert "module_actions" in root_cfg_list
    assert isinstance(root_cfg_list["module_actions"], list)


def test_root_config_resolved_has_module_actions(tmp_path: Path) -> None:
    """Test RootConfigResolved includes module_actions field (normalized to list)."""
    test_root = tmp_path
    resolved_cfg: mod_types.RootConfigResolved = {
        "include": [],
        "exclude": [],
        "out": {
            "path": "dist/script.py",
            "root": test_root,
            "origin": "test",
        },
        "__meta__": {
            "cli_root": test_root,
            "config_root": test_root,
        },
        "strict_config": False,
        "respect_gitignore": True,
        "log_level": "info",
        "dry_run": False,
        "watch_interval": 1.0,
        "stitch_mode": "raw",
        "module_mode": "multi",
        "shim": "all",
        "internal_imports": "force_strip",
        "external_imports": "top",
        "comments_mode": "keep",
        "docstring_mode": "keep",
        "module_bases": ["src"],
        "post_processing": {
            "enabled": True,
            "category_order": [],
            "categories": {},
        },
        "module_actions": [{"source": "old", "dest": "new"}],
        "main_mode": "auto",
        "main_name": None,
        "disable_build_timestamp": False,
        "license_header": "",
        "display_name": "",
        "description": "",
        "authors": "",
        "repo": "",
    }
    assert "module_actions" in resolved_cfg
    assert isinstance(resolved_cfg["module_actions"], list)
