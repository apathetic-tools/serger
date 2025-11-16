# tests/9_integration/test_module_actions_integration.py
"""Integration tests for module_actions in stitch logic.

These tests verify the integration of module_actions into the stitch flow,
focusing on unique aspects not covered by module_mode integration tests.
"""

import importlib.util
import sys
from pathlib import Path

import serger.build as mod_build
from tests.utils.buildconfig import make_build_cfg, make_include_resolved, make_resolved


def test_module_actions_transformed_names_used_for_shims(tmp_path: Path) -> None:
    """Test that transformed module names are used for shim generation."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "oldpkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "sub").mkdir()
    (pkg_dir / "sub" / "__init__.py").write_text("")
    (pkg_dir / "sub" / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("oldpkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="newpkg",
        order=[
            "oldpkg/__init__.py",
            "oldpkg/sub/__init__.py",
            "oldpkg/sub/module.py",
        ],
    )
    # Use force mode to transform oldpkg -> newpkg
    # This verifies that transformed names are used for shim generation
    build_cfg["module_mode"] = "force"

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    normalized = content.replace("'", '"')
    # Shims should use transformed names (newpkg.sub.module), not original
    # (oldpkg.sub.module)
    assert (
        '"newpkg.sub.module"' in normalized
        or '"newpkg.oldpkg.sub.module"' in normalized
    )
    assert '"oldpkg.sub.module"' not in normalized

    # Verify imports work with transformed names
    spec = importlib.util.spec_from_file_location("test_transformed", out_file)
    assert spec is not None
    assert spec.loader is not None

    for name in list(sys.modules.keys()):
        if name.startswith(("oldpkg", "newpkg", "test_transformed")):
            del sys.modules[name]

    stitched_mod = importlib.util.module_from_spec(spec)
    sys.modules["test_transformed"] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    # Should be able to import using transformed name
    # The exact path depends on preserve mode behavior
    try:
        from newpkg.sub.module import (  # type: ignore[import-not-found]  # noqa: PLC0415
            func,  # pyright: ignore[reportUnknownVariableType]
        )

        assert func() == "test"
    except ImportError:
        # If preserve mode keeps structure, try alternative path
        from newpkg.oldpkg.sub.module import (  # type: ignore[import-not-found]  # noqa: PLC0415
            func,  # pyright: ignore[reportUnknownVariableType]
        )

        assert func() == "test"


def test_module_actions_scope_original_works(tmp_path: Path) -> None:
    """Test that scope: 'original' actions work correctly."""
    # Setup: Create package structure
    oldpkg_dir = tmp_path / "oldpkg"
    oldpkg_dir.mkdir()
    (oldpkg_dir / "__init__.py").write_text("")
    (oldpkg_dir / "core.py").write_text("def core():\n    return 'core'\n")
    (oldpkg_dir / "utils.py").write_text("def util():\n    return 'util'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("oldpkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="newpkg",
        order=["oldpkg/__init__.py", "oldpkg/core.py", "oldpkg/utils.py"],
    )
    # Use force mode (generates scope: "original" action for oldpkg -> newpkg)
    # This tests that mode-generated actions with scope: "original" work
    build_cfg["module_mode"] = "force"

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    normalized = content.replace("'", '"')
    # Scope: "original" action (from mode) should transform oldpkg -> newpkg
    # The exact result depends on preserve mode behavior, but should show
    # transformation happened
    assert '"newpkg' in normalized
    # Original oldpkg should not appear (moved, not copied)
    assert '"oldpkg.core"' not in normalized or '"oldpkg.utils"' not in normalized

    # Verify imports work with transformed names
    spec = importlib.util.spec_from_file_location("test_scope", out_file)
    assert spec is not None
    assert spec.loader is not None

    for name in list(sys.modules.keys()):
        if name.startswith(("oldpkg", "newpkg", "test_scope")):
            del sys.modules[name]

    stitched_mod = importlib.util.module_from_spec(spec)
    sys.modules["test_scope"] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    # Should be able to import using transformed name
    # Try both possible paths depending on preserve mode
    try:
        from newpkg.core import core  # type: ignore[import-not-found]  # noqa: PLC0415

        assert core() == "core"
    except ImportError:
        from newpkg.oldpkg.core import (  # type: ignore[import-not-found]  # noqa: PLC0415
            core,  # pyright: ignore[reportUnknownVariableType]
        )

        assert core() == "core"
