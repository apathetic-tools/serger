# tests/95_integration_output/test_subpackage_imports.py
"""Integration tests for subpackage imports in stitched singlefile.

Tests that verify subpackages work correctly in the stitched singlefile output,
including:
- Package imports (import serger.utils, apathetic_utils)
- Submodule imports (import serger.utils.utils_modules, apathetic_utils.text)
- Submodule attribute access
- Private functions in submodules
- Functions with same name as submodules not being overwritten
- Submodules with names that conflict with stdlib modules (e.g., 'types')
"""

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path
from types import ModuleType

import serger.build as mod_build
import serger.config.config_loader as mod_config_loader
import serger.config.config_resolve as mod_config_resolve


# --- only for singlefile runs ---
__runtime_mode__ = "singlefile"


def test_serger_utils_subpackage_imports() -> None:
    """Verify subpackages work correctly in singlefile mode.

    This test verifies the fix for the original issue where subpackages
    were not being recognized, causing ModuleNotFoundError.
    """
    # --- Test 1: serger.utils package import works ---

    assert "serger.utils" in sys.modules
    utils_pkg = sys.modules["serger.utils"]
    assert isinstance(utils_pkg, ModuleType)

    # --- Test 2: serger.utils submodule import works ---

    assert "serger.utils.utils_modules" in sys.modules
    utils_modules_mod = sys.modules["serger.utils.utils_modules"]
    assert isinstance(utils_modules_mod, ModuleType)

    # --- Test 3: Submodule is accessible as attribute on package ---
    assert hasattr(utils_pkg, "utils_modules"), (
        "serger.utils should have utils_modules as an attribute"
    )
    assert utils_pkg.utils_modules is utils_modules_mod, (
        "serger.utils.utils_modules attribute should point to the module"
    )

    # --- Test 4: Private functions in serger.utils submodules are accessible ---
    import serger.utils.utils_modules as mod_utils_modules  # noqa: PLC0415

    assert hasattr(mod_utils_modules, "_interpret_dest_for_module_name"), (
        "Private functions should be accessible in submodules"
    )
    assert callable(
        mod_utils_modules._interpret_dest_for_module_name  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    ), "Private function should be callable"

    # Verify we can actually call the private function
    result = mod_utils_modules._interpret_dest_for_module_name(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        Path("/test/file.py"),
        Path("/test"),
        "*.py",
        Path("dest"),
    )
    assert isinstance(result, Path), "Private function should work correctly"

    # --- Test 5: apathetic_utils package import works ---

    assert "apathetic_utils" in sys.modules
    apathetic_utils_pkg = sys.modules["apathetic_utils"]
    assert isinstance(apathetic_utils_pkg, ModuleType)

    # --- Test 6: apathetic_utils.text submodule import works ---

    assert "apathetic_utils.text" in sys.modules
    apathetic_text_mod = sys.modules["apathetic_utils.text"]
    assert isinstance(apathetic_text_mod, ModuleType)

    # --- Test 7: Submodule is accessible as attribute on package ---
    assert hasattr(apathetic_utils_pkg, "text"), (
        "apathetic_utils should have text as an attribute"
    )
    assert apathetic_utils_pkg.text is apathetic_text_mod, (
        "apathetic_utils.text attribute should point to the module"
    )

    # --- Test 8: Can import from apathetic_utils submodule ---
    import apathetic_utils.text as amod_utils_text  # noqa: PLC0415

    assert hasattr(amod_utils_text, "plural"), "Should have plural function"
    assert callable(amod_utils_text.plural), (
        "Should be able to access functions from submodule"
    )

    # --- Test 9: apathetic_utils.types submodule (conflicts with stdlib types) ---
    # This is a critical test - 'types' conflicts with stdlib 'types' module
    assert "apathetic_utils.types" in sys.modules
    apathetic_types_mod = sys.modules["apathetic_utils.types"]
    assert isinstance(apathetic_types_mod, ModuleType)

    # Verify the submodule is accessible as attribute
    assert hasattr(apathetic_utils_pkg, "types"), (
        "apathetic_utils should have types as an attribute"
    )

    # CRITICAL: Verify it's NOT the stdlib types module
    import types as stdlib_types  # noqa: PLC0415

    assert apathetic_utils_pkg.types is apathetic_types_mod, (
        "apathetic_utils.types should point to the submodule"
    )
    assert apathetic_utils_pkg.types is not stdlib_types, (
        "apathetic_utils.types should NOT be stdlib types module"
    )

    # Verify we can import it correctly
    import apathetic_utils.types as amod_utils_types  # noqa: PLC0415

    assert amod_utils_types is apathetic_types_mod, (
        "Import should resolve to submodule, not stdlib"
    )
    assert amod_utils_types is not stdlib_types, (
        "Import should NOT resolve to stdlib types"
    )

    # Verify functions from the submodule are accessible
    assert hasattr(amod_utils_types, "safe_isinstance"), (
        "Submodule should have safe_isinstance function"
    )
    assert callable(amod_utils_types.safe_isinstance), (
        "safe_isinstance should be callable"
    )


def test_subpackage_function_not_overwritten(tmp_path: Path) -> None:
    """Verify functions with same name as submodules are not overwritten.

    This tests the fix where submodule attributes were overwriting
    functions with the same name (e.g., foo() function being overwritten
    by foo module object).
    """
    # Create a test package with a module and function of the same name
    pkg_dir = tmp_path / "testpkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("# Package\n")

    # Create foo.py with a foo() function
    (pkg_dir / "foo.py").write_text(
        '"""Module foo."""\n\ndef foo():\n    return "function foo"\n'
    )

    # Stitch it

    config_file = tmp_path / ".serger.jsonc"
    config_file.write_text(
        """{
  "include": ["testpkg/**/*.py"],
  "package": "testpkg",
  "out": "stitched.py"
}
"""
    )

    args = Namespace(config=str(config_file))
    config_result = mod_config_loader.load_and_validate_config(args)
    assert config_result is not None
    _, root_cfg, _ = config_result

    config_dir = config_file.parent
    cwd = Path.cwd()
    empty_args = Namespace()
    resolved_config = mod_config_resolve.resolve_config(
        root_cfg, empty_args, config_dir, cwd
    )

    mod_build.run_build(resolved_config)

    # Load and test the stitched file
    out_file = tmp_path / "stitched.py"
    assert out_file.exists()

    spec = importlib.util.spec_from_file_location("test_stitched", out_file)
    assert spec is not None
    assert spec.loader is not None

    # Clear any existing modules
    for name in list(sys.modules.keys()):
        if name.startswith("testpkg"):
            del sys.modules[name]

    stitched_mod = importlib.util.module_from_spec(spec)
    sys.modules["test_stitched"] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    # Verify the function is accessible and not overwritten
    from testpkg.foo import foo  # type: ignore[import-not-found]  # noqa: PLC0415

    assert callable(foo), "foo should be a callable function"  # pyright: ignore[reportUnknownArgumentType]
    assert foo() == "function foo", "foo() should return the expected value"

    # Verify the module is also accessible and has the function
    assert "testpkg.foo" in sys.modules
    foo_mod = sys.modules["testpkg.foo"]
    assert isinstance(foo_mod, ModuleType), "testpkg.foo should be a module"

    # The function should be on the module (not overwritten by module object)
    assert hasattr(foo_mod, "foo"), "foo module should have foo function"
    assert callable(foo_mod.foo), "foo function should be callable on module"
    assert foo_mod.foo() == "function foo", "foo function should work on module"


def test_submodule_name_conflicts_with_stdlib_module(tmp_path: Path) -> None:
    """Verify submodules with stdlib module names work correctly.

    This tests the fix where submodules with names that conflict with
    stdlib modules (e.g., 'types') were being overwritten by the stdlib
    module when copying globals to the package module.

    The fix ensures that submodule attributes are set after copying globals,
    and that stdlib modules are overwritten if they conflict with submodule names.
    """
    # Create a test package with a submodule named 'types' (conflicts with stdlib)
    pkg_dir = tmp_path / "testpkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("# Package\n")

    # Create types.py with a function
    (pkg_dir / "types.py").write_text(
        '"""Module types (conflicts with stdlib types)."""\n\n'
        'def test_function():\n    return "from testpkg.types"\n'
    )

    # Stitch it
    config_file = tmp_path / ".serger.jsonc"
    config_file.write_text(
        """{
  "include": ["testpkg/**/*.py"],
  "package": "testpkg",
  "out": "stitched.py"
}
"""
    )

    args = Namespace(config=str(config_file))
    config_result = mod_config_loader.load_and_validate_config(args)
    assert config_result is not None
    _, root_cfg, _ = config_result

    config_dir = config_file.parent
    cwd = Path.cwd()
    empty_args = Namespace()
    resolved_config = mod_config_resolve.resolve_config(
        root_cfg, empty_args, config_dir, cwd
    )

    mod_build.run_build(resolved_config)

    # Load and test the stitched file
    out_file = tmp_path / "stitched.py"
    assert out_file.exists()

    spec = importlib.util.spec_from_file_location("test_stitched", out_file)
    assert spec is not None
    assert spec.loader is not None

    # Clear any existing modules
    for name in list(sys.modules.keys()):
        if name.startswith("testpkg"):
            del sys.modules[name]

    stitched_mod = importlib.util.module_from_spec(spec)
    sys.modules["test_stitched"] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    # Verify the submodule is registered correctly
    assert "testpkg.types" in sys.modules, (
        "testpkg.types should be registered in sys.modules"
    )
    pkg_types_mod = sys.modules["testpkg.types"]
    assert isinstance(pkg_types_mod, ModuleType), "testpkg.types should be a module"

    # Verify the package has the submodule as an attribute
    assert "testpkg" in sys.modules
    pkg = sys.modules["testpkg"]
    assert hasattr(pkg, "types"), "testpkg should have types as an attribute"

    # CRITICAL: Verify that pkg.types points to the submodule, NOT stdlib types
    import types as stdlib_types  # noqa: PLC0415

    assert pkg.types is pkg_types_mod, (
        "testpkg.types attribute should point to the submodule, not stdlib"
    )
    assert pkg.types is not stdlib_types, (
        "testpkg.types should NOT be the stdlib types module"
    )

    # Verify we can import the submodule correctly
    import testpkg.types as pkg_types  # type: ignore[import-not-found]  # noqa: PLC0415

    assert pkg_types is pkg_types_mod, (
        "Import should resolve to the submodule, not stdlib"
    )
    assert pkg_types is not stdlib_types, "Import should NOT resolve to stdlib types"

    # Verify functions from the submodule are accessible
    assert hasattr(pkg_types, "test_function"), "Submodule should have test_function"
    test_func = pkg_types.test_function  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
    assert callable(test_func), "test_function should be callable"  # pyright: ignore[reportUnknownArgumentType]
    assert test_func() == "from testpkg.types", "test_function should work correctly"

    # Verify the submodule does NOT have stdlib types attributes
    assert not hasattr(pkg_types, "ModuleType"), (
        "Submodule should not have stdlib types attributes"
    )
