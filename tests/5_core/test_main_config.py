# tests/5_core/test_main_config.py
"""Tests for main configuration parsing and logic."""

import serger.main_config as mod_main_config


def test_parse_main_name_none() -> None:
    """Test parsing None main_name."""
    # --- execute ---
    module_path, function_name = mod_main_config.parse_main_name(None)

    # --- verify ---
    assert module_path is None
    assert function_name == "main"


def test_parse_main_name_with_dots_no_separator() -> None:
    """Test parsing main_name with dots but no :: separator."""
    # --- execute ---
    module_path, function_name = mod_main_config.parse_main_name("mypkg.subpkg")

    # --- verify ---
    assert module_path == "mypkg.subpkg"
    assert function_name == "main"


def test_parse_main_name_with_dots_explicit_separator_empty_function() -> None:
    """Test parsing main_name with dots and :: separator, empty function."""
    # --- execute ---
    module_path, function_name = mod_main_config.parse_main_name("mypkg.subpkg::")

    # --- verify ---
    assert module_path == "mypkg.subpkg"
    assert function_name == "main"


def test_parse_main_name_with_dots_explicit_separator_with_function() -> None:
    """Test parsing main_name with dots and :: separator, with function."""
    # --- execute ---
    module_path, function_name = mod_main_config.parse_main_name("mypkg.subpkg::entry")

    # --- verify ---
    assert module_path == "mypkg.subpkg"
    assert function_name == "entry"


def test_parse_main_name_single_name_with_separator_empty_function() -> None:
    """Test parsing single name with :: separator, empty function."""
    # --- execute ---
    module_path, function_name = mod_main_config.parse_main_name("mypkg::")

    # --- verify ---
    assert module_path == "mypkg"
    assert function_name == "main"


def test_parse_main_name_single_name_with_separator_with_function() -> None:
    """Test parsing single name with :: separator, with function."""
    # --- execute ---
    module_path, function_name = mod_main_config.parse_main_name("mypkg::entry")

    # --- verify ---
    assert module_path == "mypkg"
    assert function_name == "entry"


def test_parse_main_name_single_name_no_separator() -> None:
    """Test parsing single name without :: separator (function name only)."""
    # --- execute ---
    module_path, function_name = mod_main_config.parse_main_name("mypkg")

    # --- verify ---
    assert module_path is None
    assert function_name == "mypkg"


def test_parse_main_name_function_name_main() -> None:
    """Test parsing function name 'main' without module path."""
    # --- execute ---
    module_path, function_name = mod_main_config.parse_main_name("main")

    # --- verify ---
    assert module_path is None
    assert function_name == "main"


def test_parse_main_name_empty_string() -> None:
    """Test parsing empty string (edge case)."""
    # --- execute ---
    module_path, function_name = mod_main_config.parse_main_name("")

    # --- verify ---
    assert module_path is None
    assert function_name == ""


def test_parse_main_name_separator_only() -> None:
    """Test parsing :: separator only (edge case)."""
    # --- execute ---
    module_path, function_name = mod_main_config.parse_main_name("::")

    # --- verify ---
    assert module_path is None
    assert function_name == "main"


def test_parse_main_name_separator_with_function_only() -> None:
    """Test parsing :: with function name only (no module path)."""
    # --- execute ---
    module_path, function_name = mod_main_config.parse_main_name("::entry")

    # --- verify ---
    assert module_path is None
    assert function_name == "entry"


def test_parse_main_name_complex_module_path() -> None:
    """Test parsing complex multi-level module path."""
    # --- execute ---
    module_path, function_name = mod_main_config.parse_main_name("a.b.c.d.e")

    # --- verify ---
    assert module_path == "a.b.c.d.e"
    assert function_name == "main"


def test_parse_main_name_complex_module_path_with_function() -> None:
    """Test parsing complex multi-level module path with function."""
    # --- execute ---
    module_path, function_name = mod_main_config.parse_main_name("a.b.c.d.e::cli")

    # --- verify ---
    assert module_path == "a.b.c.d.e"
    assert function_name == "cli"
