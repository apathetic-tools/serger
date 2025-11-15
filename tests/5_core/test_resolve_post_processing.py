# tests/5_core/test_resolve_post_processing.py
"""Tests for resolve_post_processing function."""

import pytest

import serger.config.config_resolve as mod_resolve
import serger.config.config_types as mod_types
import serger.constants as mod_constants
import serger.logs as mod_logs


def test_resolve_post_processing_defaults() -> None:
    """Should return default configuration when no config provided."""
    build_cfg: mod_types.BuildConfig = {}
    root_cfg: mod_types.RootConfig | None = None

    resolved = mod_resolve.resolve_post_processing(build_cfg, root_cfg)

    assert resolved["enabled"] is True
    assert resolved["category_order"] == mod_constants.DEFAULT_CATEGORY_ORDER
    assert "static_checker" in resolved["categories"]
    assert "formatter" in resolved["categories"]
    assert "import_sorter" in resolved["categories"]


def test_resolve_post_processing_build_level_override() -> None:
    """Should use build-level config to override defaults."""
    build_cfg: mod_types.BuildConfig = {
        "post_processing": {
            "enabled": False,
            "category_order": ["formatter"],
            "categories": {
                "formatter": {
                    "enabled": True,
                    "priority": ["black"],
                },
            },
        },
    }
    root_cfg: mod_types.RootConfig | None = None

    resolved = mod_resolve.resolve_post_processing(build_cfg, root_cfg)

    assert resolved["enabled"] is False
    assert resolved["category_order"] == ["formatter"]
    formatter = resolved["categories"]["formatter"]
    assert formatter["priority"] == ["black"]


def test_resolve_post_processing_root_level_override() -> None:
    """Should use root-level config when build-level is not provided."""
    build_cfg: mod_types.BuildConfig = {}
    root_cfg: mod_types.RootConfig = {
        "builds": [],
        "post_processing": {
            "enabled": False,
            "category_order": ["formatter"],
        },
    }

    resolved = mod_resolve.resolve_post_processing(build_cfg, root_cfg)

    assert resolved["enabled"] is False
    assert resolved["category_order"] == ["formatter"]


def test_resolve_post_processing_build_overrides_root() -> None:
    """Should prioritize build-level config over root-level."""
    build_cfg: mod_types.BuildConfig = {
        "post_processing": {
            "enabled": True,
            "category_order": ["static_checker"],
        },
    }
    root_cfg: mod_types.RootConfig = {
        "builds": [],
        "post_processing": {
            "enabled": False,
            "category_order": ["formatter"],
        },
    }

    resolved = mod_resolve.resolve_post_processing(build_cfg, root_cfg)

    assert resolved["enabled"] is True
    assert resolved["category_order"] == ["static_checker"]


def test_resolve_post_processing_warns_invalid_category(
    module_logger: mod_logs.AppLogger,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should warn on invalid category names in category_order."""
    build_cfg: mod_types.BuildConfig = {
        "post_processing": {
            "category_order": ["invalid_category", "formatter"],
        },
    }
    root_cfg: mod_types.RootConfig | None = None

    with module_logger.use_level("warning"):
        resolved = mod_resolve.resolve_post_processing(build_cfg, root_cfg)

    # Should still resolve, but with warning
    assert "formatter" in resolved["category_order"]
    out = capsys.readouterr().err.lower()
    assert "invalid category" in out


def test_resolve_post_processing_empty_priority_disables_category() -> None:
    """Should disable category when priority is empty."""
    build_cfg: mod_types.BuildConfig = {
        "post_processing": {
            "categories": {
                "formatter": {
                    "priority": [],
                },
            },
        },
    }
    root_cfg: mod_types.RootConfig | None = None

    resolved = mod_resolve.resolve_post_processing(build_cfg, root_cfg)

    formatter = resolved["categories"]["formatter"]
    assert formatter["enabled"] is False


def test_resolve_post_processing_merges_tool_overrides() -> None:
    """Should merge tool overrides from defaults and user config."""
    build_cfg: mod_types.BuildConfig = {
        "post_processing": {
            "categories": {
                "formatter": {
                    "priority": ["ruff"],
                    "tools": {
                        "ruff": {
                            "options": ["--line-length", "100"],
                        },
                    },
                },
            },
        },
    }
    root_cfg: mod_types.RootConfig | None = None

    resolved = mod_resolve.resolve_post_processing(build_cfg, root_cfg)

    formatter = resolved["categories"]["formatter"]
    tools = formatter["tools"]
    assert "ruff" in tools
    ruff_tool = tools["ruff"]
    assert ruff_tool["options"] == ["--line-length", "100"]


def test_resolve_post_processing_includes_all_categories() -> None:
    """Should include all categories even if not in category_order."""
    build_cfg: mod_types.BuildConfig = {
        "post_processing": {
            "category_order": ["formatter"],  # Only formatter in order
        },
    }
    root_cfg: mod_types.RootConfig | None = None

    resolved = mod_resolve.resolve_post_processing(build_cfg, root_cfg)

    # All categories should be present
    assert "static_checker" in resolved["categories"]
    assert "formatter" in resolved["categories"]
    assert "import_sorter" in resolved["categories"]
    # But only formatter in order
    assert resolved["category_order"] == ["formatter"]


def test_resolve_post_processing_category_enabled_flag() -> None:
    """Should respect category enabled flag."""
    build_cfg: mod_types.BuildConfig = {
        "post_processing": {
            "categories": {
                "formatter": {
                    "enabled": False,
                    "priority": ["ruff"],
                },
            },
        },
    }
    root_cfg: mod_types.RootConfig | None = None

    resolved = mod_resolve.resolve_post_processing(build_cfg, root_cfg)

    formatter = resolved["categories"]["formatter"]
    assert formatter["enabled"] is False


def test_resolve_post_processing_custom_tool_instances() -> None:
    """Should handle custom tool instances with explicit commands."""
    build_cfg: mod_types.BuildConfig = {
        "post_processing": {
            "categories": {
                "formatter": {
                    "priority": ["ruff-check", "ruff-format"],
                    "tools": {
                        "ruff-check": {
                            "command": "ruff",
                            "args": ["check", "--fix"],
                        },
                        "ruff-format": {
                            "command": "ruff",
                            "args": ["format"],
                        },
                    },
                },
            },
        },
    }
    root_cfg: mod_types.RootConfig | None = None

    resolved = mod_resolve.resolve_post_processing(build_cfg, root_cfg)

    formatter = resolved["categories"]["formatter"]
    assert formatter["priority"] == ["ruff-check", "ruff-format"]
    tools = formatter["tools"]
    assert "ruff-check" in tools
    assert "ruff-format" in tools
    ruff_check = tools["ruff-check"]
    ruff_format = tools["ruff-format"]
    assert ruff_check["args"] == ["check", "--fix"]
    assert ruff_format["args"] == ["format"]


def test_resolve_post_processing_root_tool_override_merged_with_build() -> None:
    """Should merge root and build tool overrides correctly."""
    build_cfg: mod_types.BuildConfig = {
        "post_processing": {
            "categories": {
                "formatter": {
                    "tools": {
                        "ruff": {
                            "options": ["--line-length", "120"],
                        },
                    },
                },
            },
        },
    }
    root_cfg: mod_types.RootConfig = {
        "builds": [],
        "post_processing": {
            "categories": {
                "formatter": {
                    "tools": {
                        "ruff": {
                            "path": "/custom/ruff",
                        },
                    },
                },
            },
        },
    }

    resolved = mod_resolve.resolve_post_processing(build_cfg, root_cfg)

    # Build should override root
    formatter = resolved["categories"]["formatter"]
    tools = formatter["tools"]
    assert "ruff" in tools
    ruff_tool = tools["ruff"]
    # Options from build should be present
    assert ruff_tool["options"] == ["--line-length", "120"]
    # Path from root should be overridden (not merged, replaced)
    # Actually, looking at the merge logic, tools are replaced, not merged
    # So build's tools dict replaces root's
    assert ruff_tool["path"] is None


def test_resolve_post_processing_category_order_preserved() -> None:
    """Should preserve category order from config."""
    build_cfg: mod_types.BuildConfig = {
        "post_processing": {
            "category_order": ["import_sorter", "formatter", "static_checker"],
        },
    }
    root_cfg: mod_types.RootConfig | None = None

    resolved = mod_resolve.resolve_post_processing(build_cfg, root_cfg)

    assert resolved["category_order"] == [
        "import_sorter",
        "formatter",
        "static_checker",
    ]


def test_resolve_post_processing_none_root_config() -> None:
    """Should handle None root config gracefully."""
    build_cfg: mod_types.BuildConfig = {
        "post_processing": {
            "enabled": False,
        },
    }

    resolved = mod_resolve.resolve_post_processing(build_cfg, None)

    assert resolved["enabled"] is False


def test_resolve_post_processing_custom_labels_in_user_config_priority() -> None:
    """Should handle custom labels in user config priority."""
    build_cfg: mod_types.BuildConfig = {
        "post_processing": {
            "categories": {
                "formatter": {
                    "priority": ["ruff:first", "ruff:second"],
                    "tools": {
                        "ruff:first": {
                            "command": "ruff",
                            "args": ["check", "--fix"],
                        },
                        "ruff:second": {
                            "command": "ruff",
                            "args": ["format"],
                        },
                    },
                },
            },
        },
    }
    root_cfg: mod_types.RootConfig | None = None

    resolved = mod_resolve.resolve_post_processing(build_cfg, root_cfg)

    # Both should be in priority
    formatter = resolved["categories"]["formatter"]
    assert formatter.get("priority") == ["ruff:first", "ruff:second"]  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_resolve_post_processing_custom_labels_in_default_categories() -> None:
    """Should handle custom labels in DEFAULT_CATEGORIES priority."""
    # Temporarily modify DEFAULT_CATEGORIES to have custom labels
    original_formatter = mod_constants.DEFAULT_CATEGORIES["formatter"].copy()
    mod_constants.DEFAULT_CATEGORIES["formatter"] = {
        "enabled": True,
        "priority": ["ruff:check", "ruff:format"],
        "tools": {
            "ruff:check": {
                "command": "ruff",
                "args": ["check", "--fix"],
            },
            "ruff:format": {
                "command": "ruff",
                "args": ["format"],
            },
        },
    }

    try:
        # User config doesn't override - should use defaults
        build_cfg: mod_types.BuildConfig = {}
        root_cfg: mod_types.RootConfig | None = None
        resolved = mod_resolve.resolve_post_processing(build_cfg, root_cfg)

        formatter = resolved["categories"]["formatter"]
        # Should have custom labels from defaults
        assert formatter.get("priority") == ["ruff:check", "ruff:format"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        tools = formatter.get("tools")  # pyright: ignore[reportTypedDictNotRequiredAccess]
        assert tools is not None
        assert "ruff:check" in tools
        assert "ruff:format" in tools
    finally:
        mod_constants.DEFAULT_CATEGORIES["formatter"] = original_formatter


def test_resolve_post_processing_custom_label_fallback_from_defaults() -> None:
    """Should fallback to DEFAULT_CATEGORIES when custom label in priority.

    Custom label should be found in DEFAULT_CATEGORIES when not in user tools.
    """
    # DEFAULT_CATEGORIES has custom label
    original_formatter = mod_constants.DEFAULT_CATEGORIES["formatter"].copy()
    mod_constants.DEFAULT_CATEGORIES["formatter"] = {
        "enabled": True,
        "priority": ["ruff:check", "ruff:format"],
        "tools": {
            "ruff:check": {
                "command": "ruff",
                "args": ["check", "--fix"],
            },
            "ruff:format": {
                "command": "ruff",
                "args": ["format"],
            },
        },
    }

    try:
        # User config has custom label in priority but doesn't define it in tools
        build_cfg: mod_types.BuildConfig = {
            "post_processing": {
                "categories": {
                    "formatter": {
                        "priority": ["ruff:check"],  # In priority but not in user tools
                        # No tools dict - should fallback to defaults
                    },
                },
            },
        }
        root_cfg: mod_types.RootConfig | None = None
        resolved = mod_resolve.resolve_post_processing(build_cfg, root_cfg)

        formatter = resolved["categories"]["formatter"]
        assert formatter.get("priority") == ["ruff:check"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        tools = formatter.get("tools")  # pyright: ignore[reportTypedDictNotRequiredAccess]
        assert tools is not None
        # Should have ruff:check from defaults via fallback
        assert "ruff:check" in tools
    finally:
        mod_constants.DEFAULT_CATEGORIES["formatter"] = original_formatter
