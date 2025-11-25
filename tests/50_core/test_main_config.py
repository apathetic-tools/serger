# tests/50_core/test_main_config.py
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
        "validate_config": False,
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
        "source_bases": ["src"],
        "main_mode": "none",
        "main_name": None,
        "disable_build_timestamp": False,
        "license": "",
        "display_name": "",
        "description": "",
        "authors": "",
        "repo": "",
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
        "validate_config": False,
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
        "source_bases": ["src"],
        "main_mode": "auto",
        "main_name": "mypkg.main",
        "disable_build_timestamp": False,
        "license": "",
        "display_name": "",
        "description": "",
        "authors": "",
        "repo": "",
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
        "validate_config": False,
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
        "source_bases": ["src"],
        "main_mode": "auto",
        "main_name": "cli",
        "disable_build_timestamp": False,
        "license": "",
        "display_name": "",
        "description": "",
        "authors": "",
        "repo": "",
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
        "validate_config": False,
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
        "source_bases": ["src"],
        "main_mode": "auto",
        "main_name": None,
        "disable_build_timestamp": False,
        "package": "mypkg",
        "license": "",
        "display_name": "",
        "description": "",
        "authors": "",
        "repo": "",
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
        "validate_config": False,
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
        "source_bases": ["src"],
        "main_mode": "auto",
        "main_name": None,
        "disable_build_timestamp": False,
        "license": "",
        "display_name": "",
        "description": "",
        "authors": "",
        "repo": "",
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
        "validate_config": False,
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
        "source_bases": ["src"],
        "main_mode": "auto",
        "main_name": None,
        "disable_build_timestamp": False,
        "license": "",
        "display_name": "",
        "description": "",
        "authors": "",
        "repo": "",
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


# Tests for _extract_top_level_function_names()


def test_extract_top_level_function_names_single_function() -> None:
    """Test _extract_top_level_function_names with a single function."""
    # --- setup ---
    source = "def main():\n    pass\n"

    # --- execute ---
    names = mod_main_config._extract_top_level_function_names(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    assert names == {"main"}


def test_extract_top_level_function_names_multiple_functions() -> None:
    """Test _extract_top_level_function_names with multiple functions."""
    # --- setup ---
    source = (
        "def func1():\n    pass\n\ndef func2():\n    pass\n\ndef func3():\n    pass\n"
    )

    # --- execute ---
    names = mod_main_config._extract_top_level_function_names(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    assert names == {"func1", "func2", "func3"}


def test_extract_top_level_function_names_async_function() -> None:
    """Test _extract_top_level_function_names with async function."""
    # --- setup ---
    source = "async def main():\n    pass\n"

    # --- execute ---
    names = mod_main_config._extract_top_level_function_names(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    assert names == {"main"}


def test_extract_top_level_function_names_mixed_sync_async() -> None:
    """Test _extract_top_level_function_names with mixed sync and async functions."""
    # --- setup ---
    source = "def sync_func():\n    pass\n\nasync def async_func():\n    pass\n"

    # --- execute ---
    names = mod_main_config._extract_top_level_function_names(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    assert names == {"sync_func", "async_func"}


def test_extract_top_level_function_names_no_functions() -> None:
    """Test _extract_top_level_function_names with no functions."""
    # --- setup ---
    source = "x = 1\ny = 2\n"

    # --- execute ---
    names = mod_main_config._extract_top_level_function_names(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    assert names == set()


def test_extract_top_level_function_names_nested_functions() -> None:
    """Test _extract_top_level_function_names ignores nested functions."""
    # --- setup ---
    source = "def outer():\n    def inner():\n        pass\n    return inner\n"

    # --- execute ---
    names = mod_main_config._extract_top_level_function_names(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    # Should only include top-level function, not nested one
    assert names == {"outer"}


def test_extract_top_level_function_names_syntax_error() -> None:
    """Test _extract_top_level_function_names handles syntax errors gracefully."""
    # --- setup ---
    source = "def main(\n    # Invalid syntax"

    # --- execute ---
    names = mod_main_config._extract_top_level_function_names(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    # Should return empty set on syntax error
    assert names == set()


def test_extract_top_level_function_names_empty_source() -> None:
    """Test _extract_top_level_function_names with empty source."""
    # --- setup ---
    source = ""

    # --- execute ---
    names = mod_main_config._extract_top_level_function_names(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    assert names == set()


def test_extract_top_level_function_names_with_classes() -> None:
    """Test _extract_top_level_function_names with classes (should ignore methods)."""
    # --- setup ---
    source = (
        "def top_level():\n    pass\n\n"
        "class MyClass:\n    def method(self):\n        pass\n"
    )

    # --- execute ---
    names = mod_main_config._extract_top_level_function_names(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    # Should only include top-level function, not class methods
    assert names == {"top_level"}


def test_extract_top_level_function_names_duplicate_names() -> None:
    """Test _extract_top_level_function_names handles duplicate function names."""
    # --- setup ---
    # Note: This is invalid Python, but we test the extraction behavior
    # In practice, Python would raise a SyntaxError, but we test the extraction
    # to ensure it returns a set (which naturally handles duplicates)
    source = "def func():\n    pass\n\ndef func():\n    pass\n"

    # --- execute ---
    names = mod_main_config._extract_top_level_function_names(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    # Set should contain only one instance of "func"
    assert names == {"func"}


# Tests for _extract_main_guards()


def test_extract_main_guards_single_guard() -> None:
    """Test _extract_main_guards with a single __main__ guard."""
    # --- setup ---
    source = "def main():\n    pass\n\nif __name__ == '__main__':\n    main()\n"

    # --- execute ---
    guards = mod_main_config._extract_main_guards(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    assert len(guards) == 1
    start_line, end_line = guards[0]
    assert start_line == 4  # noqa: PLR2004  # 1-indexed line where guard starts
    assert end_line is not None
    assert end_line >= start_line


def test_extract_main_guards_multiple_guards() -> None:
    """Test _extract_main_guards with multiple __main__ guards."""
    # --- setup ---
    source = (
        "if __name__ == '__main__':\n"
        "    pass\n"
        "\n"
        "def func():\n"
        "    pass\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    func()\n"
    )

    # --- execute ---
    guards = mod_main_config._extract_main_guards(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    assert len(guards) == 2  # noqa: PLR2004
    # Both guards should be detected
    assert guards[0][0] == 1  # First guard starts at line 1
    assert guards[1][0] == 7  # noqa: PLR2004  # Second guard starts at line 7


def test_extract_main_guards_no_guards() -> None:
    """Test _extract_main_guards with no __main__ guards."""
    # --- setup ---
    source = "def main():\n    pass\n"

    # --- execute ---
    guards = mod_main_config._extract_main_guards(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    assert len(guards) == 0


def test_extract_main_guards_double_quotes() -> None:
    """Test _extract_main_guards with double quotes in __main__ guard."""
    # --- setup ---
    source = 'def main():\n    pass\n\nif __name__ == "__main__":\n    main()\n'

    # --- execute ---
    guards = mod_main_config._extract_main_guards(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    assert len(guards) == 1
    start_line, end_line = guards[0]
    assert start_line == 4  # noqa: PLR2004
    assert end_line is not None


def test_extract_main_guards_not_main_guard() -> None:
    """Test _extract_main_guards ignores non-__main__ guards."""
    # --- setup ---
    source = (
        "if __name__ == 'other':\n    pass\n\nif something == '__main__':\n    pass\n"
    )

    # --- execute ---
    guards = mod_main_config._extract_main_guards(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    assert len(guards) == 0


def test_extract_main_guards_nested_guard() -> None:
    """Test _extract_main_guards only finds top-level guards."""
    # --- setup ---
    source = (
        "def func():\n"
        "    if __name__ == '__main__':\n"
        "        pass\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    func()\n"
    )

    # --- execute ---
    guards = mod_main_config._extract_main_guards(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    # Should only find the top-level guard, not the nested one
    assert len(guards) == 1
    start_line, _end_line = guards[0]
    assert start_line == 5  # noqa: PLR2004  # Top-level guard starts at line 5


def test_extract_main_guards_syntax_error() -> None:
    """Test _extract_main_guards handles syntax errors gracefully."""
    # --- setup ---
    source = "def main(\n    # Invalid syntax"

    # --- execute ---
    guards = mod_main_config._extract_main_guards(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    # Should return empty list on syntax error
    assert len(guards) == 0


def test_extract_main_guards_empty_source() -> None:
    """Test _extract_main_guards with empty source."""
    # --- setup ---
    source = ""

    # --- execute ---
    guards = mod_main_config._extract_main_guards(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    assert len(guards) == 0


def test_extract_main_guards_complex_block() -> None:
    """Test _extract_main_guards with complex __main__ block."""
    # --- setup ---
    source = (
        "def func1():\n"
        "    pass\n"
        "\n"
        "def func2():\n"
        "    pass\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    func1()\n"
        "    func2()\n"
        "    print('done')\n"
    )

    # --- execute ---
    guards = mod_main_config._extract_main_guards(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    assert len(guards) == 1
    start_line, end_line = guards[0]
    assert start_line == 7  # noqa: PLR2004  # Guard starts at line 7
    assert end_line is not None
    assert end_line > start_line  # Should span multiple lines


def test_extract_main_guards_conditional_import() -> None:
    """Test _extract_main_guards with conditional import before guard."""
    # --- setup ---
    source = (
        "import sys\n"
        "\n"
        "if sys.platform == 'win32':\n"
        "    import win32api\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    print('hello')\n"
    )

    # --- execute ---
    guards = mod_main_config._extract_main_guards(source)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    # --- verify ---
    assert len(guards) == 1
    start_line, _end_line = guards[0]
    assert start_line == 6  # noqa: PLR2004  # Guard starts at line 6


# Tests for detect_main_blocks()


def test_detect_main_blocks_single_block(tmp_path: Path) -> None:
    """Test detect_main_blocks with a single __main__ block."""
    # --- setup ---
    file_path = tmp_path / "main.py"
    file_path.write_text(
        "def main():\n    pass\n\nif __name__ == '__main__':\n    main()\n"
    )

    # --- execute ---
    blocks = mod_main_config.detect_main_blocks(
        file_paths=[file_path],
        package_root=tmp_path,
        file_to_include={
            file_path: {"path": "main.py", "root": tmp_path, "origin": "default"}
        },
        detected_packages=set(),
    )

    # --- verify ---
    assert len(blocks) == 1
    assert blocks[0].file_path == file_path
    assert "if __name__ == '__main__':" in blocks[0].content
    assert blocks[0].module_name == "main"


def test_detect_main_blocks_multiple_blocks(tmp_path: Path) -> None:
    """Test detect_main_blocks with multiple __main__ blocks."""
    # --- setup ---
    file1 = tmp_path / "file1.py"
    file1.write_text(
        "def func1():\n    pass\n\nif __name__ == '__main__':\n    func1()\n"
    )
    file2 = tmp_path / "file2.py"
    file2.write_text(
        "def func2():\n    pass\n\nif __name__ == '__main__':\n    func2()\n"
    )

    # --- execute ---
    blocks = mod_main_config.detect_main_blocks(
        file_paths=[file1, file2],
        package_root=tmp_path,
        file_to_include={
            file1: {"path": "file1.py", "root": tmp_path, "origin": "default"},
            file2: {"path": "file2.py", "root": tmp_path, "origin": "default"},
        },
        detected_packages=set(),
    )

    # --- verify ---
    expected_block_count = 2
    assert len(blocks) == expected_block_count
    assert {b.file_path for b in blocks} == {file1, file2}


def test_detect_main_blocks_no_blocks(tmp_path: Path) -> None:
    """Test detect_main_blocks with no __main__ blocks."""
    # --- setup ---
    file_path = tmp_path / "main.py"
    file_path.write_text("def main():\n    pass\n")

    # --- execute ---
    blocks = mod_main_config.detect_main_blocks(
        file_paths=[file_path],
        package_root=tmp_path,
        file_to_include={
            file_path: {"path": "main.py", "root": tmp_path, "origin": "default"}
        },
        detected_packages=set(),
    )

    # --- verify ---
    assert len(blocks) == 0


def test_detect_main_blocks_with_package(tmp_path: Path) -> None:
    """Test detect_main_blocks with package structure."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    file_path = pkg_dir / "main.py"
    file_path.write_text(
        "def main():\n    pass\n\nif __name__ == '__main__':\n    main()\n"
    )

    # --- execute ---
    blocks = mod_main_config.detect_main_blocks(
        file_paths=[file_path],
        package_root=tmp_path,
        file_to_include={
            file_path: {"path": "mypkg/main.py", "root": tmp_path, "origin": "default"}
        },
        detected_packages={"mypkg"},
    )

    # --- verify ---
    assert len(blocks) == 1
    assert blocks[0].module_name == "mypkg.main"


def test_detect_main_blocks_double_quotes(tmp_path: Path) -> None:
    """Test detect_main_blocks with double quotes in __main__ guard."""
    # --- setup ---
    file_path = tmp_path / "main.py"
    file_path.write_text(
        'def main():\n    pass\n\nif __name__ == "__main__":\n    main()\n'
    )

    # --- execute ---
    blocks = mod_main_config.detect_main_blocks(
        file_paths=[file_path],
        package_root=tmp_path,
        file_to_include={
            file_path: {"path": "main.py", "root": tmp_path, "origin": "default"}
        },
        detected_packages=set(),
    )

    # --- verify ---
    assert len(blocks) == 1
    assert blocks[0].file_path == file_path


# Tests for select_main_block()


def test_select_main_block_priority_same_file(tmp_path: Path) -> None:
    """Test select_main_block prioritizes block in same file as main function."""
    # --- setup ---
    file1 = tmp_path / "file1.py"
    file1.write_text(
        "def main():\n    pass\n\nif __name__ == '__main__':\n    main()\n"
    )
    file2 = tmp_path / "file2.py"
    file2.write_text(
        "def other():\n    pass\n\nif __name__ == '__main__':\n    other()\n"
    )

    blocks = mod_main_config.detect_main_blocks(
        file_paths=[file1, file2],
        package_root=tmp_path,
        file_to_include={
            file1: {"path": "file1.py", "root": tmp_path, "origin": "default"},
            file2: {"path": "file2.py", "root": tmp_path, "origin": "default"},
        },
        detected_packages=set(),
    )

    # Main function is in file1
    main_result = ("main", file1, "file1")

    # --- execute ---
    selected = mod_main_config.select_main_block(
        main_blocks=blocks,
        main_function_result=main_result,
        file_paths=[file1, file2],
        module_names=["file1", "file2"],
    )

    # --- verify ---
    assert selected is not None
    assert selected.file_path == file1  # Should select block from same file


def test_select_main_block_priority_same_package(tmp_path: Path) -> None:
    """Test select_main_block prioritizes block in same package as main function."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    file1 = pkg_dir / "main.py"
    file1.write_text("def main():\n    pass\n")
    file2 = pkg_dir / "other.py"
    file2.write_text("if __name__ == '__main__':\n    pass\n")

    blocks = mod_main_config.detect_main_blocks(
        file_paths=[file1, file2],
        package_root=tmp_path,
        file_to_include={
            file1: {"path": "mypkg/main.py", "root": tmp_path, "origin": "default"},
            file2: {"path": "mypkg/other.py", "root": tmp_path, "origin": "default"},
        },
        detected_packages={"mypkg"},
    )

    # Main function is in file1 (mypkg.main)
    main_result = ("main", file1, "mypkg.main")

    # --- execute ---
    selected = mod_main_config.select_main_block(
        main_blocks=blocks,
        main_function_result=main_result,
        file_paths=[file1, file2],
        module_names=["mypkg.main", "mypkg.other"],
    )

    # --- verify ---
    assert selected is not None
    assert selected.file_path == file2  # Should select block from same package


def test_select_main_block_priority_earliest_include(tmp_path: Path) -> None:
    """Test select_main_block uses earliest include when no main function match."""
    # --- setup ---
    file1 = tmp_path / "file1.py"
    file1.write_text("if __name__ == '__main__':\n    pass\n")
    file2 = tmp_path / "file2.py"
    file2.write_text("if __name__ == '__main__':\n    pass\n")

    blocks = mod_main_config.detect_main_blocks(
        file_paths=[file1, file2],
        package_root=tmp_path,
        file_to_include={
            file1: {"path": "file1.py", "root": tmp_path, "origin": "default"},
            file2: {"path": "file2.py", "root": tmp_path, "origin": "default"},
        },
        detected_packages=set(),
    )

    # No main function
    main_result = None

    # --- execute ---
    selected = mod_main_config.select_main_block(
        main_blocks=blocks,
        main_function_result=main_result,
        file_paths=[file1, file2],
        module_names=["file1", "file2"],
    )

    # --- verify ---
    assert selected is not None
    assert selected.file_path == file1  # Should select earliest in include order


def test_detect_collisions_no_main_function() -> None:
    """Test collision detection when no main function is found."""
    # --- setup ---
    main_function_result = None
    module_sources: dict[str, str] = {
        "mypkg.module1.py": "def main():\n    pass\n",
        "mypkg.module2.py": "def main():\n    pass\n",
    }
    module_names = ["mypkg.module1", "mypkg.module2"]

    # --- execute ---
    collisions = mod_main_config.detect_collisions(
        main_function_result=main_function_result,
        module_sources=module_sources,
        module_names=module_names,
    )

    # --- verify ---
    assert collisions == []


def test_detect_collisions_no_collisions() -> None:
    """Test collision detection when no collisions exist."""
    # --- setup ---
    main_function_result = ("main", Path("/fake/path/module1.py"), "mypkg.module1")
    module_sources: dict[str, str] = {
        "mypkg.module1.py": "def main():\n    pass\n",
        "mypkg.module2.py": "def other():\n    pass\n",
    }
    module_names = ["mypkg.module1", "mypkg.module2"]

    # --- execute ---
    collisions = mod_main_config.detect_collisions(
        main_function_result=main_function_result,
        module_sources=module_sources,
        module_names=module_names,
    )

    # --- verify ---
    assert len(collisions) == 1
    assert collisions[0].module_name == "mypkg.module1"
    assert collisions[0].function_name == "main"
    assert collisions[0].is_main is True


def test_detect_collisions_with_collisions() -> None:
    """Test collision detection when collisions exist."""
    # --- setup ---
    main_function_result = ("main", Path("/fake/path/module1.py"), "mypkg.module1")
    module_sources: dict[str, str] = {
        "mypkg.module1.py": "def main():\n    pass\n",
        "mypkg.module2.py": "def main():\n    pass\n",
        "mypkg.module3.py": "def main():\n    pass\n",
    }
    module_names = ["mypkg.module1", "mypkg.module2", "mypkg.module3"]

    # --- execute ---
    collisions = mod_main_config.detect_collisions(
        main_function_result=main_function_result,
        module_sources=module_sources,
        module_names=module_names,
    )

    # --- verify ---
    expected_collision_count = 3
    assert len(collisions) == expected_collision_count
    # Check main function is marked correctly
    main_collision = next(c for c in collisions if c.module_name == "mypkg.module1")
    assert main_collision.is_main is True
    # Check other collisions are marked as non-main
    other_collisions = [c for c in collisions if c.module_name != "mypkg.module1"]
    assert all(not c.is_main for c in other_collisions)


def test_generate_auto_renames_no_collisions() -> None:
    """Test auto-rename generation when no collisions exist."""
    # --- setup ---
    main_function_result = ("main", Path("/fake/path/module1.py"), "mypkg.module1")
    collisions: list[mod_main_config.FunctionCollision] = [
        mod_main_config.FunctionCollision(
            module_name="mypkg.module1",
            function_name="main",
            is_main=True,
        )
    ]

    # --- execute ---
    renames = mod_main_config.generate_auto_renames(
        collisions=collisions,
        main_function_result=main_function_result,
    )

    # --- verify ---
    assert renames == {}


def test_generate_auto_renames_with_collisions() -> None:
    """Test auto-rename generation when collisions exist."""
    # --- setup ---
    main_function_result = ("main", Path("/fake/path/module1.py"), "mypkg.module1")
    collisions: list[mod_main_config.FunctionCollision] = [
        mod_main_config.FunctionCollision(
            module_name="mypkg.module1",
            function_name="main",
            is_main=True,
        ),
        mod_main_config.FunctionCollision(
            module_name="mypkg.module2",
            function_name="main",
            is_main=False,
        ),
        mod_main_config.FunctionCollision(
            module_name="mypkg.module3",
            function_name="main",
            is_main=False,
        ),
    ]

    # --- execute ---
    renames = mod_main_config.generate_auto_renames(
        collisions=collisions,
        main_function_result=main_function_result,
    )

    # --- verify ---
    expected_rename_count = 2
    assert len(renames) == expected_rename_count
    assert renames["mypkg.module2"] == "main_1"
    assert renames["mypkg.module3"] == "main_2"
    # Main function should not be in renames
    assert "mypkg.module1" not in renames


def test_generate_auto_renames_deterministic_order() -> None:
    """Test that auto-renames are generated in deterministic order."""
    # --- setup ---
    main_function_result = ("cli", Path("/fake/path/module1.py"), "mypkg.module1")
    # Create collisions in non-sorted order
    collisions: list[mod_main_config.FunctionCollision] = [
        mod_main_config.FunctionCollision(
            module_name="mypkg.module3",
            function_name="cli",
            is_main=False,
        ),
        mod_main_config.FunctionCollision(
            module_name="mypkg.module1",
            function_name="cli",
            is_main=True,
        ),
        mod_main_config.FunctionCollision(
            module_name="mypkg.module2",
            function_name="cli",
            is_main=False,
        ),
    ]

    # --- execute ---
    renames = mod_main_config.generate_auto_renames(
        collisions=collisions,
        main_function_result=main_function_result,
    )

    # --- verify ---
    # Should be sorted by module name
    expected_rename_count = 2
    assert len(renames) == expected_rename_count
    assert renames["mypkg.module2"] == "cli_1"
    assert renames["mypkg.module3"] == "cli_2"


def test_rename_function_in_source_simple() -> None:
    """Test renaming a simple function in source code."""
    # --- setup ---
    source = "def main():\n    pass\n"
    old_name = "main"
    new_name = "main_1"

    # --- execute ---
    result = mod_main_config.rename_function_in_source(source, old_name, new_name)

    # --- verify ---
    assert "def main_1():" in result
    assert "def main():" not in result


def test_rename_function_in_source_with_whitespace() -> None:
    """Test renaming a function with surrounding whitespace."""
    # --- setup ---
    # Test with a top-level function (main functions are always top-level)
    # with some whitespace/comments around it
    source = "\n# Comment\n\ndef main():\n    pass\n\n# Another comment\n"
    old_name = "main"
    new_name = "main_1"

    # --- execute ---
    result = mod_main_config.rename_function_in_source(source, old_name, new_name)

    # --- verify ---
    # The function name should be changed
    assert "main_1" in result
    # The old name should not appear as a function definition
    assert "def main():" not in result or "def main_1():" in result


def test_rename_function_in_source_async() -> None:
    """Test renaming an async function."""
    # --- setup ---
    source = "async def main():\n    pass\n"
    old_name = "main"
    new_name = "main_1"

    # --- execute ---
    result = mod_main_config.rename_function_in_source(source, old_name, new_name)

    # --- verify ---
    assert "async def main_1():" in result
    assert "async def main():" not in result


def test_rename_function_in_source_multiple_functions() -> None:
    """Test renaming when multiple functions exist (only rename target)."""
    # --- setup ---
    source = (
        "def other():\n    pass\n\ndef main():\n    pass\n\ndef helper():\n    pass\n"
    )
    old_name = "main"
    new_name = "main_1"

    # --- execute ---
    result = mod_main_config.rename_function_in_source(source, old_name, new_name)

    # --- verify ---
    assert "def other():" in result
    assert "def main_1():" in result
    assert "def main():" not in result
    assert "def helper():" in result


def test_rename_function_in_source_invalid_syntax() -> None:
    """Test renaming when source has invalid syntax (should return original)."""
    # --- setup ---
    source = "def main(\n    # Invalid syntax"
    old_name = "main"
    new_name = "main_1"

    # --- execute ---
    result = mod_main_config.rename_function_in_source(source, old_name, new_name)

    # --- verify ---
    # Should return original source if parsing fails
    assert result == source


def test_select_main_block_no_blocks() -> None:
    """Test select_main_block returns None when no blocks provided."""
    # --- execute ---
    selected = mod_main_config.select_main_block(
        main_blocks=[],
        main_function_result=None,
        file_paths=[],
        module_names=[],
    )

    # --- verify ---
    assert selected is None
