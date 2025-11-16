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
from tests.utils import make_build_input


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
    module_logger: mod_logs.AppLogger,
) -> None:
    """CLI --include and --out should override config include/out."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], out="dist")
    args = _args(include=["cli_src/**"], out="cli_dist")

    # --- patch and execute ---
    with module_logger.use_level("info"):
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
    module_logger: mod_logs.AppLogger,
) -> None:
    """--add-include should append to config includes, not override."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    args = _args(add_include=["extra/**"])

    # --- patch and execute ---
    with module_logger.use_level("info"):
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
    module_logger: mod_logs.AppLogger,
) -> None:
    """When .gitignore exists, its patterns should be appended as gitignore excludes."""
    # --- setup ---
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.log\n# comment\ncache/\n")
    raw = make_build_input(include=["src/**"])
    args = _args()

    # --- patch and execute ---
    with module_logger.use_level("debug"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    git_excludes = [e for e in resolved["exclude"] if e["origin"] == "gitignore"]
    patterns = [str(e["path"]) for e in git_excludes]
    assert "*.log" in patterns
    assert "cache/" in patterns


def test_resolve_build_config_respects_cli_exclude_override(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """CLI --exclude should override config excludes."""
    # --- setup ---
    raw = make_build_input(exclude=["*.tmp"], include=["src/**"])
    args = _args(exclude=["*.bak"])

    # --- patch and execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    excl = [str(e["path"]) for e in resolved["exclude"]]
    assert "*.bak" in excl
    assert "*.tmp" not in excl


def test_resolve_build_config_respects_dest_override(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """IncludeResolved with explicit dest should survive resolution unchanged."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], out="dist")
    args = _args()

    # --- patch and execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    out = resolved["out"]
    assert out["origin"] == "config"
    assert out["root"] == tmp_path
    assert out["path"] == "dist"


def test_resolve_build_config_respect_gitignore_false(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """If --no-gitignore is passed, .gitignore patterns are not loaded."""
    # --- setup ---
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.log\n")
    raw = make_build_input(include=["src/**"], respect_gitignore=False)
    args = _args(respect_gitignore=False)

    # --- patch and execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert all(e["origin"] != "gitignore" for e in resolved["exclude"])
    assert resolved["respect_gitignore"] is False


def test_resolve_build_config_add_exclude_extends(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    # --- setup ---
    raw = make_build_input(exclude=["*.tmp"], include=["src/**"])
    args = _args(add_exclude=["*.log"])

    # --- patch and execute ---
    with module_logger.use_level("info"):
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
    root_cfg: mod_types.RootConfig = {"respect_gitignore": False}
    raw = make_build_input(include=["src/**"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path, root_cfg)

    # --- validate ---
    assert resolved["respect_gitignore"] is False


def test_resolve_build_config_preserves_trailing_slash(tmp_path: Path) -> None:
    # --- setup ---
    raw: mod_types.BuildConfig = {"include": ["src/"], "out": "dist"}
    args = Namespace()  # empty placeholder

    # --- execute ---
    result = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path, {})
    inc_path = result["include"][0]["path"]

    # --- validate ---
    assert isinstance(inc_path, str)
    assert inc_path.endswith("/"), f"trailing slash lost: {inc_path!r}"


def test_resolve_build_config_warns_for_missing_include_root(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Warn if include root directory does not exist and pattern is not a glob."""
    # --- setup ---
    missing_root = tmp_path / "nonexistent_root"
    raw = make_build_input(include=[f"{missing_root}/src"])
    args = _args()

    # --- patch and execute ---
    with module_logger.use_level("info"):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    out = capsys.readouterr().err.lower()
    assert "Include root does not exist".lower() in out


def test_resolve_build_config_warns_for_missing_absolute_include(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Warn if absolute include path does not exist and pattern is not a glob."""
    # --- setup ---
    abs_missing = tmp_path / "abs_missing_dir"
    raw = make_build_input(include=[str(abs_missing)])
    args = _args()

    # --- patch and execute ---
    with module_logger.use_level("info"):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    out = capsys.readouterr().err.lower()
    assert "Include path does not exist".lower() in out


def test_resolve_build_config_warns_for_missing_relative_include(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Warn if relative include path does not exist under an existing root."""
    # --- setup ---
    existing_root = tmp_path
    raw = make_build_input(include=["missing_rel_dir"])
    args = _args()

    # --- patch and execute ---
    with module_logger.use_level("info"):
        mod_resolve.resolve_build_config(raw, args, existing_root, tmp_path)

    # --- validate ---
    out = capsys.readouterr().err.lower()
    assert "Include path does not exist".lower() in out


def test_resolve_build_config_include_with_dest_from_config(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    with module_logger.use_level("info"):
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
    module_logger: mod_logs.AppLogger,
) -> None:
    """CLI includes with dest (path:dest format) should be parsed."""
    # --- setup ---
    raw = make_build_input(include=["config_src/**"])
    args = _args(include=["src/**", "assets/:static", "docs/:help"])

    # --- execute ---
    with module_logger.use_level("info"):
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
    module_logger: mod_logs.AppLogger,
) -> None:
    """--add-include with dest should extend config includes."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    args = _args(add_include=["assets/:static", "docs/:help"])

    # --- execute ---
    with module_logger.use_level("info"):
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
    module_logger: mod_logs.AppLogger,
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
    with module_logger.use_level("info"):
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
    module_logger: mod_logs.AppLogger,
) -> None:
    """Windows drive letters without dest should not be parsed as dest."""
    # --- setup ---
    raw = make_build_input(include=["config_src/**"])
    # Test drive letters - these should NOT be split as path:dest
    args = _args(include=["C:", "D:\\"])

    # --- execute ---
    with module_logger.use_level("info"):
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
    module_logger: mod_logs.AppLogger,
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
    raw = make_build_input(include=["src/**"], use_pyproject=True)
    root_cfg: mod_types.RootConfig = {"builds": [raw]}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    assert resolved.get("display_name") == "test-package"
    assert resolved.get("package") == "test-package"
    assert resolved.get("description") == "A test package"
    assert resolved.get("authors") == "Test Author <test@example.com>"
    assert resolved.get("license_header") == "MIT"
    assert resolved.get("_pyproject_version") == "1.2.3"


def test_resolve_build_config_single_build_respects_use_pyproject_false(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Single build should respect explicit use_pyproject: false for all metadata."""
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
    raw = make_build_input(include=["src/**"], use_pyproject=False)
    root_cfg: mod_types.RootConfig = {"builds": [raw]}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    # No metadata should be extracted when use_pyproject is false
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
    # Package should not fallback to pyproject.toml name when use_pyproject is false
    assert "package" not in resolved or resolved.get("package") != "test-package"


def test_resolve_build_config_multi_build_requires_opt_in(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Multi-build should require explicit opt-in to use pyproject.toml."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
version = "1.2.3"
"""
    )
    raw1 = make_build_input(include=["src1/**"])
    raw2 = make_build_input(include=["src2/**"])
    root_cfg: mod_types.RootConfig = {"builds": [raw1, raw2]}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw1, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    # Should not use pyproject.toml without explicit opt-in
    assert (
        "display_name" not in resolved or resolved.get("display_name") != "test-package"
    )
    assert "_pyproject_version" not in resolved


def test_resolve_build_config_multi_build_with_opt_in(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    raw1 = make_build_input(include=["src1/**"], use_pyproject=True)
    raw2 = make_build_input(include=["src2/**"])
    root_cfg: mod_types.RootConfig = {"builds": [raw1, raw2]}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw1, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    assert resolved.get("display_name") == "test-package"
    assert resolved.get("description") == "A test package"
    assert resolved.get("_pyproject_version") == "1.2.3"


def test_resolve_build_config_path_resolution_build_level(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
        include=["src/**"], pyproject_path="custom.toml", use_pyproject=True
    )
    root_cfg: mod_types.RootConfig = {"builds": [raw]}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    assert resolved.get("display_name") == "custom-package"
    assert resolved.get("_pyproject_version") == "2.0.0"


def test_resolve_build_config_path_resolution_root_level(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    raw = make_build_input(include=["src/**"])
    root_cfg: mod_types.RootConfig = {"builds": [raw], "pyproject_path": "root.toml"}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    assert resolved.get("display_name") == "root-package"
    assert resolved.get("_pyproject_version") == "3.0.0"


def test_resolve_build_config_root_use_pyproject_enables_for_all_builds(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Root-level use_pyproject=True should enable pyproject for all builds."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
version = "1.2.3"
description = "A test package"
"""
    )
    raw1 = make_build_input(include=["src1/**"])
    raw2 = make_build_input(include=["src2/**"])
    root_cfg: mod_types.RootConfig = {
        "builds": [raw1, raw2],
        "use_pyproject": True,
    }
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved1 = mod_resolve.resolve_build_config(
            raw1, args, tmp_path, tmp_path, root_cfg
        )
        resolved2 = mod_resolve.resolve_build_config(
            raw2, args, tmp_path, tmp_path, root_cfg
        )

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
    module_logger: mod_logs.AppLogger,
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
        use_pyproject=True,
    )
    root_cfg: mod_types.RootConfig = {"builds": [raw]}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

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
    module_logger: mod_logs.AppLogger,
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
    root_cfg: mod_types.RootConfig = {"builds": [{}]}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

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
    module_logger: mod_logs.AppLogger,
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
    raw = make_build_input(include=["src/**"], use_pyproject=False)
    # Configless build: minimal root_cfg with only builds
    root_cfg: mod_types.RootConfig = {"builds": [{}]}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    # Configless builds should not extract pyproject.toml metadata when disabled
    assert resolved.get("display_name") != "test-package"
    assert resolved.get("package") != "test-package"
    assert resolved.get("description") != "A test package"
    assert resolved.get("license_header") != "MIT"
    assert "_pyproject_version" not in resolved


def test_resolve_build_config_root_pyproject_path_with_use_pyproject_false(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Root pyproject_path with use_pyproject: false should not use pyproject."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
version = "1.2.3"
"""
    )
    raw = make_build_input(include=["src/**"])
    root_cfg: mod_types.RootConfig = {
        "builds": [raw],
        "pyproject_path": "pyproject.toml",
        "use_pyproject": False,
    }
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    # Should not use pyproject even though path is set
    assert "_pyproject_version" not in resolved
    assert resolved.get("display_name") != "test-package"


def test_resolve_build_config_build_pyproject_path_overrides_root_false(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Build pyproject_path enables pyproject even if root use_pyproject is false."""
    # --- setup ---
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "test-package"
version = "1.2.3"
"""
    )
    raw = make_build_input(include=["src/**"], pyproject_path="pyproject.toml")
    root_cfg: mod_types.RootConfig = {
        "builds": [raw],
        "use_pyproject": False,
    }
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    # Build-level pyproject_path should enable it
    assert resolved.get("_pyproject_version") == "1.2.3"
    assert resolved.get("display_name") == "test-package"


def test_resolve_build_config_build_use_pyproject_false_overrides_pyproject_path(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Build use_pyproject: false disables pyproject even if pyproject_path is set."""
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
        use_pyproject=False,
    )
    root_cfg: mod_types.RootConfig = {
        "builds": [raw],
        "use_pyproject": False,
    }
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    # Build-level use_pyproject: false should disable it
    assert "_pyproject_version" not in resolved
    assert resolved.get("display_name") != "test-package"


def test_resolve_build_config_package_from_pyproject_when_enabled(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    raw = make_build_input(include=["src/**"], use_pyproject=True)
    root_cfg: mod_types.RootConfig = {"builds": [raw]}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    # Package should be extracted from pyproject.toml name
    assert resolved.get("package") == "my-package"
    assert resolved.get("display_name") == "my-package"


# ---------------------------------------------------------------------------
# Authors field tests
# ---------------------------------------------------------------------------


def test_resolve_build_config_authors_from_pyproject(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    raw = make_build_input(include=["src/**"], use_pyproject=True)
    root_cfg: mod_types.RootConfig = {"builds": [raw]}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    assert resolved.get("authors") == "Alice <alice@example.com>, Bob"


def test_resolve_build_config_authors_cascades_from_root(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Authors should cascade from root config to all builds."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    root_cfg: mod_types.RootConfig = {
        "builds": [raw],
        "authors": "Root Author <root@example.com>",
    }
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    assert resolved.get("authors") == "Root Author <root@example.com>"


def test_resolve_build_config_authors_build_overrides_root(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Build-level authors should override root-level."""
    # --- setup ---
    raw = make_build_input(
        include=["src/**"], authors="Build Author <build@example.com>"
    )
    root_cfg: mod_types.RootConfig = {
        "builds": [raw],
        "authors": "Root Author <root@example.com>",
    }
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    assert resolved.get("authors") == "Build Author <build@example.com>"


def test_resolve_build_config_authors_multi_build_cascades(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Authors should cascade from root to all builds in multi-build configs."""
    # --- setup ---
    raw1 = make_build_input(include=["src1/**"])
    raw2 = make_build_input(include=["src2/**"])
    root_cfg: mod_types.RootConfig = {
        "builds": [raw1, raw2],
        "authors": "Root Author <root@example.com>",
    }
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved1 = mod_resolve.resolve_build_config(
            raw1, args, tmp_path, tmp_path, root_cfg
        )
        resolved2 = mod_resolve.resolve_build_config(
            raw2, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    # Both builds should get root-level authors
    assert resolved1.get("authors") == "Root Author <root@example.com>"
    assert resolved2.get("authors") == "Root Author <root@example.com>"


def test_resolve_build_config_authors_from_pyproject_when_enabled(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    raw = make_build_input(include=["src/**"], use_pyproject=True)
    root_cfg: mod_types.RootConfig = {"builds": [raw]}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    # Should use pyproject.toml authors when enabled
    assert resolved.get("authors") == "Pyproject Author <pyproject@example.com>"


def test_resolve_build_config_authors_root_used_when_pyproject_not_enabled(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Root-level authors should be used when pyproject is not enabled."""
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
    raw = make_build_input(include=["src/**"])
    root_cfg: mod_types.RootConfig = {
        "builds": [raw],
        "authors": "Root Author <root@example.com>",
    }
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    # Root-level authors should be used when pyproject is not enabled
    assert resolved.get("authors") == "Root Author <root@example.com>"


def test_resolve_build_config_authors_optional_in_resolved(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Authors should be optional in resolved config (NotRequired)."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    root_cfg: mod_types.RootConfig = {"builds": [raw]}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    # Authors should not be present if not set anywhere
    assert "authors" not in resolved or resolved.get("authors") is None


# ---------------------------------------------------------------------------
# Version cascading tests
# ---------------------------------------------------------------------------


def test_resolve_build_config_version_cascades_from_root(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Version should cascade from root config to all builds."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    root_cfg: mod_types.RootConfig = {
        "builds": [raw],
        "version": "1.2.3",
    }
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    assert resolved.get("version") == "1.2.3"


def test_resolve_build_config_version_build_overrides_root(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Version from build config should override root config."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], version="2.0.0")
    root_cfg: mod_types.RootConfig = {
        "builds": [raw],
        "version": "1.2.3",
    }
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    assert resolved.get("version") == "2.0.0"


def test_resolve_build_config_version_multi_build_cascades(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Version should cascade from root to all builds in multi-build configs."""
    # --- setup ---
    raw1 = make_build_input(include=["src1/**"])
    raw2 = make_build_input(include=["src2/**"])
    root_cfg: mod_types.RootConfig = {
        "builds": [raw1, raw2],
        "version": "1.2.3",
    }
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved1 = mod_resolve.resolve_build_config(
            raw1, args, tmp_path, tmp_path, root_cfg
        )
        resolved2 = mod_resolve.resolve_build_config(
            raw2, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    # Both builds should get root-level version
    assert resolved1.get("version") == "1.2.3"
    assert resolved2.get("version") == "1.2.3"


def test_resolve_build_config_version_optional_in_resolved(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Version should be optional in resolved config (NotRequired)."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    root_cfg: mod_types.RootConfig = {"builds": [raw]}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    # Version should not be present if not set anywhere
    assert "version" not in resolved or resolved.get("version") is None


# ---------------------------------------------------------------------------
# Parent directory traversal tests
# ---------------------------------------------------------------------------


def test_resolve_build_config_include_with_parent_from_config(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, project, project)

    # --- validate ---
    inc = resolved["include"][0]
    # Root should be config_dir (project), path should preserve ../
    assert inc["root"] == project
    assert inc["path"] == "../shared/pkg/**"
    assert inc["origin"] == "config"


def test_resolve_build_config_out_with_parent_from_config(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Out with ../ in config should resolve relative to config_dir."""
    # --- setup ---
    project = tmp_path / "project"
    project.mkdir()
    raw = make_build_input(include=["src/**"], out="../outputs/dist")
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, project, project)

    # --- validate ---
    out = resolved["out"]
    # Root should be config_dir (project), path should preserve ../
    assert out["root"] == project
    assert out["path"] == "../outputs/dist"
    assert out["origin"] == "config"


def test_resolve_build_config_include_with_parent_from_cli(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, cwd)

    # --- validate ---
    inc = resolved["include"][0]
    # Root should be cwd, path should preserve ../
    assert inc["root"] == cwd
    assert inc["path"] == "../shared/pkg/**"
    assert inc["origin"] == "cli"


def test_resolve_build_config_out_with_parent_from_cli(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Out with ../ from CLI should resolve relative to cwd."""
    # --- setup ---
    cwd = tmp_path / "project"
    cwd.mkdir()
    raw = make_build_input(include=["src/**"], out="dist")
    args = _args(out="../outputs/dist")

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, cwd)

    # --- validate ---
    out = resolved["out"]
    # Root should be cwd, path should preserve ../
    assert out["root"] == cwd
    assert out["path"] == "../outputs/dist"
    assert out["origin"] == "cli"


def test_resolve_build_config_include_with_parent_different_config_and_cwd(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, config_dir, cwd)

    # --- validate ---
    inc = resolved["include"][0]
    # Should use config_dir as root, not cwd
    assert inc["root"] == config_dir
    assert inc["path"] == "../shared/pkg/**"
    assert inc["origin"] == "config"


def test_resolve_build_config_out_with_parent_different_config_and_cwd(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    with module_logger.use_level("info"):
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
    module_logger: mod_logs.AppLogger,
) -> None:
    """Shim setting should default to 'all' if not specified."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["shim"] == "all"


def test_resolve_build_config_shim_from_build_config(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Shim setting from build config should be used."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], shim="public")
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["shim"] == "public"


def test_resolve_build_config_shim_cascades_from_root(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Shim setting should cascade from root config if not in build config."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    root_cfg: mod_types.RootConfig = {"shim": "none"}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    assert resolved["shim"] == "none"


def test_resolve_build_config_shim_build_overrides_root(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Build-level shim setting should override root-level."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], shim="public")
    root_cfg: mod_types.RootConfig = {"shim": "none"}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    assert resolved["shim"] == "public"


def test_resolve_build_config_shim_validates_all_value(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Shim setting should accept 'all' as a valid value."""
    # --- setup ---
    valid_shim_values = mod_apathetic_utils.literal_to_set(mod_types.ShimSetting)
    raw = make_build_input(include=["src/**"], shim="all")
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["shim"] == "all"
    assert "all" in valid_shim_values


def test_resolve_build_config_shim_validates_public_value(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Shim setting should accept 'public' as a valid value."""
    # --- setup ---
    valid_shim_values = mod_apathetic_utils.literal_to_set(mod_types.ShimSetting)
    raw = make_build_input(include=["src/**"], shim="public")
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["shim"] == "public"
    assert "public" in valid_shim_values


def test_resolve_build_config_shim_validates_none_value(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Shim setting should accept 'none' as a valid value."""
    # --- setup ---
    valid_shim_values = mod_apathetic_utils.literal_to_set(mod_types.ShimSetting)
    raw = make_build_input(include=["src/**"], shim="none")
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["shim"] == "none"
    assert "none" in valid_shim_values


def test_resolve_build_config_shim_invalid_value_raises_error(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Shim setting should raise error for invalid root config values."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    # Use cast to allow invalid value for testing validation
    root_cfg = cast("mod_types.RootConfig", {"shim": "invalid"})
    args = _args()

    # --- execute and validate ---
    with (
        module_logger.use_level("info"),
        pytest.raises(ValueError, match="Invalid shim value"),
    ):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path, root_cfg)


# ---------------------------------------------------------------------------
# Module actions tests
# ---------------------------------------------------------------------------


def test_resolve_build_config_module_actions_dict_format(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Module actions dict format should be accepted and normalized with defaults."""
    # --- setup ---
    raw = make_build_input(
        include=["src/**"], module_actions={"oldmodule": "newmodule"}
    )
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
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
    module_logger: mod_logs.AppLogger,
) -> None:
    """Module actions list format should be accepted with defaults applied."""
    # --- setup ---
    raw = make_build_input(
        include=["src/**"],
        module_actions=[{"source": "old", "dest": "new", "action": "move"}],
    )
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
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
    module_logger: mod_logs.AppLogger,
) -> None:
    """Module actions should cascade from root config with defaults applied."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    root_cfg: mod_types.RootConfig = {"module_actions": {"old": "new"}}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

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
    module_logger: mod_logs.AppLogger,
) -> None:
    """Build-level module_actions should override root-level."""
    # --- setup ---
    raw = make_build_input(
        include=["src/**"], module_actions={"build_old": "build_new"}
    )
    root_cfg: mod_types.RootConfig = {"module_actions": {"root_old": "root_new"}}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    module_logger: mod_logs.AppLogger,
) -> None:
    """Module actions dict format with None value should create delete action."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], module_actions={"old": None})
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    module_logger: mod_logs.AppLogger,
) -> None:
    """Module actions with action='none' should be normalized to 'delete'."""
    # --- setup ---
    raw = make_build_input(
        include=["src/**"],
        module_actions=[{"source": "old", "action": "none"}],
    )
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
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
    module_logger: mod_logs.AppLogger,
) -> None:
    """Module actions should have all defaults applied when fields are missing."""
    # --- setup ---
    raw = make_build_input(
        include=["src/**"],
        module_actions=[{"source": "old", "dest": "new"}],  # Only source and dest
    )
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    module_logger: mod_logs.AppLogger,
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
    with module_logger.use_level("info"):
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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
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
    module_logger: mod_logs.AppLogger,
) -> None:
    """Module bases should default to ['src'] if not specified."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["module_bases"] == ["src"]


def test_resolve_build_config_module_bases_build_level(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Module bases should use build-level value when specified."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], module_bases=["lib", "vendor"])
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["module_bases"] == ["lib", "vendor"]


def test_resolve_build_config_module_bases_cascades_from_root(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Module bases should cascade from root config if not in build config."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    root_cfg: mod_types.RootConfig = {"module_bases": ["lib", "vendor"]}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    assert resolved["module_bases"] == ["lib", "vendor"]


def test_resolve_build_config_module_bases_build_overrides_root(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Build-level module bases should override root-level."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], module_bases=["custom"])
    root_cfg: mod_types.RootConfig = {"module_bases": ["lib", "vendor"]}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    assert resolved["module_bases"] == ["custom"]


def test_resolve_build_config_module_bases_string_conversion(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Module bases string should be converted to list[str] on resolve."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], module_bases="lib")
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["module_bases"] == ["lib"]


def test_resolve_build_config_module_bases_string_cascades_from_root(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Module bases string from root should be converted to list[str] on resolve."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    root_cfg: mod_types.RootConfig = {"module_bases": "lib"}
    args = _args()

    # --- execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(
            raw, args, tmp_path, tmp_path, root_cfg
        )

    # --- validate ---
    assert resolved["module_bases"] == ["lib"]
