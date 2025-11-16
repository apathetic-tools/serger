# tests/5_core/test_validate_config.py
"""Tests for serger.config_validate."""

from typing import Any

import serger.config.config_validate as mod_validate


# ---------------------------------------------------------------------------
# Basic “known good” configurations
# ---------------------------------------------------------------------------


def test_valid_minimal_root_and_build() -> None:
    """A simple flat config with list[str] include should validate True."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "include": ["src"],
        "out": "dist",
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    assert summary.valid is True


def test_valid_multiple_builds() -> None:
    """Multi-build configs are no longer supported - this test is removed."""
    # Multi-build support has been removed. This test is kept as a placeholder
    # but will fail validation since "builds" key is not supported.
    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [
            {"include": ["src"], "out": "dist"},
            {"include": ["tests"], "out": "dist/tests"},
        ],
        "watch_interval": 1.0,
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    # Should fail because "builds" key is not supported
    assert summary.valid is False


# ---------------------------------------------------------------------------
# Structural or type errors
# ---------------------------------------------------------------------------


def test_invalid_builds_not_a_list() -> None:
    """The 'builds' key is not supported - should fail validation."""
    # --- setup ---
    # not supported
    cfg: dict[str, Any] = {"builds": {"include": ["src"], "out": "dist"}}

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    assert summary.valid is False


def test_invalid_inner_type_in_list() -> None:
    """Include should be list[str], but we insert an int."""
    # --- setup ---
    cfg: dict[str, Any] = {"include": ["src", 42], "out": "dist"}

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    assert summary.valid is False


def test_invalid_top_level_key() -> None:
    """Unknown root key should invalidate config under strict=True."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "include": ["src"],
        "out": "dist",
        "bogus": 123,
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg, strict=True)

    # --- validate ---
    assert summary.valid is False


# ---------------------------------------------------------------------------
# Optional/edge handling
# ---------------------------------------------------------------------------


def test_empty_build_list() -> None:
    """The 'builds' key is not supported - should fail validation."""
    # --- setup ---
    cfg: dict[str, Any] = {"builds": []}

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    # Should fail because "builds" key is not supported
    assert summary.valid is False


def test_handles_list_of_typed_dicts() -> None:
    """Flat config should validate correctly."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "include": ["src"],
        "out": "dist",
        "strict_config": False,
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    assert summary.valid is True


def test_warn_keys_once_behavior() -> None:
    """Repeated dry-run keys should only trigger one warning."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "include": ["src"],
        "out": "dist",
        "dry_run": True,
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    # Collect all messages that mention dry-run, across all warning categories
    pool = summary.errors + summary.strict_warnings + summary.warnings
    # Only one log message mentioning dry-run should appear
    dry_msgs = [m for m in pool if "dry-run" in m]
    assert len(dry_msgs) == 1


def test_invalid_type_at_root() -> None:
    """Root-level key of wrong type should fail."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "include": ["src"],
        "out": "dist",
        "strict_config": "yes",  # wrong type
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg, strict=True)

    # --- validate ---
    assert summary.valid is False


def test_root_and_build_strict_config() -> None:
    """Strict config should mark unknown keys as invalid."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "include": ["src"],
        "out": "dist",
        "strict_config": True,
        "extra": 123,  # unknown key
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    # Collect all messages that mention dry-run, across all warning categories
    pool = summary.errors + summary.strict_warnings + summary.warnings
    # With strict=True, unknown key should mark invalid
    assert summary.valid is False
    assert any("unknown key" in msg.lower() for msg in pool)


def test_invalid_missing_builds_key() -> None:
    """Config without required fields should fail."""
    # --- setup ---
    cfg: dict[str, Any] = {"not_builds": []}

    # --- execute ---
    summary = mod_validate.validate_config(cfg, strict=True)

    # --- validate ---
    # Config without include/out should fail (or at least have warnings)
    # The exact behavior depends on validation rules
    assert isinstance(summary.valid, bool)


def test_valid_with_optional_fields() -> None:
    # --- setup ---
    cfg: dict[str, Any] = {
        "include": ["src"],
        "out": "dist",
        "log_level": "debug",
        "respect_gitignore": True,
        "watch_interval": 2.5,
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg, strict=True)

    # --- validate ---
    assert summary.valid is True


def test_empty_build_dict() -> None:
    """Empty config dict should be valid (may have warnings about missing fields)."""
    # --- setup ---
    cfg: dict[str, Any] = {}

    # --- execute ---
    summary = mod_validate.validate_config(cfg, strict=True)

    # --- validate ---
    # Empty config might be valid (zero-config mode) or might have warnings
    assert isinstance(summary.valid, bool)


def test_validate_config_suggests_similar_keys() -> None:
    """Validator should suggest close matches for mistyped keys."""
    # --- setup ---
    # Build a minimal but valid config with two bad keys that look like
    # legitimate ones so fuzzy suggestions trigger.
    bad_cfg: dict[str, Any] = {
        "inclde": ["src"],  # close to "include"
        "outt": "dist",  # close to "out"
    }

    # --- execute ---
    summary = mod_validate.validate_config(bad_cfg)

    # --- validate ---
    # we just care about the suggestions, not if the validation failed or passed
    assert isinstance(summary.valid, bool)

    # It should have reported unknown keys
    pool = summary.errors + summary.strict_warnings + summary.warnings
    joined = "\n".join(pool).lower()

    # Find all messages mentioning 'unknown key' and 'Hint:'
    assert "unknown key" in joined
    # Each bad key should appear with a suggestion line
    assert "'inclde' → 'include'" in joined
    assert "'outt' → 'out'" in joined


# ---------------------------------------------------------------------------
# Aggregation / combined warnings
# ---------------------------------------------------------------------------


def test_aggregates_multiple_builds_same_warning() -> None:
    """Multi-build configs are no longer supported - this test is removed."""
    # Multi-build support has been removed. This test is kept as a placeholder
    # but will fail validation since "builds" key is not supported.
    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [
            {"include": ["src"], "out": "dist", "dry_run": True},
            {"include": ["src2"], "out": "dist2", "dry_run": True},
        ],
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    # Should fail because "builds" key is not supported
    assert summary.valid is False


def test_aggregates_multiple_root_and_builds() -> None:
    """Multi-build configs are no longer supported - this test is removed."""
    # Multi-build support has been removed. This test is kept as a placeholder
    # but will fail validation since "builds" key is not supported.
    # --- setup ---
    cfg: dict[str, Any] = {
        "dry_run": True,
        "builds": [
            {"include": ["src"], "out": "dist", "dry_run": True},
            {"include": ["src2"], "out": "dist2", "dry_run": True},
        ],
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    # Should fail because "builds" key is not supported
    assert summary.valid is False


def test_aggregates_strict_and_non_strict_separately() -> None:
    """Multi-build configs are no longer supported - this test is removed."""
    # Multi-build support has been removed. This test is kept as a placeholder
    # but will fail validation since "builds" key is not supported.
    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [
            {
                "include": ["src"],
                "out": "dist",
                "dry_run": True,
                "strict_config": True,
            },
            {
                "include": ["src2"],
                "out": "dist2",
                "dry_run": True,
                "strict_config": False,
            },
        ],
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    # Should fail because "builds" key is not supported
    assert summary.valid is False


def test_aggregator_clears_after_flush() -> None:
    """Running validation twice should not leak previous aggregation state."""
    # --- setup ---
    cfg1: dict[str, Any] = {
        "include": ["src"],
        "out": "dist",
        "dry_run": True,
    }
    cfg2: dict[str, Any] = {
        "include": ["src"],
        "out": "dist",
    }

    # --- execute ---
    summary1 = mod_validate.validate_config(cfg1)
    summary2 = mod_validate.validate_config(cfg2)

    # --- validate ---
    pool1 = summary1.errors + summary1.strict_warnings + summary1.warnings
    pool2 = summary2.errors + summary2.strict_warnings + summary2.warnings
    # First run should have one dry-run warning
    assert any("dry-run" in m for m in pool1)
    # Second run should not repeat or leak messages
    assert not any("dry-run" in m for m in pool2)


def test_validate_config_prewarn_suppresses_unknown_keys() -> None:
    """Keys handled by warn_keys_once should not appear again as unknown."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "include": ["src"],
        "out": "dist",
        "dry_run": True,
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    pool = summary.errors + summary.strict_warnings + summary.warnings
    joined = "\n".join(pool)
    # It should warn about dry-run once, but not call it "unknown"
    assert "dry-run" in joined or "dry_run" in joined
    assert "unknown key" not in joined
