# tests/5_core/test_parse_config.py
"""Tests for config_loader (package and standalone versions)."""

from typing import Any

import pytest

import serger.config.config_loader as mod_config_loader


def test_parse_config_returns_none_for_empty_values() -> None:
    # --- execute and verify ---
    assert mod_config_loader.parse_config(None) is None
    assert mod_config_loader.parse_config({}) is None
    assert mod_config_loader.parse_config([]) is None


def test_parse_config_list_of_strings_single_build() -> None:
    """List of strings should normalize into flat config with include list."""
    # --- execute ---
    result = mod_config_loader.parse_config(["src/**", "lib/**"])

    # --- verify ---
    assert result == {"include": ["src/**", "lib/**"]}


def test_parse_config_flat_config() -> None:
    """Flat config should be returned as-is with all fields at root level."""
    # --- setup ---
    data: dict[str, Any] = {
        "include": ["src"],
        "out": "dist",
        "watch_interval": 3.5,
        "package": "mypkg",
    }

    # --- execute ---
    result = mod_config_loader.parse_config(data)

    # --- verify ---
    assert result == data
    assert result is not None
    assert "builds" not in result
    assert "build" not in result


def test_parse_config_flat_config_with_unknown_fields() -> None:
    """Flat config should preserve unknown fields for later validation."""
    # --- setup ---
    data: dict[str, Any] = {
        "include": ["src"],
        "out": "dist",
        "mystery": True,  # unknown field, should be preserved
    }

    # --- execute ---
    result = mod_config_loader.parse_config(data)

    # --- verify ---
    assert result == data
    assert result is not None
    assert "mystery" in result
    assert result["mystery"] is True


def test_parse_config_rejects_list_of_dicts() -> None:
    """List of dicts (multi-build) should raise TypeError."""
    # --- setup ---
    data: list[dict[str, Any]] = [
        {"include": ["src"]},
        {"include": ["lib"]},
    ]

    # --- execute & verify ---
    with pytest.raises(TypeError, match="Multi-build configuration is not supported"):
        mod_config_loader.parse_config(data)


def test_parse_config_rejects_mixed_type_list() -> None:
    """Mixed-type list should raise TypeError (must be all strings)."""
    # --- setup ---
    # This list contains both a string and a dict — invalid mix.
    bad_config: list[object] = ["src/**", {"out": "dist"}]

    # --- execute & verify ---
    with pytest.raises(TypeError, match="Invalid mixed-type list"):
        mod_config_loader.parse_config(bad_config)


def test_parse_config_rejects_invalid_root_type() -> None:
    """Non-dict or non-list root should raise a TypeError."""
    # --- execute and verify ---
    with pytest.raises(TypeError) as excinfo:
        mod_config_loader.parse_config("not_a_dict_or_list")  # type: ignore[arg-type]

    msg = str(excinfo.value)
    assert "Invalid top-level value" in msg
    assert "expected object" in msg


def test_parse_config_preserves_main_mode() -> None:
    """main_mode should be preserved in parsed config."""
    # --- setup ---
    data: dict[str, Any] = {
        "include": ["src"],
        "main_mode": "none",
    }

    # --- execute ---
    result = mod_config_loader.parse_config(data)

    # --- verify ---
    assert result is not None
    assert result["main_mode"] == "none"


def test_parse_config_preserves_main_name() -> None:
    """main_name should be preserved in parsed config."""
    # --- setup ---
    data: dict[str, Any] = {
        "include": ["src"],
        "main_name": "mypkg.main",
    }

    # --- execute ---
    result = mod_config_loader.parse_config(data)

    # --- verify ---
    assert result is not None
    assert result["main_name"] == "mypkg.main"


def test_parse_config_preserves_main_name_none() -> None:
    """main_name=None should be preserved in parsed config."""
    # --- setup ---
    data: dict[str, Any] = {
        "include": ["src"],
        "main_name": None,
    }

    # --- execute ---
    result = mod_config_loader.parse_config(data)

    # --- verify ---
    assert result is not None
    assert result["main_name"] is None
