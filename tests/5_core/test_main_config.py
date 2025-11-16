# tests/5_core/test_main_config.py
"""Tests for main configuration parsing and logic."""

import ast
from pathlib import Path

import serger.config as mod_config
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


# Tests for find_main_function()


def test_find_main_function_main_mode_none(tmp_path: Path) -> None:
    """Test find_main_function returns None when main_mode is 'none'."""
    # --- setup ---
    config: mod_config.RootConfigResolved = {
        "include": [],
        "exclude": [],
        "strict_config": False,
        "out": {"path": "out.py", "root": tmp_path, "origin": "default"},
        "respect_gitignore": True,
        "log_level": "INFO",
        "watch_interval": 1.0,
        "dry_run": False,
        "__meta__": {
            "cli_root": tmp_path,
            "config_root": tmp_path,
        },
        "post_processing": {
            "enabled": True,
            "category_order": [],
            "categories": {},
        },
        "internal_imports": "force_strip",
        "external_imports": "top",
        "stitch_mode": "raw",
        "module_mode": "none",
        "shim": "all",
        "module_actions": [],
        "comments_mode": "keep",
        "docstring_mode": "keep",
        "module_bases": ["src"],
        "main_mode": "none",
        "main_name": None,
    }
    file_path = tmp_path / "main.py"
    file_path.write_text("def main():\n    pass\n")

    # --- execute ---
    result = mod_main_config.find_main_function(
        config=config,
        file_paths=[file_path],
        module_sources={"main.py": "def main():\n    pass\n"},
        module_names=["main"],
        package_root=tmp_path,
        file_to_include={
            file_path: {"path": "main.py", "root": tmp_path, "origin": "default"}
        },
        detected_packages=set(),
    )

    # --- verify ---
    assert result is None


def test_find_main_function_with_main_name_module_path(tmp_path: Path) -> None:
    """Test find_main_function with main_name specifying module path."""
    # --- setup ---
    config: mod_config.RootConfigResolved = {
        "include": [],
        "exclude": [],
        "strict_config": False,
        "out": {"path": "out.py", "root": tmp_path, "origin": "default"},
        "respect_gitignore": True,
        "log_level": "INFO",
        "watch_interval": 1.0,
        "dry_run": False,
        "__meta__": {
            "cli_root": tmp_path,
            "config_root": tmp_path,
        },
        "post_processing": {
            "enabled": True,
            "category_order": [],
            "categories": {},
        },
        "internal_imports": "force_strip",
        "external_imports": "top",
        "stitch_mode": "raw",
        "module_mode": "none",
        "shim": "all",
        "module_actions": [],
        "comments_mode": "keep",
        "docstring_mode": "keep",
        "module_bases": ["src"],
        "main_mode": "auto",
        "main_name": "mypkg.main",
    }
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    file_path = pkg_dir / "main.py"
    file_path.write_text("def main():\n    pass\n")

    # --- execute ---
    result = mod_main_config.find_main_function(
        config=config,
        file_paths=[file_path],
        module_sources={"mypkg.main.py": "def main():\n    pass\n"},
        module_names=["mypkg.main"],
        package_root=tmp_path,
        file_to_include={
            file_path: {"path": "mypkg/main.py", "root": tmp_path, "origin": "default"}
        },
        detected_packages={"mypkg"},
    )

    # --- verify ---
    assert result is not None
    function_name, source_file, module_path = result
    assert function_name == "main"
    assert source_file == file_path
    assert module_path == "mypkg.main"


def test_find_main_function_with_main_name_function_only(tmp_path: Path) -> None:
    """Test find_main_function with main_name specifying function name only."""
    # --- setup ---
    config: mod_config.RootConfigResolved = {
        "include": [],
        "exclude": [],
        "strict_config": False,
        "out": {"path": "out.py", "root": tmp_path, "origin": "default"},
        "respect_gitignore": True,
        "log_level": "INFO",
        "watch_interval": 1.0,
        "dry_run": False,
        "__meta__": {
            "cli_root": tmp_path,
            "config_root": tmp_path,
        },
        "post_processing": {
            "enabled": True,
            "category_order": [],
            "categories": {},
        },
        "internal_imports": "force_strip",
        "external_imports": "top",
        "stitch_mode": "raw",
        "module_mode": "none",
        "shim": "all",
        "module_actions": [],
        "comments_mode": "keep",
        "docstring_mode": "keep",
        "module_bases": ["src"],
        "main_mode": "auto",
        "main_name": "cli",
    }
    file_path = tmp_path / "main.py"
    file_path.write_text("def cli():\n    pass\n")

    # --- execute ---
    result = mod_main_config.find_main_function(
        config=config,
        file_paths=[file_path],
        module_sources={"main.py": "def cli():\n    pass\n"},
        module_names=["main"],
        package_root=tmp_path,
        file_to_include={
            file_path: {"path": "main.py", "root": tmp_path, "origin": "default"}
        },
        detected_packages=set(),
    )

    # --- verify ---
    assert result is not None
    function_name, source_file, module_path = result
    assert function_name == "cli"
    assert source_file == file_path
    assert module_path == "main"


def test_find_main_function_with_package_config(tmp_path: Path) -> None:
    """Test find_main_function with package config specified."""
    # --- setup ---
    config: mod_config.RootConfigResolved = {
        "include": [],
        "exclude": [],
        "strict_config": False,
        "out": {"path": "out.py", "root": tmp_path, "origin": "default"},
        "respect_gitignore": True,
        "log_level": "INFO",
        "watch_interval": 1.0,
        "dry_run": False,
        "__meta__": {
            "cli_root": tmp_path,
            "config_root": tmp_path,
        },
        "post_processing": {
            "enabled": True,
            "category_order": [],
            "categories": {},
        },
        "internal_imports": "force_strip",
        "external_imports": "top",
        "stitch_mode": "raw",
        "module_mode": "none",
        "shim": "all",
        "module_actions": [],
        "comments_mode": "keep",
        "docstring_mode": "keep",
        "module_bases": ["src"],
        "main_mode": "auto",
        "main_name": None,
        "package": "mypkg",
    }
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    file_path = pkg_dir / "main.py"
    file_path.write_text("def main():\n    pass\n")

    # --- execute ---
    result = mod_main_config.find_main_function(
        config=config,
        file_paths=[file_path],
        module_sources={"mypkg.main.py": "def main():\n    pass\n"},
        module_names=["mypkg.main"],
        package_root=tmp_path,
        file_to_include={
            file_path: {"path": "mypkg/main.py", "root": tmp_path, "origin": "default"}
        },
        detected_packages={"mypkg"},
    )

    # --- verify ---
    assert result is not None
    function_name, source_file, module_path = result
    assert function_name == "main"
    assert source_file == file_path
    assert module_path == "mypkg.main"


def test_find_main_function_priority_main_py(tmp_path: Path) -> None:
    """Test find_main_function prioritizes __main__.py over other files."""
    # --- setup ---
    config: mod_config.RootConfigResolved = {
        "include": [],
        "exclude": [],
        "strict_config": False,
        "out": {"path": "out.py", "root": tmp_path, "origin": "default"},
        "respect_gitignore": True,
        "log_level": "INFO",
        "watch_interval": 1.0,
        "dry_run": False,
        "__meta__": {
            "cli_root": tmp_path,
            "config_root": tmp_path,
        },
        "post_processing": {
            "enabled": True,
            "category_order": [],
            "categories": {},
        },
        "internal_imports": "force_strip",
        "external_imports": "top",
        "stitch_mode": "raw",
        "module_mode": "none",
        "shim": "all",
        "module_actions": [],
        "comments_mode": "keep",
        "docstring_mode": "keep",
        "module_bases": ["src"],
        "main_mode": "auto",
        "main_name": None,
    }
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    main_py = pkg_dir / "__main__.py"
    main_py.write_text("def main():\n    pass\n")
    other_py = pkg_dir / "other.py"
    other_py.write_text("def main():\n    pass\n")

    # --- execute ---
    result = mod_main_config.find_main_function(
        config=config,
        file_paths=[other_py, main_py],  # other.py first in list
        module_sources={
            "mypkg.other.py": "def main():\n    pass\n",
            "mypkg.__main__.py": "def main():\n    pass\n",
        },
        module_names=["mypkg.other", "mypkg.__main__"],
        package_root=tmp_path,
        file_to_include={
            other_py: {"path": "mypkg/other.py", "root": tmp_path, "origin": "default"},
            main_py: {
                "path": "mypkg/__main__.py",
                "root": tmp_path,
                "origin": "default",
            },
        },
        detected_packages={"mypkg"},
    )

    # --- verify ---
    assert result is not None
    function_name, source_file, module_path = result
    assert function_name == "main"
    assert source_file == main_py  # Should prefer __main__.py
    assert module_path == "mypkg.__main__"


def test_find_main_function_not_found(tmp_path: Path) -> None:
    """Test find_main_function returns None when function not found."""
    # --- setup ---
    config: mod_config.RootConfigResolved = {
        "include": [],
        "exclude": [],
        "strict_config": False,
        "out": {"path": "out.py", "root": tmp_path, "origin": "default"},
        "respect_gitignore": True,
        "log_level": "INFO",
        "watch_interval": 1.0,
        "dry_run": False,
        "__meta__": {
            "cli_root": tmp_path,
            "config_root": tmp_path,
        },
        "post_processing": {
            "enabled": True,
            "category_order": [],
            "categories": {},
        },
        "internal_imports": "force_strip",
        "external_imports": "top",
        "stitch_mode": "raw",
        "module_mode": "none",
        "shim": "all",
        "module_actions": [],
        "comments_mode": "keep",
        "docstring_mode": "keep",
        "module_bases": ["src"],
        "main_mode": "auto",
        "main_name": None,
    }
    file_path = tmp_path / "main.py"
    file_path.write_text("def other():\n    pass\n")

    # --- execute ---
    result = mod_main_config.find_main_function(
        config=config,
        file_paths=[file_path],
        module_sources={"main.py": "def other():\n    pass\n"},
        module_names=["main"],
        package_root=tmp_path,
        file_to_include={
            file_path: {"path": "main.py", "root": tmp_path, "origin": "default"}
        },
        detected_packages=set(),
    )

    # --- verify ---
    assert result is None


# Tests for detect_function_parameters()


def test_detect_function_parameters_no_params() -> None:
    """Test detect_function_parameters with function having no parameters."""
    # --- setup ---
    source = "def main():\n    pass\n"
    tree = ast.parse(source)
    func_node = tree.body[0]
    assert isinstance(func_node, ast.FunctionDef)

    # --- execute ---
    result = mod_main_config.detect_function_parameters(func_node)

    # --- verify ---
    assert result is False


def test_detect_function_parameters_positional_args() -> None:
    """Test detect_function_parameters with positional arguments."""
    # --- setup ---
    source = "def main(arg1, arg2):\n    pass\n"
    tree = ast.parse(source)
    func_node = tree.body[0]
    assert isinstance(func_node, ast.FunctionDef)

    # --- execute ---
    result = mod_main_config.detect_function_parameters(func_node)

    # --- verify ---
    assert result is True


def test_detect_function_parameters_star_args() -> None:
    """Test detect_function_parameters with *args."""
    # --- setup ---
    source = "def main(*args):\n    pass\n"
    tree = ast.parse(source)
    func_node = tree.body[0]
    assert isinstance(func_node, ast.FunctionDef)

    # --- execute ---
    result = mod_main_config.detect_function_parameters(func_node)

    # --- verify ---
    assert result is True


def test_detect_function_parameters_star_star_kwargs() -> None:
    """Test detect_function_parameters with **kwargs."""
    # --- setup ---
    source = "def main(**kwargs):\n    pass\n"
    tree = ast.parse(source)
    func_node = tree.body[0]
    assert isinstance(func_node, ast.FunctionDef)

    # --- execute ---
    result = mod_main_config.detect_function_parameters(func_node)

    # --- verify ---
    assert result is True


def test_detect_function_parameters_defaults() -> None:
    """Test detect_function_parameters with default values."""
    # --- setup ---
    source = "def main(arg1='default'):\n    pass\n"
    tree = ast.parse(source)
    func_node = tree.body[0]
    assert isinstance(func_node, ast.FunctionDef)

    # --- execute ---
    result = mod_main_config.detect_function_parameters(func_node)

    # --- verify ---
    assert result is True


def test_detect_function_parameters_keyword_only() -> None:
    """Test detect_function_parameters with keyword-only arguments."""
    # --- setup ---
    source = "def main(*, kwarg1):\n    pass\n"
    tree = ast.parse(source)
    func_node = tree.body[0]
    assert isinstance(func_node, ast.FunctionDef)

    # --- execute ---
    result = mod_main_config.detect_function_parameters(func_node)

    # --- verify ---
    assert result is True


def test_detect_function_parameters_combined() -> None:
    """Test detect_function_parameters with combined parameter types."""
    # --- setup ---
    source = "def main(pos1, pos2='default', *args, kwonly, **kwargs):\n    pass\n"
    tree = ast.parse(source)
    func_node = tree.body[0]
    assert isinstance(func_node, ast.FunctionDef)

    # --- execute ---
    result = mod_main_config.detect_function_parameters(func_node)

    # --- verify ---
    assert result is True


def test_detect_function_parameters_async_function() -> None:
    """Test detect_function_parameters with async function."""
    # --- setup ---
    source = "async def main(arg1):\n    pass\n"
    tree = ast.parse(source)
    func_node = tree.body[0]
    assert isinstance(func_node, ast.AsyncFunctionDef)

    # --- execute ---
    result = mod_main_config.detect_function_parameters(func_node)

    # --- verify ---
    assert result is True
