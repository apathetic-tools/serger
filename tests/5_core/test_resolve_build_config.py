# tests/5_core/test_resolve_build_config.py

"""Tests for serger.config_resolve."""

import argparse
from argparse import Namespace
from pathlib import Path
from typing import cast

import pytest

import apathetic_utils as mod_apathetic_utils
import serger.config.config_resolve as mod_resolve
import serger.config.config_types as mod_types
import serger.logs as mod_logs
from tests.utils import make_build_input, make_test_package


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _args(**kwargs: object) -> argparse.Namespace:
    """Build a fake argparse.Namespace with common CLI defaults."""
    arg_namespace = argparse.Namespace()
    # default fields expected by resolver
    arg_namespace.include = None
    arg_namespace.exclude = None
    arg_namespace.add_include = None
    arg_namespace.add_exclude = None
    arg_namespace.out = None
    arg_namespace.watch = None
    arg_namespace.log_level = None
    arg_namespace.respect_gitignore = None
    arg_namespace.use_color = None
    arg_namespace.config = None
    arg_namespace.dry_run = False
    for k, v in kwargs.items():
        setattr(arg_namespace, k, v)
    return arg_namespace


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_resolve_build_config_from_config_paths(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Ensure config-based include/out/exclude resolve relative to config_dir."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], exclude=["*.tmp"], out="dist")
    args = _args()

    # --- patch and execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    inc = resolved["include"][0]
    exc = resolved["exclude"][0]
    out = resolved["out"]

    assert inc["root"] == tmp_path
    assert exc["root"] == tmp_path
    assert out["root"] == tmp_path
    assert resolved["log_level"].lower() == "info"
    assert resolved["respect_gitignore"] is True
    assert resolved["__meta__"]["config_root"] == tmp_path
    assert resolved["__meta__"]["cli_root"] == tmp_path


def test_resolve_build_config_cli_overrides_include_and_out(
    tmp_path: Path,
) -> None:
    """CLI --include and --out should override config include/out."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], out="dist")
    args = _args(include=["cli_src/**"], out="cli_dist")

    # --- patch and execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    inc = resolved["include"][0]
    out = resolved["out"]

    assert inc["path"] == "cli_src/**"
    assert inc["origin"] == "cli"
    assert out["path"] == "cli_dist"
    assert out["origin"] == "cli"


def test_resolve_build_config_add_include_extends(
    tmp_path: Path,
) -> None:
    """--add-include should append to config includes, not override."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    args = _args(add_include=["extra/**"])

    # --- patch and execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    paths = [i["path"] for i in resolved["include"]]
    assert "src/**" in paths
    assert "extra/**" in paths
    origins = {i["origin"] for i in resolved["include"]}
    assert "config" in origins
    assert "cli" in origins


def test_resolve_build_config_gitignore_patterns_added(
    tmp_path: Path,
) -> None:
    """When .gitignore exists, its patterns should be appended as gitignore excludes."""
    # --- setup ---
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.log\n# comment\ncache/\n")
    raw = make_build_input(include=["src/**"])
    args = _args()

    # --- patch and execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    git_excludes = [e for e in resolved["exclude"] if e["origin"] == "gitignore"]
    patterns = [str(e["path"]) for e in git_excludes]
    assert "*.log" in patterns
    assert "cache/" in patterns


def test_resolve_build_config_respects_cli_exclude_override(
    tmp_path: Path,
) -> None:
    """CLI --exclude should override config excludes."""
    # --- setup ---
    raw = make_build_input(exclude=["*.tmp"], include=["src/**"])
    args = _args(exclude=["*.bak"])

    # --- patch and execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    excl = [str(e["path"]) for e in resolved["exclude"]]
    assert "*.bak" in excl
    assert "*.tmp" not in excl


def test_resolve_build_config_respects_dest_override(
    tmp_path: Path,
) -> None:
    """IncludeResolved with explicit dest should survive resolution unchanged."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], out="dist")
    args = _args()

    # --- patch and execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    out = resolved["out"]
    assert out["origin"] == "config"
    assert out["root"] == tmp_path
    assert out["path"] == "dist"


def test_resolve_build_config_respect_gitignore_false(
    tmp_path: Path,
) -> None:
    """If --no-gitignore is passed, .gitignore patterns are not loaded."""
    # --- setup ---
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.log\n")
    raw = make_build_input(include=["src/**"], respect_gitignore=False)
    args = _args(respect_gitignore=False)

    # --- patch and execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert all(e["origin"] != "gitignore" for e in resolved["exclude"])
    assert resolved["respect_gitignore"] is False


def test_resolve_build_config_add_exclude_extends(
    tmp_path: Path,
) -> None:
    # --- setup ---
    raw = make_build_input(exclude=["*.tmp"], include=["src/**"])
    args = _args(add_exclude=["*.log"])

    # --- patch and execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    patterns = [str(e["path"]) for e in resolved["exclude"]]
    assert "*.tmp" in patterns
    assert "*.log" in patterns
    origins = {e["origin"] for e in resolved["exclude"]}
    assert "config" in origins
    assert "cli" in origins


def test_resolve_build_config_handles_empty_include(tmp_path: Path) -> None:
    # --- setup ---
    args = _args()
    raw = make_build_input(include=[])

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["include"] == []


def test_resolve_build_config_with_absolute_include(tmp_path: Path) -> None:
    # --- setup ---
    abs_src = tmp_path / "src"
    abs_src.mkdir()
    args = _args()
    raw = make_build_input(include=[str(abs_src)])

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    inc = resolved["include"][0]
    assert inc["root"] == abs_src.resolve()
    assert inc["path"] == "."


def test_resolve_build_config_inherits_root_gitignore_setting(tmp_path: Path) -> None:
    # --- setup ---
    raw = make_build_input(include=["src/**"], respect_gitignore=False)
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["respect_gitignore"] is False


def test_resolve_build_config_preserves_trailing_slash(tmp_path: Path) -> None:
    # --- setup ---
    raw: mod_types.RootConfig = {"include": ["src/"], "out": "dist"}
    args = Namespace()  # empty placeholder

    # --- execute ---
    result = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)
    inc_path = result["include"][0]["path"]

    # --- validate ---
    assert isinstance(inc_path, str)
    assert inc_path.endswith("/"), f"trailing slash lost: {inc_path!r}"


def test_resolve_build_config_warns_for_missing_include_root(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Warn if include root directory does not exist and pattern is not a glob."""
    # --- setup ---
    missing_root = tmp_path / "nonexistent_root"
    raw = make_build_input(include=[f"{missing_root}/src"])
    args = _args()

    # --- patch and execute ---
    mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    out = capsys.readouterr().err.lower()
    assert "Include root does not exist".lower() in out


def test_resolve_build_config_warns_for_missing_absolute_include(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Warn if absolute include path does not exist and pattern is not a glob."""
    # --- setup ---
    abs_missing = tmp_path / "abs_missing_dir"
    raw = make_build_input(include=[str(abs_missing)])
    args = _args()

    # --- patch and execute ---
    mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    out = capsys.readouterr().err.lower()
    assert "Include path does not exist".lower() in out


def test_resolve_build_config_warns_for_missing_relative_include(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Warn if relative include path does not exist under an existing root."""
    # --- setup ---
    existing_root = tmp_path
    raw = make_build_input(include=["missing_rel_dir"])
    args = _args()

    # --- patch and execute ---
    mod_resolve.resolve_build_config(raw, args, existing_root, tmp_path)

    # --- validate ---
    out = capsys.readouterr().err.lower()
    assert "Include path does not exist".lower() in out


def test_resolve_build_config_include_with_dest_from_config(
    tmp_path: Path,
) -> None:
    """Config includes with dest should propagate to resolved config."""
    # --- setup ---
    raw = make_build_input(
        include=[
            "src/**",
            {"path": "assets/", "dest": "static"},
            {"path": "docs/", "dest": "help"},
        ],
    )
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    inc_list = resolved["include"]
    expected_count = 3
    assert len(inc_list) == expected_count

    # First include: no dest
    assert inc_list[0]["path"] == "src/**"
    assert inc_list[0]["origin"] == "config"
    assert "dest" not in inc_list[0]

    # Second include: with dest
    assert inc_list[1]["path"] == "assets/"
    assert inc_list[1]["origin"] == "config"
    assert inc_list[1].get("dest") == Path("static")

    # Third include: with dest
    assert inc_list[2]["path"] == "docs/"
    assert inc_list[2]["origin"] == "config"
    assert inc_list[2].get("dest") == Path("help")


def test_resolve_build_config_include_with_dest_from_cli(
    tmp_path: Path,
) -> None:
    """CLI includes with dest (path:dest format) should be parsed."""
    # --- setup ---
    raw = make_build_input(include=["config_src/**"])
    args = _args(include=["src/**", "assets/:static", "docs/:help"])

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    inc_list = resolved["include"]
    expected_count = 3
    assert len(inc_list) == expected_count

    # First include: no dest
    assert inc_list[0]["path"] == "src/**"
    assert inc_list[0]["origin"] == "cli"
    assert "dest" not in inc_list[0]

    # Second include: with dest
    assert inc_list[1]["path"] == "assets/"
    assert inc_list[1]["origin"] == "cli"
    assert inc_list[1].get("dest") == Path("static")

    # Third include: with dest
    assert inc_list[2]["path"] == "docs/"
    assert inc_list[2]["origin"] == "cli"
    assert inc_list[2].get("dest") == Path("help")


def test_resolve_build_config_add_include_with_dest(
    tmp_path: Path,
) -> None:
    """--add-include with dest should extend config includes."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    args = _args(add_include=["assets/:static", "docs/:help"])

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    inc_list = resolved["include"]
    expected_count = 3
    assert len(inc_list) == expected_count

    # Config include
    assert inc_list[0]["path"] == "src/**"
    assert inc_list[0]["origin"] == "config"
    assert "dest" not in inc_list[0]

    # Add-includes with dest
    assert inc_list[1]["path"] == "assets/"
    assert inc_list[1]["origin"] == "cli"
    assert inc_list[1].get("dest") == Path("static")

    assert inc_list[2]["path"] == "docs/"
    assert inc_list[2]["origin"] == "cli"
    assert inc_list[2].get("dest") == Path("help")


def test_resolve_build_config_include_windows_path_with_dest(
    tmp_path: Path,
) -> None:
    """Windows absolute paths with dest should be parsed correctly."""
    # --- setup ---
    raw = make_build_input(include=["config_src/**"])
    # Test various Windows path formats with dest
    args = _args(
        include=[
            r"C:\Users\test\src:renamed",
            "D:\\project\\assets\\:static",
            r"E:\docs:help",
        ]
    )

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    inc_list = resolved["include"]
    expected_count = 3
    assert len(inc_list) == expected_count

    # First: C: drive with nested path
    assert inc_list[0]["path"] == r"C:\Users\test\src"
    assert inc_list[0]["origin"] == "cli"
    assert inc_list[0].get("dest") == Path("renamed")

    # Second: D: drive with trailing backslash
    assert inc_list[1]["path"] == "D:\\project\\assets\\"
    assert inc_list[1]["origin"] == "cli"
    assert inc_list[1].get("dest") == Path("static")

    # Third: E: drive simple path
    assert inc_list[2]["path"] == r"E:\docs"
    assert inc_list[2]["origin"] == "cli"
    assert inc_list[2].get("dest") == Path("help")


def test_resolve_build_config_include_windows_drive_only(
    tmp_path: Path,
) -> None:
    """Windows drive letters without dest should not be parsed as dest."""
    # --- setup ---
    raw = make_build_input(include=["config_src/**"])
    # Test drive letters - these should NOT be split as path:dest
    args = _args(include=["C:", "D:\\"])

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    inc_list = resolved["include"]
    expected_count = 2
    assert len(inc_list) == expected_count

    # Drive letter only - not split
    assert inc_list[0]["path"] == "C:"
    assert inc_list[0]["origin"] == "cli"
    assert "dest" not in inc_list[0]

    # Drive with backslash - not split
    assert inc_list[1]["path"] == "D:\\"
    assert inc_list[1]["origin"] == "cli"
    assert "dest" not in inc_list[1]


# ---------------------------------------------------------------------------
# Pyproject.toml integration tests
# ---------------------------------------------------------------------------


def test_resolve_build_config_single_build_uses_pyproject_when_enabled(
    tmp_path: Path,
) -> None:
    """Single build should use pyproject.toml when explicitly enabled."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
version = "1.2.3"
description = "A test package"
license = "MIT"
authors = [
    {name = "Test Author", email = "test@example.com"}
]
"""
    )
    raw = make_build_input(include=["src/**"], use_pyproject_metadata=True)
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved.get("display_name") == "test-package"
    assert resolved.get("package") == "test-package"
    assert resolved.get("description") == "A test package"
    assert resolved.get("authors") == "Test Author <test@example.com>"
    assert resolved.get("license_header") == "MIT"
    assert resolved.get("_pyproject_version") == "1.2.3"


def test_resolve_build_config_single_build_respects_use_pyproject_metadata_false(
    tmp_path: Path,
) -> None:
    """Single build should respect explicit use_pyproject_metadata: false."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
version = "1.2.3"
description = "A test package"
authors = [
    {name = "Alice", email = "alice@example.com"}
]
"""
    )
    raw = make_build_input(include=["src/**"], use_pyproject_metadata=False)
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # No metadata should be extracted when use_pyproject_metadata is false
    assert (
        "display_name" not in resolved or resolved.get("display_name") != "test-package"
    )
    assert "_pyproject_version" not in resolved
    assert (
        "description" not in resolved or resolved.get("description") != "A test package"
    )
    assert (
        "authors" not in resolved
        or resolved.get("authors") != "Alice <alice@example.com>"
    )
    # Package IS always extracted from pyproject.toml for resolution purposes,
    # regardless of use_pyproject_metadata setting
    assert resolved.get("package") == "test-package"


def test_resolve_build_config_multi_build_requires_opt_in(
    tmp_path: Path,
) -> None:
    """Multi-build should not use pyproject.toml when explicitly disabled."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
version = "1.2.3"
"""
    )
    raw1 = make_build_input(include=["src1/**"], use_pyproject_metadata=False)
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw1, args, tmp_path, tmp_path)

    # --- validate ---
    # Should not use pyproject.toml metadata when explicitly disabled
    assert (
        "display_name" not in resolved or resolved.get("display_name") != "test-package"
    )
    assert "_pyproject_version" not in resolved
    # Package IS always extracted from pyproject.toml for resolution purposes,
    # regardless of use_pyproject_metadata setting
    assert resolved.get("package") == "test-package"


def test_resolve_build_config_multi_build_with_opt_in(
    tmp_path: Path,
) -> None:
    """Multi-build should use pyproject.toml when build explicitly opts in."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
version = "1.2.3"
description = "A test package"
"""
    )
    raw1 = make_build_input(include=["src1/**"], use_pyproject_metadata=True)
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw1, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved.get("display_name") == "test-package"
    assert resolved.get("description") == "A test package"
    assert resolved.get("_pyproject_version") == "1.2.3"


def test_resolve_build_config_path_resolution_build_level(
    tmp_path: Path,
) -> None:
    """Build-level pyproject_path should take precedence."""
    # --- setup ---
    custom_pyproject = tmp_path / "custom.toml"
    custom_pyproject.write_text(
        """[project]
name = "custom-package"
version = "2.0.0"
"""
    )
    default_pyproject = tmp_path / "pyproject.toml"
    default_pyproject.write_text(
        """[project]
name = "default-package"
version = "1.0.0"
"""
    )
    raw = make_build_input(
        include=["src/**"], pyproject_path="custom.toml", use_pyproject_metadata=True
    )
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved.get("display_name") == "custom-package"
    assert resolved.get("_pyproject_version") == "2.0.0"


def test_resolve_build_config_path_resolution_root_level(
    tmp_path: Path,
) -> None:
    """Root-level pyproject_path should enable pyproject for builds."""
    # --- setup ---
    root_pyproject = tmp_path / "root.toml"
    root_pyproject.write_text(
        """[project]
name = "root-package"
version = "3.0.0"
"""
    )
    raw = make_build_input(include=["src/**"], pyproject_path="root.toml")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved.get("display_name") == "root-package"
    assert resolved.get("_pyproject_version") == "3.0.0"


def test_resolve_build_config_root_use_pyproject_metadata_enables_for_all_builds(
    tmp_path: Path,
) -> None:
    """Root-level use_pyproject_metadata=True should enable pyproject for all builds."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
version = "1.2.3"
description = "A test package"
"""
    )
    raw1 = make_build_input(include=["src1/**"], use_pyproject_metadata=True)
    raw2 = make_build_input(include=["src2/**"], use_pyproject_metadata=True)
    args = _args()

    # --- execute ---
    resolved1 = mod_resolve.resolve_build_config(raw1, args, tmp_path, tmp_path)
    resolved2 = mod_resolve.resolve_build_config(raw2, args, tmp_path, tmp_path)

    # --- validate ---
    # Both builds should get pyproject metadata
    assert resolved1.get("display_name") == "test-package"
    assert resolved1.get("package") == "test-package"
    assert resolved1.get("_pyproject_version") == "1.2.3"
    assert resolved2.get("display_name") == "test-package"
    assert resolved2.get("package") == "test-package"
    assert resolved2.get("_pyproject_version") == "1.2.3"


def test_resolve_build_config_overrides_explicit_fields_when_pyproject_enabled(
    tmp_path: Path,
) -> None:
    """Should override explicitly set fields when pyproject is enabled."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "pyproject-name"
version = "1.0.0"
description = "pyproject description"
license = "MIT"
authors = [
    {name = "Pyproject Author", email = "pyproject@example.com"}
]
"""
    )
    raw = make_build_input(
        include=["src/**"],
        display_name="config-name",
        description="config description",
        authors="Config Author <config@example.com>",
        use_pyproject_metadata=True,
    )
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # When pyproject is enabled, all fields are overwritten
    assert resolved.get("display_name") == "pyproject-name"
    assert resolved.get("package") == "pyproject-name"
    assert resolved.get("description") == "pyproject description"
    assert resolved.get("authors") == "Pyproject Author <pyproject@example.com>"
    assert resolved.get("license_header") == "MIT"
    assert resolved.get("_pyproject_version") == "1.0.0"


def test_resolve_build_config_configless_uses_pyproject_by_default(
    tmp_path: Path,
) -> None:
    """Configless builds should use pyproject.toml by default."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
version = "1.2.3"
description = "A test package"
license = "MIT"
authors = [
    {name = "Test Author", email = "test@example.com"}
]
"""
    )
    raw = make_build_input(include=["src/**"])
    # Configless build: minimal root_cfg with only builds
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Configless builds should extract pyproject.toml metadata by default
    assert resolved.get("display_name") == "test-package"
    assert resolved.get("package") == "test-package"
    assert resolved.get("description") == "A test package"
    assert resolved.get("license_header") == "MIT"
    assert resolved.get("authors") == "Test Author <test@example.com>"
    assert resolved.get("_pyproject_version") == "1.2.3"


def test_resolve_build_config_configless_can_disable_pyproject(
    tmp_path: Path,
) -> None:
    """Configless builds can explicitly disable pyproject.toml."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
version = "1.2.3"
description = "A test package"
license = "MIT"
"""
    )
    raw = make_build_input(include=["src/**"], use_pyproject_metadata=False)
    # Configless build: minimal root_cfg with only builds
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Configless builds should not extract pyproject.toml metadata when disabled
    assert resolved.get("display_name") != "test-package"
    # Package IS always extracted from pyproject.toml for resolution purposes,
    # regardless of use_pyproject_metadata setting
    assert resolved.get("package") == "test-package"
    assert resolved.get("description") != "A test package"
    assert resolved.get("license_header") != "MIT"
    assert "_pyproject_version" not in resolved


def test_resolve_build_config_root_pyproject_path_with_use_pyproject_metadata_false(
    tmp_path: Path,
) -> None:
    """Config with use_pyproject_metadata: false should not use pyproject."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
version = "1.2.3"
"""
    )
    raw = make_build_input(include=["src/**"], use_pyproject_metadata=False)
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Should not use pyproject even though file exists
    assert "_pyproject_version" not in resolved
    assert resolved.get("display_name") != "test-package"


def test_resolve_build_config_build_pyproject_path_overrides_root_false(
    tmp_path: Path,
) -> None:
    """Build pyproject_path enables pyproject even if root metadata is false."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
version = "1.2.3"
"""
    )
    raw = make_build_input(include=["src/**"], pyproject_path="pyproject.toml")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Build-level pyproject_path should enable it
    assert resolved.get("_pyproject_version") == "1.2.3"
    assert resolved.get("display_name") == "test-package"


def test_resolve_build_config_build_use_pyproject_metadata_false_overrides_path(
    tmp_path: Path,
) -> None:
    """Build use_pyproject_metadata: false disables metadata even if path is set."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
version = "1.2.3"
"""
    )
    raw = make_build_input(
        include=["src/**"],
        pyproject_path="pyproject.toml",
        use_pyproject_metadata=False,
    )
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Build-level use_pyproject_metadata: false should disable it
    assert "_pyproject_version" not in resolved
    assert resolved.get("display_name") != "test-package"


def test_resolve_build_config_package_from_pyproject_when_enabled(
    tmp_path: Path,
) -> None:
    """Package extracted from pyproject.toml name when pyproject enabled."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "my-package"
version = "1.0.0"
"""
    )
    # Build config without package field, but with pyproject enabled
    raw = make_build_input(include=["src/**"], use_pyproject_metadata=True)
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Package should be extracted from pyproject.toml name
    assert resolved.get("package") == "my-package"
    assert resolved.get("display_name") == "my-package"


# ---------------------------------------------------------------------------
# Authors field tests
# ---------------------------------------------------------------------------


def test_resolve_build_config_authors_from_pyproject(
    tmp_path: Path,
) -> None:
    """Authors should be extracted from pyproject.toml when pyproject is enabled."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
authors = [
    {name = "Alice", email = "alice@example.com"},
    {name = "Bob"}
]
"""
    )
    raw = make_build_input(include=["src/**"], use_pyproject_metadata=True)
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved.get("authors") == "Alice <alice@example.com>, Bob"


def test_resolve_build_config_authors_cascades_from_root(
    tmp_path: Path,
) -> None:
    """Authors should be set when provided in config."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], authors="Root Author <root@example.com>")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved.get("authors") == "Root Author <root@example.com>"


def test_resolve_build_config_authors_build_overrides_root(
    tmp_path: Path,
) -> None:
    """Build-level authors should override root-level."""
    # --- setup ---
    raw = make_build_input(
        include=["src/**"], authors="Build Author <build@example.com>"
    )
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved.get("authors") == "Build Author <build@example.com>"


def test_resolve_build_config_authors_multi_build_cascades(
    tmp_path: Path,
) -> None:
    """Authors should cascade from root to all builds in multi-build configs."""
    # --- setup ---
    raw1 = make_build_input(
        include=["src1/**"], authors="Root Author <root@example.com>"
    )
    raw2 = make_build_input(
        include=["src2/**"], authors="Root Author <root@example.com>"
    )
    args = _args()

    # --- execute ---
    resolved1 = mod_resolve.resolve_build_config(raw1, args, tmp_path, tmp_path)
    resolved2 = mod_resolve.resolve_build_config(raw2, args, tmp_path, tmp_path)

    # --- validate ---
    # Both builds should get root-level authors
    assert resolved1.get("authors") == "Root Author <root@example.com>"
    assert resolved2.get("authors") == "Root Author <root@example.com>"


def test_resolve_build_config_authors_from_pyproject_when_enabled(
    tmp_path: Path,
) -> None:
    """Authors should be extracted from pyproject.toml when pyproject is enabled."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
authors = [
    {name = "Pyproject Author", email = "pyproject@example.com"}
]
"""
    )
    raw = make_build_input(include=["src/**"], use_pyproject_metadata=True)
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Should use pyproject.toml authors when enabled
    assert resolved.get("authors") == "Pyproject Author <pyproject@example.com>"


def test_resolve_build_config_authors_root_used_when_pyproject_not_enabled(
    tmp_path: Path,
) -> None:
    """Config authors should be used when pyproject is explicitly disabled."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
authors = [
    {name = "Pyproject Author", email = "pyproject@example.com"}
]
"""
    )
    raw = make_build_input(
        include=["src/**"],
        use_pyproject_metadata=False,
        authors="Root Author <root@example.com>",
    )
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Config authors should be used when pyproject is explicitly disabled
    assert resolved.get("authors") == "Root Author <root@example.com>"


def test_resolve_build_config_authors_optional_in_resolved(
    tmp_path: Path,
) -> None:
    """Authors should be optional in resolved config (NotRequired)."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Authors should not be present if not set anywhere
    assert "authors" not in resolved or resolved.get("authors") is None


# ---------------------------------------------------------------------------
# Version cascading tests
# ---------------------------------------------------------------------------


def test_resolve_build_config_version_cascades_from_root(
    tmp_path: Path,
) -> None:
    """Version should be set when provided in config."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], version="1.2.3")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved.get("version") == "1.2.3"


def test_resolve_build_config_version_build_overrides_root(
    tmp_path: Path,
) -> None:
    """Version from build config should override root config."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], version="2.0.0")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved.get("version") == "2.0.0"


def test_resolve_build_config_version_multi_build_cascades(
    tmp_path: Path,
) -> None:
    """Version should cascade from root to all builds in multi-build configs."""
    # --- setup ---
    raw1 = make_build_input(include=["src1/**"], version="1.2.3")
    raw2 = make_build_input(include=["src2/**"], version="1.2.3")
    args = _args()

    # --- execute ---
    resolved1 = mod_resolve.resolve_build_config(raw1, args, tmp_path, tmp_path)
    resolved2 = mod_resolve.resolve_build_config(raw2, args, tmp_path, tmp_path)

    # --- validate ---
    # Both builds should get root-level version
    assert resolved1.get("version") == "1.2.3"
    assert resolved2.get("version") == "1.2.3"


def test_resolve_build_config_version_optional_in_resolved(
    tmp_path: Path,
) -> None:
    """Version should be optional in resolved config (NotRequired)."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Version should not be present if not set anywhere
    assert "version" not in resolved or resolved.get("version") is None


# ---------------------------------------------------------------------------
# Parent directory traversal tests
# ---------------------------------------------------------------------------


def test_resolve_build_config_include_with_parent_from_config(
    tmp_path: Path,
) -> None:
    """Include with ../ in config should resolve relative to config_dir."""
    # --- setup ---
    shared = tmp_path / "shared"
    shared.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    raw = make_build_input(include=["../shared/pkg/**"], out="dist")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, project, project)

    # --- validate ---
    inc = resolved["include"][0]
    # Root should be config_dir (project), path should preserve ../
    assert inc["root"] == project
    assert inc["path"] == "../shared/pkg/**"
    assert inc["origin"] == "config"


def test_resolve_build_config_out_with_parent_from_config(
    tmp_path: Path,
) -> None:
    """Out with ../ in config should resolve relative to config_dir."""
    # --- setup ---
    project = tmp_path / "project"
    project.mkdir()
    raw = make_build_input(include=["src/**"], out="../outputs/dist")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, project, project)

    # --- validate ---
    out = resolved["out"]
    # Root should be config_dir (project), path should preserve ../
    assert out["root"] == project
    assert out["path"] == "../outputs/dist"
    assert out["origin"] == "config"


def test_resolve_build_config_include_with_parent_from_cli(
    tmp_path: Path,
) -> None:
    """Include with ../ from CLI should resolve relative to cwd."""
    # --- setup ---
    shared = tmp_path / "shared"
    shared.mkdir()
    cwd = tmp_path / "project"
    cwd.mkdir()
    raw = make_build_input(include=["src/**"], out="dist")
    args = _args(include=["../shared/pkg/**"])

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, cwd)

    # --- validate ---
    inc = resolved["include"][0]
    # Root should be cwd, path should preserve ../
    assert inc["root"] == cwd
    assert inc["path"] == "../shared/pkg/**"
    assert inc["origin"] == "cli"


def test_resolve_build_config_out_with_parent_from_cli(
    tmp_path: Path,
) -> None:
    """Out with ../ from CLI should resolve relative to cwd."""
    # --- setup ---
    cwd = tmp_path / "project"
    cwd.mkdir()
    raw = make_build_input(include=["src/**"], out="dist")
    args = _args(out="../outputs/dist")

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, cwd)

    # --- validate ---
    out = resolved["out"]
    # Root should be cwd, path should preserve ../
    assert out["root"] == cwd
    assert out["path"] == "../outputs/dist"
    assert out["origin"] == "cli"


def test_resolve_build_config_include_with_parent_different_config_and_cwd(
    tmp_path: Path,
) -> None:
    """Config include with ../ should use config_dir, not cwd."""
    # --- setup ---
    shared = tmp_path / "shared"
    shared.mkdir()
    config_dir = tmp_path / "config_dir"
    config_dir.mkdir()
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    # Include goes backwards from config_dir, not cwd
    raw = make_build_input(include=["../shared/pkg/**"], out="dist")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, config_dir, cwd)

    # --- validate ---
    inc = resolved["include"][0]
    # Should use config_dir as root, not cwd
    assert inc["root"] == config_dir
    assert inc["path"] == "../shared/pkg/**"
    assert inc["origin"] == "config"


def test_resolve_build_config_out_with_parent_different_config_and_cwd(
    tmp_path: Path,
) -> None:
    """Config out with ../ should use config_dir, not cwd."""
    # --- setup ---
    config_dir = tmp_path / "config_dir"
    config_dir.mkdir()
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    # Out goes backwards from config_dir, not cwd
    raw = make_build_input(include=["src/**"], out="../outputs/dist")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, config_dir, cwd)

    # --- validate ---
    out = resolved["out"]
    # Should use config_dir as root, not cwd
    assert out["root"] == config_dir
    assert out["path"] == "../outputs/dist"
    assert out["origin"] == "config"


# ---------------------------------------------------------------------------
# Shim setting tests
# ---------------------------------------------------------------------------


def test_resolve_build_config_shim_default_value(
    tmp_path: Path,
) -> None:
    """Shim setting should default to 'all' if not specified."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["shim"] == "all"


def test_resolve_build_config_shim_from_build_config(
    tmp_path: Path,
) -> None:
    """Shim setting from build config should be used."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], shim="public")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["shim"] == "public"


def test_resolve_build_config_shim_cascades_from_root(
    tmp_path: Path,
) -> None:
    """Shim setting should use default when not specified."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Default shim is "all"
    assert resolved["shim"] == "all"


def test_resolve_build_config_shim_build_overrides_root(
    tmp_path: Path,
) -> None:
    """Build-level shim setting should override root-level."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], shim="public")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["shim"] == "public"


def test_resolve_build_config_shim_validates_all_value(
    tmp_path: Path,
) -> None:
    """Shim setting should accept 'all' as a valid value."""
    # --- setup ---
    valid_shim_values = mod_apathetic_utils.literal_to_set(mod_types.ShimSetting)
    raw = make_build_input(include=["src/**"], shim="all")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["shim"] == "all"
    assert "all" in valid_shim_values


def test_resolve_build_config_shim_validates_public_value(
    tmp_path: Path,
) -> None:
    """Shim setting should accept 'public' as a valid value."""
    # --- setup ---
    valid_shim_values = mod_apathetic_utils.literal_to_set(mod_types.ShimSetting)
    raw = make_build_input(include=["src/**"], shim="public")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["shim"] == "public"
    assert "public" in valid_shim_values


def test_resolve_build_config_shim_validates_none_value(
    tmp_path: Path,
) -> None:
    """Shim setting should accept 'none' as a valid value."""
    # --- setup ---
    valid_shim_values = mod_apathetic_utils.literal_to_set(mod_types.ShimSetting)
    raw = make_build_input(include=["src/**"], shim="none")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["shim"] == "none"
    assert "none" in valid_shim_values


def test_resolve_build_config_shim_invalid_value_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Shim setting should raise error for invalid values."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], shim="invalid")
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(ValueError, match="Invalid shim value"),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_shim_invalid_root_value_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Shim setting should raise error for invalid root config values."""
    # --- setup ---
    # Use cast to allow invalid value for testing validation
    raw = make_build_input(include=["src/**"], shim="invalid")
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(ValueError, match="Invalid shim value"),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


# ---------------------------------------------------------------------------
# Module actions tests
# ---------------------------------------------------------------------------


def test_resolve_build_config_module_actions_dict_format(
    tmp_path: Path,
) -> None:
    """Module actions dict format should be accepted and normalized with defaults."""
    # --- setup ---
    raw = make_build_input(
        include=["src/**"], module_actions={"oldmodule": "newmodule"}
    )
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert "module_actions" in resolved
    assert isinstance(resolved["module_actions"], list)
    assert len(resolved["module_actions"]) == 1
    action = resolved["module_actions"][0]
    # All fields should be present with defaults applied
    # Normalized actions have all fields present
    assert action["source"] == "oldmodule"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["dest"] == "newmodule"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["action"] == "move"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["mode"] == "preserve"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["scope"] == "shim"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["affects"] == "shims"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["cleanup"] == "auto"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_resolve_build_config_module_actions_list_format(
    tmp_path: Path,
) -> None:
    """Module actions list format should be accepted with defaults applied."""
    # --- setup ---
    raw = make_build_input(
        include=["src/**"],
        module_actions=[{"source": "old", "dest": "new", "action": "move"}],
    )
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert "module_actions" in resolved
    assert isinstance(resolved["module_actions"], list)
    assert len(resolved["module_actions"]) == 1
    action = resolved["module_actions"][0]
    # All fields should be present with defaults applied
    # Normalized actions have all fields present
    assert action["source"] == "old"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["dest"] == "new"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["action"] == "move"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["mode"] == "preserve"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["scope"] == "shim"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["affects"] == "shims"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["cleanup"] == "auto"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_resolve_build_config_module_actions_cascades_from_root(
    tmp_path: Path,
) -> None:
    """Module actions should be set when provided in config with defaults applied."""
    # --- setup ---
    raw = make_build_input(
        include=["src/**"],
        module_actions=[{"source": "old", "dest": "new", "action": "move"}],
    )
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert "module_actions" in resolved
    assert isinstance(resolved["module_actions"], list)
    assert len(resolved["module_actions"]) == 1
    action = resolved["module_actions"][0]
    # All fields should be present with defaults applied
    # Normalized actions have all fields present
    assert action["source"] == "old"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["dest"] == "new"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["action"] == "move"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["mode"] == "preserve"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["scope"] == "shim"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["affects"] == "shims"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["cleanup"] == "auto"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_resolve_build_config_module_actions_build_overrides_root(
    tmp_path: Path,
) -> None:
    """Build-level module_actions should override root-level."""
    # --- setup ---
    raw = make_build_input(
        include=["src/**"], module_actions={"build_old": "build_new"}
    )
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert "module_actions" in resolved
    assert len(resolved["module_actions"]) == 1
    action = resolved["module_actions"][0]
    # Normalized actions have all fields present
    assert action["source"] == "build_old"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["dest"] == "build_new"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    # Defaults should still be applied
    assert action["action"] == "move"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["mode"] == "preserve"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["scope"] == "shim"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["affects"] == "shims"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["cleanup"] == "auto"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_resolve_build_config_module_actions_invalid_dict_key_type_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Module actions dict with non-string keys should raise error."""
    # --- setup ---
    # Use cast to allow invalid value for testing validation
    raw = cast(
        "mod_types.BuildConfig",
        {"include": ["src/**"], "module_actions": {123: "new"}},
    )
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(TypeError, match="module_actions dict keys must be strings"),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_module_actions_invalid_dict_value_type_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Module actions dict with non-string/None values should raise error."""
    # --- setup ---
    # Use cast to allow invalid value for testing validation
    raw = cast(
        "mod_types.BuildConfig",
        {"include": ["src/**"], "module_actions": {"old": 123}},
    )
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(
            ValueError, match="module_actions dict values must be strings or None"
        ),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_module_actions_list_missing_source_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Module actions list item missing 'source' should raise error."""
    # --- setup ---
    # Use cast to allow invalid value for testing validation
    raw = cast(
        "mod_types.BuildConfig",
        {"include": ["src/**"], "module_actions": [{"dest": "new"}]},
    )
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(ValueError, match=r"missing required 'source' key"),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_module_actions_list_invalid_action_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Module actions list with invalid action value should raise error."""
    # --- setup ---
    # Use cast to allow invalid value for testing validation
    raw = cast(
        "mod_types.BuildConfig",
        {
            "include": ["src/**"],
            "module_actions": [{"source": "old", "action": "invalid"}],
        },
    )
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(ValueError, match=r"module_actions.*'action'].*invalid"),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_module_actions_invalid_type_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Module actions with invalid type should raise error."""
    # --- setup ---
    # Use cast to allow invalid value for testing validation
    raw = cast(
        "mod_types.BuildConfig",
        {"include": ["src/**"], "module_actions": "invalid"},
    )
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(ValueError, match="module_actions must be dict or list"),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_module_actions_dict_format_delete(
    tmp_path: Path,
) -> None:
    """Module actions dict format with None value should create delete action."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], module_actions={"old": None})
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert len(resolved["module_actions"]) == 1
    action = resolved["module_actions"][0]
    # Normalized actions have all fields present
    assert action["source"] == "old"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["action"] == "delete"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert "dest" not in action  # dest must not be present for delete
    assert action["mode"] == "preserve"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["scope"] == "shim"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["affects"] == "shims"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["cleanup"] == "auto"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_resolve_build_config_module_actions_empty_source_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Module actions with empty source string should raise error."""
    # --- setup ---
    raw = cast(
        "mod_types.BuildConfig",
        {"include": ["src/**"], "module_actions": {"": "new"}},
    )
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(
            ValueError, match="module_actions dict keys \\(source\\) must be non-empty"
        ),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_module_actions_list_empty_source_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Module actions list with empty source string should raise error."""
    # --- setup ---
    raw = cast(
        "mod_types.BuildConfig",
        {"include": ["src/**"], "module_actions": [{"source": ""}]},
    )
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(
            ValueError, match=r"module_actions.*'source'].*must be a non-empty string"
        ),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_module_actions_move_missing_dest_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Module actions with move action missing dest should raise error."""
    # --- setup ---
    raw = cast(
        "mod_types.BuildConfig",
        {
            "include": ["src/**"],
            "module_actions": [{"source": "old", "action": "move"}],
        },
    )
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(ValueError, match="'dest' is required for 'move' action"),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_module_actions_copy_missing_dest_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Module actions with copy action missing dest should raise error."""
    # --- setup ---
    raw = cast(
        "mod_types.BuildConfig",
        {
            "include": ["src/**"],
            "module_actions": [{"source": "old", "action": "copy"}],
        },
    )
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(ValueError, match="'dest' is required for 'copy' action"),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_module_actions_delete_with_dest_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Module actions with delete action having dest should raise error."""
    # --- setup ---
    raw = cast(
        "mod_types.BuildConfig",
        {
            "include": ["src/**"],
            "module_actions": [{"source": "old", "action": "delete", "dest": "new"}],
        },
    )
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(
            ValueError, match="'dest' must not be present for 'delete' action"
        ),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_module_actions_none_normalized_to_delete(
    tmp_path: Path,
) -> None:
    """Module actions with action='none' should be normalized to 'delete'."""
    # --- setup ---
    raw = make_build_input(
        include=["src/**"],
        module_actions=[{"source": "old", "action": "none"}],
    )
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert len(resolved["module_actions"]) == 1
    action = resolved["module_actions"][0]
    # Normalized actions have all fields present
    assert action["source"] == "old"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    # Normalized from "none"
    assert action["action"] == "delete"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert "dest" not in action
    assert action["mode"] == "preserve"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["scope"] == "shim"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["affects"] == "shims"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["cleanup"] == "auto"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_resolve_build_config_module_actions_defaults_applied(
    tmp_path: Path,
) -> None:
    """Module actions should have all defaults applied when fields are missing."""
    # --- setup ---
    raw = make_build_input(
        include=["src/**"],
        module_actions=[{"source": "old", "dest": "new"}],  # Only source and dest
    )
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert len(resolved["module_actions"]) == 1
    action = resolved["module_actions"][0]
    # Normalized actions have all fields present
    assert action["source"] == "old"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["dest"] == "new"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    # Defaults applied
    assert action["action"] == "move"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["mode"] == "preserve"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    # Default for user actions
    assert action["scope"] == "shim"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["affects"] == "shims"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["cleanup"] == "auto"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_resolve_build_config_module_actions_invalid_mode_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Module actions with invalid mode should raise error."""
    # --- setup ---
    raw = cast(
        "mod_types.BuildConfig",
        {
            "include": ["src/**"],
            "module_actions": [{"source": "old", "dest": "new", "mode": "invalid"}],
        },
    )
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(ValueError, match=r"module_actions.*'mode'].*invalid"),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_module_actions_invalid_scope_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Module actions with invalid scope should raise error."""
    # --- setup ---
    raw = cast(
        "mod_types.BuildConfig",
        {
            "include": ["src/**"],
            "module_actions": [{"source": "old", "dest": "new", "scope": "invalid"}],
        },
    )
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(ValueError, match=r"module_actions.*'scope'].*invalid"),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_module_actions_invalid_affects_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Module actions with invalid affects should raise error."""
    # --- setup ---
    raw = cast(
        "mod_types.BuildConfig",
        {
            "include": ["src/**"],
            "module_actions": [{"source": "old", "dest": "new", "affects": "invalid"}],
        },
    )
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(ValueError, match=r"module_actions.*'affects'].*invalid"),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_module_actions_invalid_cleanup_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Module actions with invalid cleanup should raise error."""
    # --- setup ---
    raw = cast(
        "mod_types.BuildConfig",
        {
            "include": ["src/**"],
            "module_actions": [{"source": "old", "dest": "new", "cleanup": "invalid"}],
        },
    )
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(ValueError, match=r"module_actions.*'cleanup'].*invalid"),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_module_actions_source_path_validation(
    tmp_path: Path,
) -> None:
    """Module actions with source_path should validate it's a non-empty string."""
    # --- setup ---
    raw = make_build_input(
        include=["src/**"],
        module_actions=[
            {"source": "old", "dest": "new", "source_path": "/path/to/file.py"}
        ],
    )
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert len(resolved["module_actions"]) == 1
    action = resolved["module_actions"][0]
    # Normalized actions have all fields present
    assert action["source"] == "old"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["dest"] == "new"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["source_path"] == "/path/to/file.py"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    # Defaults should still be applied
    assert action["action"] == "move"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["mode"] == "preserve"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["scope"] == "shim"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["affects"] == "shims"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    assert action["cleanup"] == "auto"  # pyright: ignore[reportTypedDictNotRequiredAccess]


def test_resolve_build_config_module_actions_empty_source_path_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Module actions with empty source_path should raise error."""
    # --- setup ---
    raw = cast(
        "mod_types.BuildConfig",
        {
            "include": ["src/**"],
            "module_actions": [{"source": "old", "dest": "new", "source_path": ""}],
        },
    )
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(
            ValueError,
            match=r"module_actions.*'source_path'].*must be a non-empty string",
        ),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_module_actions_invalid_source_path_type_raises_error(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Module actions with non-string source_path should raise error."""
    # --- setup ---
    raw = cast(
        "mod_types.BuildConfig",
        {
            "include": ["src/**"],
            "module_actions": [{"source": "old", "dest": "new", "source_path": 123}],
        },
    )
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(
            TypeError, match=r"module_actions.*'source_path'].*must be a string"
        ),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_module_bases_defaults(
    tmp_path: Path,
) -> None:
    """Module bases should default to ['src'] if not specified."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["module_bases"] == ["src"]


def test_resolve_build_config_module_bases_build_level(
    tmp_path: Path,
) -> None:
    """Module bases should use build-level value when specified."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], module_bases=["lib", "vendor"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["module_bases"] == ["lib", "vendor"]


def test_resolve_build_config_module_bases_cascades_from_root(
    tmp_path: Path,
) -> None:
    """Module bases should be set when provided in config."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], module_bases=["lib", "vendor"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["module_bases"] == ["lib", "vendor"]


def test_resolve_build_config_module_bases_build_overrides_root(
    tmp_path: Path,
) -> None:
    """Build-level module bases should override root-level."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], module_bases=["custom"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["module_bases"] == ["custom"]


def test_resolve_build_config_module_bases_string_conversion(
    tmp_path: Path,
) -> None:
    """Module bases string should be converted to list[str] on resolve."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], module_bases="lib")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["module_bases"] == ["lib"]


def test_resolve_build_config_module_bases_string_cascades_from_root(
    tmp_path: Path,
) -> None:
    """Module bases string should be converted to list[str] on resolve."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], module_bases="lib")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["module_bases"] == ["lib"]


# ---------------------------------------------------------------------------
# Auto-include from package and module_bases
# ---------------------------------------------------------------------------


def test_resolve_build_config_auto_include_single_base_single_package(
    tmp_path: Path,
) -> None:
    """Auto-include should set includes to package found in single base."""
    # --- setup ---
    # Create package structure: src/mypkg/
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pkg_dir = src_dir / "mypkg"
    make_test_package(pkg_dir)

    # Config with package but no includes
    raw = make_build_input(package="mypkg", module_bases=["src"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert len(resolved["include"]) == 1
    inc = resolved["include"][0]
    assert inc["path"] == "src/mypkg/"
    assert inc["origin"] == "config"
    assert resolved.get("package") == "mypkg"


def test_resolve_build_config_auto_include_multiple_bases_multiple_packages(
    tmp_path: Path,
) -> None:
    """Auto-include should work with multiple bases and multiple packages."""
    # --- setup ---
    # Create packages in different bases
    src_dir = tmp_path / "src"
    lib_dir = tmp_path / "lib"
    src_dir.mkdir()
    lib_dir.mkdir()
    src_pkg = src_dir / "srcpkg"
    lib_pkg = lib_dir / "libpkg"
    make_test_package(src_pkg)
    make_test_package(lib_pkg)

    # Config with package matching first base
    raw = make_build_input(package="srcpkg", module_bases=["src", "lib"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert len(resolved["include"]) == 1
    inc = resolved["include"][0]
    assert inc["path"] == "src/srcpkg/"
    assert inc["origin"] == "config"
    assert resolved.get("package") == "srcpkg"


def test_resolve_build_config_auto_include_same_package_first_match_wins(
    tmp_path: Path,
) -> None:
    """When same package exists in multiple bases, first match wins."""
    # --- setup ---
    # Create same package name in different bases
    src_dir = tmp_path / "src"
    lib_dir = tmp_path / "lib"
    src_dir.mkdir()
    lib_dir.mkdir()
    src_pkg = src_dir / "mypkg"
    lib_pkg = lib_dir / "mypkg"
    make_test_package(src_pkg)
    make_test_package(lib_pkg)

    # Config with package matching both bases
    raw = make_build_input(package="mypkg", module_bases=["src", "lib"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Should use first match (src/mypkg), not lib/mypkg
    assert len(resolved["include"]) == 1
    inc = resolved["include"][0]
    assert inc["path"] == "src/mypkg/"
    assert inc["origin"] == "config"
    assert resolved.get("package") == "mypkg"


def test_resolve_build_config_auto_include_multiple_packages_in_single_base(
    tmp_path: Path,
) -> None:
    """Auto-include should work when multiple packages exist in single base."""
    # --- setup ---
    # Create multiple packages in same base
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pkg1_dir = src_dir / "pkg1"
    pkg2_dir = src_dir / "pkg2"
    make_test_package(pkg1_dir)
    make_test_package(pkg2_dir)

    # Config with package matching one of them
    raw = make_build_input(package="pkg2", module_bases=["src"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert len(resolved["include"]) == 1
    inc = resolved["include"][0]
    assert inc["path"] == "src/pkg2/"
    assert inc["origin"] == "config"
    assert resolved.get("package") == "pkg2"


def test_resolve_build_config_auto_include_does_not_override_existing_includes(
    tmp_path: Path,
) -> None:
    """Auto-include should not override when includes are already provided."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pkg_dir = src_dir / "mypkg"
    make_test_package(pkg_dir)

    # Config with includes already set
    raw = make_build_input(
        package="mypkg", module_bases=["src"], include=["src/other/**"]
    )
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Should keep original includes, not auto-set
    assert len(resolved["include"]) == 1
    inc = resolved["include"][0]
    assert inc["path"] == "src/other/**"
    assert inc["origin"] == "config"


def test_resolve_build_config_auto_include_does_not_override_cli_includes(
    tmp_path: Path,
) -> None:
    """Auto-include should not override when CLI --include is provided."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pkg_dir = src_dir / "mypkg"
    make_test_package(pkg_dir)

    # Config with package but no includes, CLI provides includes
    raw = make_build_input(package="mypkg", module_bases=["src"])
    args = _args(include=["cli_src/**"])

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Should use CLI includes, not auto-set
    assert len(resolved["include"]) == 1
    inc = resolved["include"][0]
    assert inc["path"] == "cli_src/**"
    assert inc["origin"] == "cli"


def test_resolve_build_config_auto_include_does_not_override_add_include(
    tmp_path: Path,
) -> None:
    """Auto-include should not override when --add-include is provided."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pkg_dir = src_dir / "mypkg"
    make_test_package(pkg_dir)

    # Config with package but no includes, CLI provides add-include
    raw = make_build_input(package="mypkg", module_bases=["src"])
    args = _args(add_include=["extra/**"])

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Should use add-include, not auto-set
    assert len(resolved["include"]) == 1
    inc = resolved["include"][0]
    assert inc["path"] == "extra/**"
    assert inc["origin"] == "cli"


def test_resolve_build_config_auto_include_does_not_set_when_package_not_found(
    tmp_path: Path,
) -> None:
    """Auto-include should not set when package is provided but not found.

    When a package is explicitly provided but doesn't exist in module_bases,
    we don't auto-set includes (respects user's explicit choice even if invalid).
    """
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pkg_dir1 = src_dir / "otherpkg"
    make_test_package(pkg_dir1)
    pkg_dir2 = src_dir / "anotherpkg"
    make_test_package(pkg_dir2)

    # Config with package that doesn't exist in module_bases
    # User explicitly provided package, so we respect it (even if invalid)
    raw = make_build_input(package="nonexistent", module_bases=["src"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Package should remain as user provided (even if not found)
    assert resolved.get("package") == "nonexistent"
    # Should not auto-set includes when package not found in module_bases
    assert len(resolved["include"]) == 0


def test_resolve_build_config_auto_include_does_not_set_when_no_package(
    tmp_path: Path,
) -> None:
    """Auto-include should set when package is auto-detected from multiple modules.

    With the new enhanced auto-detection, when multiple modules exist and no package
    is provided, step 7 (first package in module_bases order) will select the first
    module found, and includes will be auto-set based on that package.
    """
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pkg_dir1 = src_dir / "mypkg"
    make_test_package(pkg_dir1)
    pkg_dir2 = src_dir / "otherpkg"
    make_test_package(pkg_dir2)

    # Config without package
    # Multiple modules - step 7 will select first one found
    raw = make_build_input(module_bases=["src"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Package should be auto-detected (first in module_bases order)
    assert resolved.get("package") in ("mypkg", "otherpkg")
    # Includes should be auto-set based on detected package
    assert len(resolved["include"]) > 0


def test_resolve_build_config_auto_include_does_not_set_when_explicit_empty_includes(
    tmp_path: Path,
) -> None:
    """Auto-include should not set when includes are explicitly set to empty."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pkg_dir = src_dir / "mypkg"
    make_test_package(pkg_dir)

    # Config with explicitly empty includes
    raw = make_build_input(package="mypkg", module_bases=["src"], include=[])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Should respect explicit empty includes, not auto-set
    assert len(resolved["include"]) == 0


def test_resolve_build_config_auto_include_does_not_set_when_empty_module_bases(
    tmp_path: Path,
) -> None:
    """Auto-include should not set when module_bases is empty."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pkg_dir = src_dir / "mypkg"
    make_test_package(pkg_dir)

    # Config with empty module_bases (shouldn't happen in practice, but test it)
    raw = make_build_input(package="mypkg", module_bases=[])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Should not auto-set includes when module_bases is empty
    assert len(resolved["include"]) == 0


def test_resolve_build_config_auto_include_works_with_single_file_module(
    tmp_path: Path,
) -> None:
    """Auto-include should work when package is a single-file module (.py file)."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    # Create a single-file module (not a directory)
    module_file = src_dir / "mymodule.py"
    module_file.write_text('def hello():\n    return "world"\n', encoding="utf-8")

    # Config with package matching the module file
    raw = make_build_input(package="mymodule", module_bases=["src"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert len(resolved["include"]) == 1
    inc = resolved["include"][0]
    assert inc["path"] == "src/mymodule.py"
    assert inc["origin"] == "config"
    assert resolved.get("package") == "mymodule"


def test_resolve_build_config_auto_detect_single_module_when_package_not_found(
    tmp_path: Path,
) -> None:
    """Respect user's explicit package choice even if not found in module_bases.

    When a package is explicitly provided, we respect it (even if invalid).
    Auto-detection only happens when no package is provided.
    """
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pkg_dir = src_dir / "mypkg"
    make_test_package(pkg_dir)

    # Config with package that doesn't exist in module_bases
    # User explicitly provided package, so we respect it
    raw = make_build_input(package="nonexistent", module_bases=["src"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Should respect user's explicit package choice (even if not found)
    assert resolved.get("package") == "nonexistent"
    # Should not auto-set includes when package not found
    assert len(resolved["include"]) == 0


def test_resolve_build_config_auto_detect_single_module_when_no_package(
    tmp_path: Path,
) -> None:
    """Auto-detect single module when no package is provided."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pkg_dir = src_dir / "mypkg"
    make_test_package(pkg_dir)

    # Config without package
    # But there's exactly 1 module, so we should auto-detect it
    raw = make_build_input(module_bases=["src"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Should auto-detect the single module and set it as package
    assert resolved.get("package") == "mypkg"
    assert len(resolved["include"]) == 1
    inc = resolved["include"][0]
    assert inc["path"] == "src/mypkg/"
    assert inc["origin"] == "config"


def test_resolve_build_config_auto_detect_single_file_module_when_no_package(
    tmp_path: Path,
) -> None:
    """Auto-detect single file module when no package is provided."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    module_file = src_dir / "mymodule.py"
    module_file.write_text("def hello(): pass\n")

    # Config without package
    # But there's exactly 1 module file, so we should auto-detect it
    raw = make_build_input(module_bases=["src"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Should auto-detect the single module file and set it as package
    assert resolved.get("package") == "mymodule"
    assert len(resolved["include"]) == 1
    inc = resolved["include"][0]
    assert inc["path"] == "src/mymodule.py"
    assert inc["origin"] == "config"


def test_resolve_build_config_auto_include_works_with_pyproject_package(
    tmp_path: Path,
) -> None:
    """Auto-include should work when package comes from pyproject.toml."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pkg_dir = src_dir / "mypkg"
    make_test_package(pkg_dir)

    # Create pyproject.toml with package name
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "mypkg"\n',
        encoding="utf-8",
    )

    # Config with use_pyproject_metadata enabled but no includes
    raw = make_build_input(module_bases=["src"], use_pyproject_metadata=True)
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Should auto-set includes to package from pyproject.toml
    assert len(resolved["include"]) == 1
    inc = resolved["include"][0]
    assert inc["path"] == "src/mypkg/"
    assert inc["origin"] == "config"
    assert resolved.get("package") == "mypkg"


def test_resolve_build_config_infer_package_from_include_paths(
    tmp_path: Path,
) -> None:
    """Package should be inferred from include paths when not explicitly set."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pkg_dir = src_dir / "mypkg"
    make_test_package(pkg_dir)

    # Config with includes but no package
    # Step 3: Infer from include paths
    raw = make_build_input(include=["src/mypkg/**"], module_bases=["src"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Package should be inferred from include paths
    assert resolved.get("package") == "mypkg"


def test_resolve_build_config_infer_package_from_include_paths_with_init_py(
    tmp_path: Path,
) -> None:
    """Package inference should use __init__.py markers when available."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pkg_dir = src_dir / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("# package\n")
    (pkg_dir / "module.py").write_text("def hello(): pass\n")

    # Config with includes pointing to __init__.py but no package
    raw = make_build_input(
        include=["src/mypkg/__init__.py", "src/mypkg/module.py"],
        module_bases=["src"],
    )
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Package should be inferred from include paths using __init__.py marker
    assert resolved.get("package") == "mypkg"


def test_resolve_build_config_infer_package_from_include_paths_most_common(
    tmp_path: Path,
) -> None:
    """Package inference should use most common package when multiple exist."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    pkg1_dir = src_dir / "pkg1"
    pkg1_dir.mkdir()
    (pkg1_dir / "__init__.py").write_text("# pkg1\n")
    (pkg1_dir / "mod1.py").write_text("def hello1(): pass\n")
    (pkg1_dir / "mod2.py").write_text("def hello2(): pass\n")

    pkg2_dir = src_dir / "pkg2"
    pkg2_dir.mkdir()
    (pkg2_dir / "__init__.py").write_text("# pkg2\n")
    (pkg2_dir / "mod1.py").write_text("def hello3(): pass\n")

    # Config with includes pointing to multiple packages, but pkg1 appears more
    # Step 3: Infer from include paths, should use most common
    raw = make_build_input(
        include=[
            "src/pkg1/mod1.py",
            "src/pkg1/mod2.py",
            "src/pkg2/mod1.py",
        ],
        module_bases=["src"],
    )
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Package should be inferred as most common (pkg1 appears twice, pkg2 once)
    assert resolved.get("package") == "pkg1"


def test_resolve_build_config_main_function_detection_in_package_resolution(
    tmp_path: Path,
) -> None:
    """Package should be detected via main function when multiple modules exist."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create two packages
    pkg1_dir = src_dir / "pkg1"
    pkg1_dir.mkdir()
    (pkg1_dir / "module.py").write_text("def hello(): pass\n")

    pkg2_dir = src_dir / "pkg2"
    pkg2_dir.mkdir()
    (pkg2_dir / "main.py").write_text("def main():\n    pass\n")

    # Config without package, multiple modules exist
    # Step 4: Main function detection should prefer pkg2
    raw = make_build_input(module_bases=["src"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Package should be detected via main function (pkg2 has main())
    assert resolved.get("package") == "pkg2"


def test_resolve_build_config_main_function_detection_with_name_main_block(
    tmp_path: Path,
) -> None:
    """Package detection should find modules with if __name__ == '__main__' blocks."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create two packages
    pkg1_dir = src_dir / "pkg1"
    pkg1_dir.mkdir()
    (pkg1_dir / "module.py").write_text("def hello(): pass\n")

    pkg2_dir = src_dir / "pkg2"
    pkg2_dir.mkdir()
    (pkg2_dir / "main.py").write_text(
        "if __name__ == '__main__':\n    print('hello')\n"
    )

    # Config without package, multiple modules exist
    # Step 4: Main function detection should prefer pkg2
    raw = make_build_input(module_bases=["src"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    # Package should be detected via __name__ == '__main__' block (pkg2)
    assert resolved.get("package") == "pkg2"


def test_resolve_build_config_main_mode_default_value(
    tmp_path: Path,
) -> None:
    """main_mode should default to 'auto' if not specified."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["main_mode"] == "auto"


def test_resolve_build_config_main_mode_from_config(
    tmp_path: Path,
) -> None:
    """main_mode from config should be used."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], main_mode="none")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["main_mode"] == "none"


def test_resolve_build_config_main_mode_invalid_value(
    tmp_path: Path, module_logger: mod_logs.AppLogger
) -> None:
    """Invalid main_mode value should raise ValueError."""
    # --- setup ---
    raw: mod_types.RootConfig = {
        "include": ["src/**"],
        "main_mode": "invalid",  # type: ignore[typeddict-unknown-key]
    }
    args = _args()

    # --- execute & validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(ValueError, match="Invalid main_mode value"),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)


def test_resolve_build_config_main_name_default_value(
    tmp_path: Path,
) -> None:
    """main_name should default to None if not specified."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["main_name"] is None


def test_resolve_build_config_main_name_from_config(
    tmp_path: Path,
) -> None:
    """main_name from config should be used."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], main_name="mypkg.main")
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["main_name"] == "mypkg.main"


def test_resolve_build_config_main_name_none_explicit(
    tmp_path: Path,
) -> None:
    """Explicit main_name=None should be preserved."""
    # --- setup ---
    raw: mod_types.RootConfig = {
        "include": ["src/**"],
        "main_name": None,  # type: ignore[typeddict-unknown-key]
    }
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["main_name"] is None
