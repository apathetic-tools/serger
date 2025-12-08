# tests/0_independant/test_can_run_configless.py

from argparse import Namespace

import serger.config.config_loader as mod_config_loader


def test_can_run_configless_with_include() -> None:
    """Should return True when --include is present."""
    args = Namespace(
        include=["src/**/*.py"],
        add_include=None,
    )
    assert mod_config_loader.can_run_configless(args) is True


def test_can_run_configless_with_add_include() -> None:
    """Should return True when --add-include is present."""
    args = Namespace(
        include=None,
        add_include=["tests/**/*.py"],
    )
    assert mod_config_loader.can_run_configless(args) is True


def test_can_run_configless_with_positional_include() -> None:
    """Should return True when positional include is present (merged into include)."""
    args = Namespace(
        include=["docs/**"],  # Positional includes are merged into include
        add_include=None,
    )
    assert mod_config_loader.can_run_configless(args) is True


def test_can_run_configless_with_multiple_options() -> None:
    """Should return True when multiple options are present."""
    args = Namespace(
        include=["src/**"],
        add_include=["tests/**"],
    )
    assert mod_config_loader.can_run_configless(args) is True


def test_can_run_configless_with_all_options() -> None:
    """Should return True when all options are present."""
    args = Namespace(
        include=["src/**", "docs/**"],  # Positional includes merged into include
        add_include=["tests/**"],
    )
    assert mod_config_loader.can_run_configless(args) is True


def test_can_run_configless_with_no_options() -> None:
    """Should return False when no options are present."""
    args = Namespace(
        include=None,
        add_include=None,
    )
    assert mod_config_loader.can_run_configless(args) is False


def test_can_run_configless_with_empty_include() -> None:
    """Should return False when include is an empty list."""
    args = Namespace(
        include=[],
        add_include=None,
    )
    assert mod_config_loader.can_run_configless(args) is False


def test_can_run_configless_with_empty_add_include() -> None:
    """Should return False when add_include is an empty list."""
    args = Namespace(
        include=None,
        add_include=[],
    )
    assert mod_config_loader.can_run_configless(args) is False


def test_can_run_configless_missing_attributes() -> None:
    """Should return False when some attributes are missing from Namespace."""
    args = Namespace()
    assert mod_config_loader.can_run_configless(args) is False


def test_can_run_configless_partial_missing_attributes() -> None:
    """Should return True when only some required attributes are missing but
    one present attribute has a truthy value."""
    args = Namespace(include=["src/**"])
    # Only 'include' is set, others don't exist
    assert mod_config_loader.can_run_configless(args) is True
