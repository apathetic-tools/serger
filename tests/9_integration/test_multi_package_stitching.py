# tests/9_integration/test_multi_package_stitching.py
"""Integration tests for multi-package stitching support.

Tests that serger can stitch multiple packages together and that the shims
correctly reflect all packages that were imported.
"""

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path
from types import ModuleType

import serger.build as mod_build
import serger.config.config_loader as mod_config_loader
import serger.config.config_resolve as mod_config_resolve
from tests.utils.buildconfig import make_build_cfg, make_include_resolved, make_resolved


def test_multi_package_stitching_with_shims(tmp_path: Path) -> None:
    """Test stitching two packages together and verify shims work correctly."""
    # --- Setup: Create two separate packages ---
    pkg1_dir = tmp_path / "pkg1"
    pkg2_dir = tmp_path / "pkg2"
    pkg1_dir.mkdir()
    pkg2_dir.mkdir()

    # Package 1: pkg1/__init__.py and pkg1/module1.py
    (pkg1_dir / "__init__.py").write_text("# Package 1\n__version__ = '1.0.0'\n")
    (pkg1_dir / "module1.py").write_text(
        '"""Module 1 from package 1."""\n\ndef func1():\n    '
        'return "from pkg1.module1"\n'
    )

    # Package 2: pkg2/__init__.py and pkg2/module2.py
    (pkg2_dir / "__init__.py").write_text("# Package 2\n__version__ = '2.0.0'\n")
    (pkg2_dir / "module2.py").write_text(
        '"""Module 2 from package 2."""\n\ndef func2():\n    '
        'return "from pkg2.module2"\n'
    )

    # --- Create build config ---
    out_file = tmp_path / "stitched.py"
    includes = [
        make_include_resolved("pkg1/**/*.py", tmp_path),
        make_include_resolved("pkg2/**/*.py", tmp_path),
    ]

    build_cfg = make_build_cfg(
        tmp_path,
        includes,
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="pkg1",  # Primary package name
        order=[
            "pkg1/__init__.py",
            "pkg1/module1.py",
            "pkg2/__init__.py",
            "pkg2/module2.py",
        ],
    )

    # --- Execute stitch ---
    mod_build.run_build(build_cfg)

    # --- Verify output file exists ---
    assert out_file.exists(), "Stitched file should be created"

    content = out_file.read_text()

    # --- Verify both packages' modules are included ---
    assert "# === pkg1.__init__ ===" in content
    assert "# === pkg1.module1 ===" in content
    assert "# === pkg2.__init__ ===" in content
    assert "# === pkg2.module2 ===" in content

    # --- Verify shims are created for both packages ---
    assert "# --- import shims for single-file runtime ---" in content

    # Check for loop-based shim generation
    assert "for _name in" in content
    assert "sys.modules[_name] = _mod" in content

    # Normalize quotes for easier assertion (shims use double quotes in generated code)
    normalized_content = content.replace("'", '"')

    # Check that shims exist for pkg1 modules
    assert '"pkg1.__init__"' in normalized_content
    assert '"pkg1.module1"' in normalized_content

    # Check that shims exist for pkg2 modules
    assert '"pkg2.__init__"' in normalized_content
    assert '"pkg2.module2"' in normalized_content

    # --- Verify shims work by importing the stitched file ---
    spec = importlib.util.spec_from_file_location("stitched_test", out_file)
    assert spec is not None
    assert spec.loader is not None

    # Clear any existing modules
    for name in list(sys.modules.keys()):
        if name.startswith(("pkg1", "pkg2")):
            del sys.modules[name]

    # Load the stitched module
    stitched_mod: ModuleType = importlib.util.module_from_spec(spec)
    sys.modules["stitched_test"] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    # --- Verify shims were created in sys.modules ---
    assert "pkg1.__init__" in sys.modules
    assert "pkg1.module1" in sys.modules
    assert "pkg2.__init__" in sys.modules
    assert "pkg2.module2" in sys.modules

    # --- Verify packages are isolated (different module objects) ---
    pkg1_mod = sys.modules["pkg1.module1"]
    pkg2_mod = sys.modules["pkg2.module2"]
    assert pkg1_mod is not pkg2_mod, "Packages should have separate module objects"

    # --- Verify modules within same package share module object ---
    pkg1_init = sys.modules["pkg1.__init__"]
    assert pkg1_init is pkg1_mod, "Modules in same package should share module object"

    pkg2_init = sys.modules["pkg2.__init__"]
    assert pkg2_init is pkg2_mod, "Modules in same package should share module object"

    # --- Verify imports work correctly ---
    from pkg1.module1 import func1  # type: ignore[import-not-found]  # noqa: PLC0415
    from pkg2.module2 import func2  # type: ignore[import-not-found]  # noqa: PLC0415

    assert func1() == "from pkg1.module1"
    assert func2() == "from pkg2.module2"


def test_multi_package_stitching_via_config_file(tmp_path: Path) -> None:
    """Test multi-package stitching using a config file."""
    # --- Setup: Create two separate packages ---
    pkg1_dir = tmp_path / "pkg1"
    pkg2_dir = tmp_path / "pkg2"
    pkg1_dir.mkdir()
    pkg2_dir.mkdir()

    # Add __init__.py files to make them proper packages
    (pkg1_dir / "__init__.py").write_text("")
    (pkg2_dir / "__init__.py").write_text("")

    (pkg1_dir / "foo.py").write_text("def foo():\n    return 'foo from pkg1'\n")
    (pkg2_dir / "bar.py").write_text("def bar():\n    return 'bar from pkg2'\n")

    # --- Create config file ---
    config_file = tmp_path / ".serger.jsonc"
    config_file.write_text(
        """{
  "include": [
    "pkg1/**/*.py",
    "pkg2/**/*.py"
  ],
  "exclude": [
    "**/__init__.py"
  ],
  "package": "pkg1",
  "order": [
    "pkg1/foo.py",
    "pkg2/bar.py"
  ],
  "out": "stitched.py"
}
"""
    )

    # --- Execute via CLI simulation (using run_build directly) ---
    # Load config
    args = Namespace(config=str(config_file))
    config_result = mod_config_loader.load_and_validate_config(args)
    assert config_result is not None
    _, root_cfg, _ = config_result

    # Resolve config
    config_dir = config_file.parent
    cwd = Path.cwd()
    empty_args = Namespace()
    resolved_root = mod_config_resolve.resolve_config(
        root_cfg, empty_args, config_dir, cwd
    )
    # Execute build
    mod_build.run_build(resolved_root)

    # --- Verify output ---
    out_file = tmp_path / "stitched.py"
    assert out_file.exists()

    content = out_file.read_text()

    # Verify both packages are stitched
    # Module names are derived from paths relative to package root
    assert "# === pkg1.foo ===" in content or "# === foo ===" in content
    assert "# === pkg2.bar ===" in content or "# === bar ===" in content

    # Verify shims for both packages
    # Module names are derived from paths and include package prefix
    # (pkg1.foo, pkg2.bar). The shims should use the full module names
    # with package prefix. Check for loop-based shim generation
    assert "for _name in" in content
    assert "sys.modules[_name] = _mod" in content
    # Normalize quotes for easier assertion (shims use double quotes in generated code)
    normalized_content = content.replace("'", '"')
    assert '"pkg1.foo"' in normalized_content
    assert '"pkg2.bar"' in normalized_content

    # Verify imports work
    spec = importlib.util.spec_from_file_location("stitched_test2", out_file)
    assert spec is not None
    assert spec.loader is not None

    for name in list(sys.modules.keys()):
        if name.startswith(("pkg1", "pkg2")):
            del sys.modules[name]

    stitched_mod = importlib.util.module_from_spec(spec)
    sys.modules["stitched_test2"] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    from pkg1.foo import foo  # type: ignore[import-not-found]  # noqa: PLC0415
    from pkg2.bar import bar  # type: ignore[import-not-found]  # noqa: PLC0415

    assert foo() == "foo from pkg1"
    assert bar() == "bar from pkg2"


def test_multi_package_stitching_three_packages(tmp_path: Path) -> None:
    """Test stitching three packages together."""
    # --- Setup: Create three separate packages ---
    pkg1_dir = tmp_path / "pkg1"
    pkg2_dir = tmp_path / "pkg2"
    pkg3_dir = tmp_path / "pkg3"
    pkg1_dir.mkdir()
    pkg2_dir.mkdir()
    pkg3_dir.mkdir()

    (pkg1_dir / "__init__.py").write_text("# Package 1\n")
    (pkg1_dir / "module1.py").write_text('def func1():\n    return "from pkg1"\n')

    (pkg2_dir / "__init__.py").write_text("# Package 2\n")
    (pkg2_dir / "module2.py").write_text('def func2():\n    return "from pkg2"\n')

    (pkg3_dir / "__init__.py").write_text("# Package 3\n")
    (pkg3_dir / "module3.py").write_text('def func3():\n    return "from pkg3"\n')

    # --- Create build config ---
    out_file = tmp_path / "stitched.py"
    includes = [
        make_include_resolved("pkg1/**/*.py", tmp_path),
        make_include_resolved("pkg2/**/*.py", tmp_path),
        make_include_resolved("pkg3/**/*.py", tmp_path),
    ]

    build_cfg = make_build_cfg(
        tmp_path,
        includes,
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="pkg1",
        order=[
            "pkg1/__init__.py",
            "pkg1/module1.py",
            "pkg2/__init__.py",
            "pkg2/module2.py",
            "pkg3/__init__.py",
            "pkg3/module3.py",
        ],
    )

    # --- Execute stitch ---
    mod_build.run_build(build_cfg)

    # --- Verify output file exists ---
    assert out_file.exists()

    content = out_file.read_text()

    # --- Verify all packages' modules are included ---
    assert "# === pkg1.__init__ ===" in content
    assert "# === pkg1.module1 ===" in content
    assert "# === pkg2.__init__ ===" in content
    assert "# === pkg2.module2 ===" in content
    assert "# === pkg3.__init__ ===" in content
    assert "# === pkg3.module3 ===" in content

    # --- Verify shims are created for all packages ---
    normalized_content = content.replace("'", '"')
    assert '"pkg1.__init__"' in normalized_content
    assert '"pkg1.module1"' in normalized_content
    assert '"pkg2.__init__"' in normalized_content
    assert '"pkg2.module2"' in normalized_content
    assert '"pkg3.__init__"' in normalized_content
    assert '"pkg3.module3"' in normalized_content

    # --- Verify imports work ---
    spec = importlib.util.spec_from_file_location("stitched_test3", out_file)
    assert spec is not None
    assert spec.loader is not None

    for name in list(sys.modules.keys()):
        if name.startswith(("pkg1", "pkg2", "pkg3")):
            del sys.modules[name]

    stitched_mod = importlib.util.module_from_spec(spec)
    sys.modules["stitched_test3"] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    from pkg1.module1 import (  # pyright: ignore[reportMissingImports]  # noqa: PLC0415
        func1,  # pyright: ignore[reportUnknownVariableType]
    )
    from pkg2.module2 import (  # pyright: ignore[reportMissingImports]  # noqa: PLC0415
        func2,  # pyright: ignore[reportUnknownVariableType]
    )
    from pkg3.module3 import func3  # type: ignore[import-not-found]  # noqa: PLC0415

    assert func1() == "from pkg1"
    assert func2() == "from pkg2"
    assert func3() == "from pkg3"


def test_multi_package_auto_discover_order_with_cross_package_imports(
    tmp_path: Path,
) -> None:
    """Test auto-discovery of order when stitching multiple packages with cross-package imports."""  # noqa: E501
    # --- Setup: Create two packages with cross-package dependencies ---
    pkg1_dir = tmp_path / "pkg1"
    pkg2_dir = tmp_path / "pkg2"
    pkg1_dir.mkdir()
    pkg2_dir.mkdir()

    # Add __init__.py files to make them proper packages
    (pkg1_dir / "__init__.py").write_text("")
    (pkg2_dir / "__init__.py").write_text("")

    # Package 1: base module (no dependencies)
    (pkg1_dir / "base.py").write_text("BASE = 1\n")

    # Package 2: derived module that imports from pkg1
    (pkg2_dir / "derived.py").write_text(
        "from pkg1.base import BASE\n\nDERIVED = BASE + 1\n"
    )

    # Package 2: main module that imports from pkg2.derived
    (pkg2_dir / "main.py").write_text(
        "from pkg2.derived import DERIVED\n\nMAIN = DERIVED + 1\n"
    )

    # --- Create build config WITHOUT explicit order ---
    out_file = tmp_path / "stitched.py"
    includes = [
        make_include_resolved("pkg1/**/*.py", tmp_path),
        make_include_resolved("pkg2/**/*.py", tmp_path),
    ]
    excludes = [
        make_resolved("**/__init__.py", tmp_path),
    ]

    build_cfg = make_build_cfg(
        tmp_path,
        includes,
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="pkg1",  # Primary package name
        exclude=excludes,
        # No order specified - should auto-discover
    )

    # --- Execute stitch ---
    mod_build.run_build(build_cfg)

    # --- Verify output file exists ---
    assert out_file.exists(), "Stitched file should be created"

    content = out_file.read_text()

    # --- Verify all modules are included ---
    assert "# === pkg1.base ===" in content
    assert "# === pkg2.derived ===" in content
    assert "# === pkg2.main ===" in content

    # --- Verify order is correct (pkg1.base before pkg2.derived before pkg2.main) ---
    base_pos = content.find("BASE = 1")
    derived_pos = content.find("DERIVED = BASE + 1")
    main_pos = content.find("MAIN = DERIVED + 1")

    assert base_pos < derived_pos < main_pos, (
        "Auto-discovered order should respect cross-package dependencies: "
        f"pkg1.base at {base_pos}, pkg2.derived at {derived_pos}, "
        f"pkg2.main at {main_pos}"
    )

    # --- Verify shims are created for both packages ---
    normalized_content = content.replace("'", '"')
    assert '"pkg1.base"' in normalized_content
    assert '"pkg2.derived"' in normalized_content
    assert '"pkg2.main"' in normalized_content

    # --- Verify imports work correctly ---
    spec = importlib.util.spec_from_file_location("stitched_test_auto", out_file)
    assert spec is not None
    assert spec.loader is not None

    for name in list(sys.modules.keys()):
        if name.startswith(("pkg1", "pkg2")):
            del sys.modules[name]

    stitched_mod = importlib.util.module_from_spec(spec)
    sys.modules["stitched_test_auto"] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    from pkg1.base import BASE  # type: ignore[import-not-found]  # noqa: PLC0415
    from pkg2.derived import DERIVED  # type: ignore[import-not-found]  # noqa: PLC0415
    from pkg2.main import MAIN  # type: ignore[import-not-found]  # noqa: PLC0415

    assert BASE == 1
    assert DERIVED == 2  # noqa: PLR2004
    assert MAIN == 3  # noqa: PLR2004
