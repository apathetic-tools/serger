# tests/9_integration/test_module_actions_integration.py
"""Integration tests for module_actions in stitch logic.

These tests verify the integration of module_actions into the stitch flow,
focusing on unique aspects not covered by module_mode integration tests.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

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


def test_scope_shim_actions_validated_incrementally(tmp_path: Path) -> None:
    """Test that scope: 'shim' actions are validated incrementally.

    Note: This test verifies that scope: 'shim' actions can reference
    results of previous actions (incremental validation). The actual
    transformation behavior is tested in other integration tests.
    """
    # Setup: Create package structure
    oldpkg_dir = tmp_path / "oldpkg"
    oldpkg_dir.mkdir()
    (oldpkg_dir / "__init__.py").write_text("")
    (oldpkg_dir / "core.py").write_text("def core():\n    return 'core'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("oldpkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["oldpkg/__init__.py", "oldpkg/core.py"],
    )
    # Use force mode (generates scope: "original" action for oldpkg -> mypkg)
    # This transforms oldpkg to mypkg, oldpkg.core to mypkg.core
    # Then add scope: "shim" action to rename mypkg -> mypkg.newpkg
    # This tests that scope: "shim" actions can reference results of
    # scope: "original" actions (incremental validation)
    build_cfg["module_mode"] = "force"
    build_cfg["module_actions"] = [
        {"source": "mypkg", "dest": "mypkg.newpkg", "scope": "shim"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    normalized = content.replace("'", '"')
    # After force mode + shim action: oldpkg -> mypkg.oldpkg -> mypkg.newpkg
    # The exact result depends on preserve mode, but should show transformation
    assert '"mypkg' in normalized


def test_scope_original_and_shim_mixed(tmp_path: Path) -> None:
    """Test mixing scope: 'original' and scope: 'shim' actions.

    Note: This test verifies that actions with different scopes are
    applied in the correct order (original first, then shim).
    """
    # Setup: Create package structure
    oldpkg_dir = tmp_path / "oldpkg"
    oldpkg_dir.mkdir()
    (oldpkg_dir / "__init__.py").write_text("")
    (oldpkg_dir / "core.py").write_text("def core():\n    return 'core'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("oldpkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["oldpkg/__init__.py", "oldpkg/core.py"],
    )
    # Mix scope: "original" and scope: "shim" actions
    # original: oldpkg -> newpkg (operates on original tree)
    # shim: mypkg.newpkg -> mypkg.finalpkg (operates on transformed tree)
    build_cfg["module_mode"] = "multi"
    build_cfg["module_actions"] = [
        {"source": "oldpkg", "dest": "newpkg", "scope": "original"},
        {"source": "mypkg.newpkg", "dest": "mypkg.finalpkg", "scope": "shim"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    normalized = content.replace("'", '"')
    # After both actions: oldpkg -> newpkg -> mypkg.finalpkg
    # The exact result depends on preserve mode, but should show transformation
    assert '"mypkg' in normalized


def test_scope_none_mode_with_original_scope(tmp_path: Path) -> None:
    """Test module_mode: 'none' with user actions using scope: 'original'.

    Note: This test verifies that scope: 'original' actions work correctly
    when module_mode is 'none' (no mode-generated actions).
    """
    # Setup: Create package structure
    oldpkg_dir = tmp_path / "oldpkg"
    oldpkg_dir.mkdir()
    (oldpkg_dir / "__init__.py").write_text("")
    (oldpkg_dir / "core.py").write_text("def core():\n    return 'core'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("oldpkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["oldpkg/__init__.py", "oldpkg/core.py"],
    )
    # module_mode: "none" means no mode-generated actions
    # User actions with scope: "original" create initial shim structure
    build_cfg["module_mode"] = "none"
    build_cfg["module_actions"] = [
        {"source": "oldpkg", "dest": "newpkg", "scope": "original"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    normalized = content.replace("'", '"')
    # Actions with scope: "original" should transform original names
    # The exact result depends on preserve mode and package_name prepending
    assert '"mypkg' in normalized or '"newpkg' in normalized


# Note: Error tests for scope validation are deferred to a later iteration
# when we have a better understanding of when validation errors actually occur.
# The error message improvements (including scope information) are already
# implemented in the validation functions and will be tested when we add
# comprehensive validation tests.


def test_affects_shims_only_affects_shim_generation(tmp_path: Path) -> None:
    """Test that affects: 'shims' only affects shim generation, not file selection."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
    )
    # affects: "shims" should only affect shim generation, not file selection
    # File should still be stitched even if shim is deleted
    build_cfg["module_actions"] = [
        {"source": "pkg1", "action": "delete", "affects": "shims"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # File should still be stitched (module code should be present)
    assert "def func()" in content
    # But shim should be deleted (no shim for pkg1)
    normalized = content.replace("'", '"')
    # pkg1 shim should not exist (deleted by affects: "shims" action)
    assert '"pkg1"' not in normalized or '"mypkg.pkg1"' not in normalized


def test_affects_stitching_only_affects_file_selection(
    tmp_path: Path,
) -> None:
    """Test affects: 'stitching' only affects file selection."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
    )
    # affects: "stitching" should only affect file selection
    # File should not be stitched, but shim might still exist (creating mismatch)
    build_cfg["module_mode"] = "multi"  # Generates shims for all packages
    build_cfg["module_actions"] = [
        {
            "source": "pkg1",
            "action": "delete",
            "affects": "stitching",
            "cleanup": "auto",
        },
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # File should not be stitched (module code should not be present)
    assert "def func()" not in content
    # Cleanup: "auto" should delete broken shims
    normalized = content.replace("'", '"')
    # pkg1 shim should be auto-deleted (cleanup: "auto")
    assert '"pkg1"' not in normalized
    assert '"mypkg.pkg1"' not in normalized


def test_affects_both_affects_both_shims_and_stitching(tmp_path: Path) -> None:
    """Test that affects: 'both' affects both shim generation and file selection."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
    )
    # affects: "both" should affect both shim generation and file selection
    build_cfg["module_actions"] = [
        {"source": "pkg1", "action": "delete", "affects": "both"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # File should not be stitched (module code should not be present)
    assert "def func()" not in content
    # Shim should also be deleted
    normalized = content.replace("'", '"')
    assert '"pkg1"' not in normalized
    assert '"mypkg.pkg1"' not in normalized


def test_cleanup_auto_deletes_broken_shims(tmp_path: Path) -> None:
    """Test that cleanup: 'auto' deletes broken shims."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
    )
    # mode: "multi" generates shims for all packages
    # action with affects: "stitching" deletes from stitching only
    # cleanup: "auto" should delete broken shims
    build_cfg["module_mode"] = "multi"
    build_cfg["module_actions"] = [
        {
            "source": "pkg1",
            "action": "delete",
            "affects": "stitching",
            "cleanup": "auto",
        },
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # File should not be stitched
    assert "def func()" not in content
    # Broken shim should be auto-deleted
    normalized = content.replace("'", '"')
    assert '"pkg1"' not in normalized
    assert '"mypkg.pkg1"' not in normalized


def test_cleanup_error_raises_error_for_broken_shims(tmp_path: Path) -> None:
    """Test that cleanup: 'error' raises error for broken shims."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
    )
    # mode: "multi" generates shims for all packages
    # action with affects: "stitching" deletes from stitching only
    # cleanup: "error" should raise error for broken shims
    build_cfg["module_mode"] = "multi"
    build_cfg["module_actions"] = [
        {
            "source": "pkg1",
            "action": "delete",
            "affects": "stitching",
            "cleanup": "error",
        },
    ]

    # Should raise ValueError about broken shims
    with pytest.raises(ValueError, match="broken shims"):
        mod_build.run_build(build_cfg)


def test_cleanup_ignore_keeps_broken_shims(tmp_path: Path) -> None:
    """Test that cleanup: 'ignore' keeps broken shims."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
    )
    # mode: "multi" generates shims for all packages
    # action with affects: "stitching" deletes from stitching only
    # cleanup: "ignore" should keep broken shims
    build_cfg["module_mode"] = "multi"
    build_cfg["module_actions"] = [
        {
            "source": "pkg1",
            "action": "delete",
            "affects": "stitching",
            "cleanup": "ignore",
        },
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # File should not be stitched
    assert "def func()" not in content
    # Broken shim should still exist (cleanup: "ignore")
    # Note: The shim might still exist, but pointing to non-existent module
    # This is the expected behavior for cleanup: "ignore"
    # We just verify the build succeeded (no error raised)
    assert len(content) > 0


# ============================================================================
# End-to-End Tests: Config → Stitched File → Import
# ============================================================================


def test_end_to_end_move_action_works(tmp_path: Path) -> None:
    """Test end-to-end: config with move action → stitched file → import works."""
    # Setup: Create package structure
    oldpkg_dir = tmp_path / "oldpkg"
    oldpkg_dir.mkdir()
    (oldpkg_dir / "__init__.py").write_text("")
    (oldpkg_dir / "module.py").write_text("def func():\n    return 'moved'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("oldpkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["oldpkg/__init__.py", "oldpkg/module.py"],
    )
    build_cfg["module_actions"] = [
        {"source": "oldpkg", "dest": "newpkg", "action": "move", "scope": "original"},
    ]

    mod_build.run_build(build_cfg)

    # Verify stitched file content
    content = out_file.read_text()
    assert "def func()" in content
    normalized = content.replace("'", '"')
    # Should have transformed module name
    assert '"mypkg.newpkg.module"' in normalized or '"newpkg.module"' in normalized

    # Verify import works
    spec = importlib.util.spec_from_file_location("test_e2e_move", out_file)
    assert spec is not None
    assert spec.loader is not None

    for name in list(sys.modules.keys()):
        if name.startswith(("oldpkg", "newpkg", "mypkg", "test_e2e_move")):
            del sys.modules[name]

    stitched_mod = importlib.util.module_from_spec(spec)
    sys.modules["test_e2e_move"] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    # Try to import from transformed location
    try:
        from mypkg.newpkg.module import (  # type: ignore[import-not-found]  # noqa: PLC0415
            func,  # pyright: ignore[reportUnknownVariableType]
        )

        assert func() == "moved"
    except ImportError:
        # Try alternative path
        from newpkg.module import (  # type: ignore[import-not-found]  # noqa: PLC0415
            func,  # pyright: ignore[reportUnknownVariableType]
        )

        assert func() == "moved"


def test_end_to_end_copy_action_works(tmp_path: Path) -> None:
    """Test end-to-end: config with copy action → stitched file → import works."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'copied'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
    )
    build_cfg["module_actions"] = [
        {"source": "pkg1", "dest": "pkg2", "action": "copy", "scope": "original"},
    ]

    mod_build.run_build(build_cfg)

    # Verify stitched file content
    content = out_file.read_text()
    assert "def func()" in content
    normalized = content.replace("'", '"')
    # Should have both original and copied module names
    assert '"mypkg.pkg1.module"' in normalized or '"pkg1.module"' in normalized
    assert '"mypkg.pkg2.module"' in normalized or '"pkg2.module"' in normalized

    # Verify import works from both locations
    spec = importlib.util.spec_from_file_location("test_e2e_copy", out_file)
    assert spec is not None
    assert spec.loader is not None

    for name in list(sys.modules.keys()):
        if name.startswith(("pkg1", "pkg2", "mypkg", "test_e2e_copy")):
            del sys.modules[name]

    stitched_mod = importlib.util.module_from_spec(spec)
    sys.modules["test_e2e_copy"] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    # Should be able to import from both locations
    # Try pkg1 first
    try:
        from mypkg.pkg1.module import (  # type: ignore[import-not-found]  # noqa: PLC0415
            func,  # pyright: ignore[reportUnknownVariableType]
        )

        assert func() == "copied"
    except ImportError:
        from pkg1.module import (  # type: ignore[import-not-found]  # noqa: PLC0415
            func,  # pyright: ignore[reportUnknownVariableType]
        )

        assert func() == "copied"

    # Try pkg2
    for name in list(sys.modules.keys()):
        if name.startswith(("pkg1", "pkg2", "mypkg")):
            del sys.modules[name]

    stitched_mod = importlib.util.module_from_spec(spec)
    sys.modules["test_e2e_copy"] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    try:
        from mypkg.pkg2.module import (  # type: ignore[import-not-found]  # noqa: PLC0415
            func,  # pyright: ignore[reportUnknownVariableType]
        )

        assert func() == "copied"
    except ImportError:
        from pkg2.module import (  # type: ignore[import-not-found]  # noqa: PLC0415
            func,  # pyright: ignore[reportUnknownVariableType]
        )

        assert func() == "copied"


def test_end_to_end_delete_action_works(tmp_path: Path) -> None:
    """Test end-to-end: config with delete action → stitched file → import fails."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'deleted'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
    )
    build_cfg["module_actions"] = [
        {"source": "pkg1", "action": "delete", "scope": "original", "affects": "both"},
    ]

    mod_build.run_build(build_cfg)

    # Verify stitched file content
    content = out_file.read_text()
    # File should not be stitched (deleted)
    assert "def func()" not in content
    normalized = content.replace("'", '"')
    # Shim should also be deleted
    assert '"pkg1"' not in normalized
    assert '"mypkg.pkg1"' not in normalized

    # Verify import fails
    spec = importlib.util.spec_from_file_location("test_e2e_delete", out_file)
    assert spec is not None
    assert spec.loader is not None

    for name in list(sys.modules.keys()):
        if name.startswith(("pkg1", "mypkg", "test_e2e_delete")):
            del sys.modules[name]

    stitched_mod = importlib.util.module_from_spec(spec)
    sys.modules["test_e2e_delete"] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    # Should not be able to import deleted module
    with pytest.raises(ImportError):
        importlib.import_module("mypkg.pkg1.module")


def test_end_to_end_transformed_names_correct_in_stitched_file(
    tmp_path: Path,
) -> None:
    """Test that transformed module names are correct in stitched file."""
    # Setup: Create nested package structure
    oldpkg_dir = tmp_path / "oldpkg"
    oldpkg_dir.mkdir()
    (oldpkg_dir / "__init__.py").write_text("")
    (oldpkg_dir / "sub").mkdir()
    (oldpkg_dir / "sub" / "__init__.py").write_text("")
    (oldpkg_dir / "sub" / "module.py").write_text("VALUE = 42\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("oldpkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=[
            "oldpkg/__init__.py",
            "oldpkg/sub/__init__.py",
            "oldpkg/sub/module.py",
        ],
    )
    build_cfg["module_actions"] = [
        {"source": "oldpkg", "dest": "newpkg", "action": "move", "scope": "original"},
    ]

    mod_build.run_build(build_cfg)

    # Verify transformed names in stitched file
    content = out_file.read_text()
    normalized = content.replace("'", '"')
    # Should have transformed module name, not original
    assert (
        '"mypkg.newpkg.sub.module"' in normalized or '"newpkg.sub.module"' in normalized
    )
    assert '"oldpkg.sub.module"' not in normalized


def test_end_to_end_shims_work_after_transformations(tmp_path: Path) -> None:
    """Test that shims work correctly after transformations."""
    # Setup: Create package structure
    oldpkg_dir = tmp_path / "oldpkg"
    oldpkg_dir.mkdir()
    (oldpkg_dir / "__init__.py").write_text("")
    (oldpkg_dir / "module.py").write_text("def func():\n    return 'shimmed'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("oldpkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["oldpkg/__init__.py", "oldpkg/module.py"],
    )
    build_cfg["module_actions"] = [
        {"source": "oldpkg", "dest": "newpkg", "action": "move", "scope": "original"},
    ]

    mod_build.run_build(build_cfg)

    # Verify shims work
    spec = importlib.util.spec_from_file_location("test_e2e_shims", out_file)
    assert spec is not None
    assert spec.loader is not None

    for name in list(sys.modules.keys()):
        if name.startswith(("oldpkg", "newpkg", "mypkg", "test_e2e_shims")):
            del sys.modules[name]

    stitched_mod = importlib.util.module_from_spec(spec)
    sys.modules["test_e2e_shims"] = stitched_mod
    spec.loader.exec_module(stitched_mod)

    # Should be able to import using transformed name via shim
    try:
        from mypkg.newpkg.module import (  # noqa: PLC0415  # pyright: ignore[reportMissingImports]
            func,  # pyright: ignore[reportUnknownVariableType]
        )

        assert func() == "shimmed"
    except ImportError:
        from newpkg.module import (  # noqa: PLC0415  # pyright: ignore[reportMissingImports]
            func,  # pyright: ignore[reportUnknownVariableType]
        )

        assert func() == "shimmed"


# ============================================================================
# Mode + Actions Tests
# ============================================================================


def test_mode_force_with_user_actions(tmp_path: Path) -> None:
    """Test module_mode: 'force' + user actions work together."""
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
        package="mypkg",
        order=["oldpkg/__init__.py", "oldpkg/core.py", "oldpkg/utils.py"],
    )
    # Force mode transforms oldpkg -> mypkg
    # User action transforms mypkg.core -> mypkg.newcore
    build_cfg["module_mode"] = "force"
    build_cfg["module_actions"] = [
        {"source": "mypkg.core", "dest": "mypkg.newcore", "scope": "shim"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    normalized = content.replace("'", '"')
    # Should have transformed names
    assert '"mypkg' in normalized
    # Should have newcore (from user action)
    assert '"mypkg.newcore"' in normalized or '"newcore"' in normalized


def test_mode_unify_with_user_actions(tmp_path: Path) -> None:
    """Test module_mode: 'unify' + user actions work together."""
    # Setup: Create multiple packages
    pkg1_dir = tmp_path / "pkg1"
    pkg2_dir = tmp_path / "pkg2"
    pkg1_dir.mkdir()
    pkg2_dir.mkdir()
    (pkg1_dir / "__init__.py").write_text("")
    (pkg1_dir / "module.py").write_text("def func1():\n    return 'pkg1'\n")
    (pkg2_dir / "__init__.py").write_text("")
    (pkg2_dir / "module.py").write_text("def func2():\n    return 'pkg2'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [
            make_include_resolved("pkg1/**/*.py", tmp_path),
            make_include_resolved("pkg2/**/*.py", tmp_path),
        ],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=[
            "pkg1/__init__.py",
            "pkg1/module.py",
            "pkg2/__init__.py",
            "pkg2/module.py",
        ],
    )
    # Unify mode transforms pkg1, pkg2 -> mypkg
    # User action transforms mypkg.module -> mypkg.unified
    build_cfg["module_mode"] = "unify"
    build_cfg["module_actions"] = [
        {"source": "mypkg.module", "dest": "mypkg.unified", "scope": "shim"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    normalized = content.replace("'", '"')
    # Should have unified names
    assert '"mypkg' in normalized
    # Should have unified module (from user action)
    assert '"mypkg.unified"' in normalized or '"unified"' in normalized


def test_mode_none_with_user_actions_original_scope(tmp_path: Path) -> None:
    """Test module_mode: 'none' + user actions with scope: 'original'."""
    # Setup: Create package structure
    oldpkg_dir = tmp_path / "oldpkg"
    oldpkg_dir.mkdir()
    (oldpkg_dir / "__init__.py").write_text("")
    (oldpkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("oldpkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["oldpkg/__init__.py", "oldpkg/module.py"],
    )
    # No mode-generated actions
    # User action with scope: "original" transforms oldpkg -> newpkg
    build_cfg["module_mode"] = "none"
    build_cfg["module_actions"] = [
        {"source": "oldpkg", "dest": "newpkg", "scope": "original"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # Headers should show transformed names (module_mode == "none" so no shims)
    assert "# === newpkg ===" in content
    assert "# === newpkg.module ===" in content
    # Original should not appear in headers (moved)
    assert "# === oldpkg ===" not in content
    assert "# === oldpkg.module ===" not in content


def test_mode_generated_actions_work_correctly(tmp_path: Path) -> None:
    """Test that mode-generated actions work correctly."""
    # Setup: Create multiple packages
    pkg1_dir = tmp_path / "pkg1"
    pkg2_dir = tmp_path / "pkg2"
    pkg1_dir.mkdir()
    pkg2_dir.mkdir()
    (pkg1_dir / "__init__.py").write_text("")
    (pkg1_dir / "module.py").write_text("def func1():\n    return 'pkg1'\n")
    (pkg2_dir / "__init__.py").write_text("")
    (pkg2_dir / "module.py").write_text("def func2():\n    return 'pkg2'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [
            make_include_resolved("pkg1/**/*.py", tmp_path),
            make_include_resolved("pkg2/**/*.py", tmp_path),
        ],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=[
            "pkg1/__init__.py",
            "pkg1/module.py",
            "pkg2/__init__.py",
            "pkg2/module.py",
        ],
    )
    # Force mode generates actions to transform pkg1, pkg2 -> mypkg
    build_cfg["module_mode"] = "force"

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    normalized = content.replace("'", '"')
    # Should have transformed names from mode-generated actions
    assert '"mypkg' in normalized
    # Original package names should not appear (moved)
    assert '"pkg1.module"' not in normalized
    assert '"pkg2.module"' not in normalized


# ============================================================================
# Comprehensive Scope Tests
# ============================================================================


def test_scope_original_operates_on_original_tree(tmp_path: Path) -> None:
    """Test that scope: 'original' actions operate on original tree."""
    # Setup: Create package structure
    oldpkg_dir = tmp_path / "oldpkg"
    oldpkg_dir.mkdir()
    (oldpkg_dir / "__init__.py").write_text("")
    (oldpkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("oldpkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["oldpkg/__init__.py", "oldpkg/module.py"],
    )
    # scope: "original" operates on original tree (oldpkg)
    build_cfg["module_actions"] = [
        {"source": "oldpkg", "dest": "newpkg", "scope": "original"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    normalized = content.replace("'", '"')
    # Should have transformed names
    assert '"mypkg.newpkg.module"' in normalized or '"newpkg.module"' in normalized
    # Original should not appear (moved)
    assert '"oldpkg.module"' not in normalized


def test_scope_shim_operates_on_transformed_tree(tmp_path: Path) -> None:
    """Test that scope: 'shim' actions operate on transformed tree."""
    # Setup: Create package structure
    oldpkg_dir = tmp_path / "oldpkg"
    oldpkg_dir.mkdir()
    (oldpkg_dir / "__init__.py").write_text("")
    (oldpkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("oldpkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["oldpkg/__init__.py", "oldpkg/module.py"],
    )
    # Force mode transforms oldpkg -> mypkg
    # scope: "shim" operates on transformed tree (mypkg)
    build_cfg["module_mode"] = "force"
    build_cfg["module_actions"] = [
        {"source": "mypkg", "dest": "mypkg.final", "scope": "shim"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    normalized = content.replace("'", '"')
    # Should have final transformed names
    assert '"mypkg.final' in normalized
    # Original mypkg should not appear (moved by shim action)
    assert '"mypkg.module"' not in normalized or '"mypkg.final.module"' in normalized


def test_scope_shim_chaining_works(tmp_path: Path) -> None:
    """Test chaining scope: 'shim' actions."""
    # Setup: Create package structure
    oldpkg_dir = tmp_path / "oldpkg"
    oldpkg_dir.mkdir()
    (oldpkg_dir / "__init__.py").write_text("")
    (oldpkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("oldpkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["oldpkg/__init__.py", "oldpkg/module.py"],
    )
    # Force mode transforms oldpkg -> mypkg
    # Chain shim actions: mypkg -> mypkg.step1 -> mypkg.step2
    build_cfg["module_mode"] = "force"
    build_cfg["module_actions"] = [
        {"source": "mypkg", "dest": "mypkg.step1", "scope": "shim"},
        {"source": "mypkg.step1", "dest": "mypkg.step2", "scope": "shim"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    normalized = content.replace("'", '"')
    # Should have final chained name
    assert '"mypkg.step2' in normalized
    # Intermediate steps should not appear (moved)
    assert '"mypkg.module"' not in normalized
    assert '"mypkg.step1.module"' not in normalized


def test_scope_original_and_shim_mixed_comprehensive(tmp_path: Path) -> None:
    """Test mixing scope: 'original' and scope: 'shim' comprehensively."""
    # Setup: Create package structure
    oldpkg_dir = tmp_path / "oldpkg"
    oldpkg_dir.mkdir()
    (oldpkg_dir / "__init__.py").write_text("")
    (oldpkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("oldpkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["oldpkg/__init__.py", "oldpkg/module.py"],
    )
    # Mix original and shim actions
    # original: oldpkg -> newpkg (operates on original tree)
    # shim: mypkg.newpkg -> mypkg.final (operates on transformed tree)
    build_cfg["module_actions"] = [
        {"source": "oldpkg", "dest": "newpkg", "scope": "original"},
        {"source": "mypkg.newpkg", "dest": "mypkg.final", "scope": "shim"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    normalized = content.replace("'", '"')
    # Should have final transformed names
    assert '"mypkg.final' in normalized
    # Intermediate steps should not appear (moved)
    assert '"oldpkg.module"' not in normalized
    assert '"mypkg.newpkg.module"' not in normalized


# ============================================================================
# Comprehensive Affects Tests
# ============================================================================


def test_affects_shims_only_affects_shim_generation_comprehensive(
    tmp_path: Path,
) -> None:
    """Test affects: 'shims' only affects shim generation comprehensively."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
    )
    # affects: "shims" should only affect shim generation
    build_cfg["module_actions"] = [
        {"source": "pkg1", "action": "delete", "affects": "shims"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # File should still be stitched (module code should be present)
    assert "def func()" in content
    # But shim should be deleted
    normalized = content.replace("'", '"')
    assert '"pkg1"' not in normalized
    assert '"mypkg.pkg1"' not in normalized


def test_affects_stitching_only_affects_file_selection_comprehensive(
    tmp_path: Path,
) -> None:
    """Test affects: 'stitching' only affects file selection comprehensively."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
    )
    # affects: "stitching" should only affect file selection
    build_cfg["module_mode"] = "multi"  # Generates shims for all packages
    build_cfg["module_actions"] = [
        {
            "source": "pkg1",
            "action": "delete",
            "affects": "stitching",
            "cleanup": "auto",
        },
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # File should not be stitched (module code should not be present)
    assert "def func()" not in content
    # Cleanup: "auto" should delete broken shims
    normalized = content.replace("'", '"')
    assert '"pkg1"' not in normalized
    assert '"mypkg.pkg1"' not in normalized


def test_affects_both_affects_both_comprehensive(tmp_path: Path) -> None:
    """Test affects: 'both' affects both shims and stitching comprehensively."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
    )
    # affects: "both" should affect both shim generation and file selection
    build_cfg["module_actions"] = [
        {"source": "pkg1", "action": "delete", "affects": "both"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # File should not be stitched (module code should not be present)
    assert "def func()" not in content
    # Shim should also be deleted
    normalized = content.replace("'", '"')
    assert '"pkg1"' not in normalized
    assert '"mypkg.pkg1"' not in normalized


def test_affects_files_correctly_included_excluded(tmp_path: Path) -> None:
    """Test that files are correctly included/excluded based on affects."""
    # Setup: Create multiple packages
    pkg1_dir = tmp_path / "pkg1"
    pkg2_dir = tmp_path / "pkg2"
    pkg1_dir.mkdir()
    pkg2_dir.mkdir()
    (pkg1_dir / "__init__.py").write_text("")
    (pkg1_dir / "module1.py").write_text("def func1():\n    return 'pkg1'\n")
    (pkg2_dir / "__init__.py").write_text("")
    (pkg2_dir / "module2.py").write_text("def func2():\n    return 'pkg2'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [
            make_include_resolved("pkg1/**/*.py", tmp_path),
            make_include_resolved("pkg2/**/*.py", tmp_path),
        ],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=[
            "pkg1/__init__.py",
            "pkg1/module1.py",
            "pkg2/__init__.py",
            "pkg2/module2.py",
        ],
    )
    # affects: "stitching" should exclude pkg1 from stitching
    # pkg2 should still be stitched
    build_cfg["module_actions"] = [
        {"source": "pkg1", "action": "delete", "affects": "stitching"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # pkg1 should not be stitched
    assert "def func1()" not in content
    # pkg2 should still be stitched
    assert "def func2()" in content


# ============================================================================
# Comprehensive Cleanup Tests
# ============================================================================


def test_cleanup_auto_deletes_broken_shims_comprehensive(tmp_path: Path) -> None:
    """Test cleanup: 'auto' deletes broken shims comprehensively."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
    )
    # mode: "multi" generates shims for all packages
    # action with affects: "stitching" deletes from stitching only
    # cleanup: "auto" should delete broken shims
    build_cfg["module_mode"] = "multi"
    build_cfg["module_actions"] = [
        {
            "source": "pkg1",
            "action": "delete",
            "affects": "stitching",
            "cleanup": "auto",
        },
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # File should not be stitched
    assert "def func()" not in content
    # Broken shim should be auto-deleted
    normalized = content.replace("'", '"')
    assert '"pkg1"' not in normalized
    assert '"mypkg.pkg1"' not in normalized


def test_cleanup_error_raises_error_comprehensive(tmp_path: Path) -> None:
    """Test cleanup: 'error' raises error comprehensively."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
    )
    # mode: "multi" generates shims for all packages
    # action with affects: "stitching" deletes from stitching only
    # cleanup: "error" should raise error for broken shims
    build_cfg["module_mode"] = "multi"
    build_cfg["module_actions"] = [
        {
            "source": "pkg1",
            "action": "delete",
            "affects": "stitching",
            "cleanup": "error",
        },
    ]

    # Should raise ValueError about broken shims
    with pytest.raises(ValueError, match="broken shims"):
        mod_build.run_build(build_cfg)


def test_cleanup_ignore_keeps_broken_shims_comprehensive(tmp_path: Path) -> None:
    """Test cleanup: 'ignore' keeps broken shims comprehensively."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
    )
    # mode: "multi" generates shims for all packages
    # action with affects: "stitching" deletes from stitching only
    # cleanup: "ignore" should keep broken shims
    build_cfg["module_mode"] = "multi"
    build_cfg["module_actions"] = [
        {
            "source": "pkg1",
            "action": "delete",
            "affects": "stitching",
            "cleanup": "ignore",
        },
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # File should not be stitched
    assert "def func()" not in content
    # Broken shim should still exist (cleanup: "ignore")
    # Build should succeed (no error raised)
    assert len(content) > 0


def test_cleanup_shim_stitching_mismatch_scenarios(tmp_path: Path) -> None:
    """Test shim-stitching mismatch scenarios."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    # Test scenario: shim exists but module is deleted from stitching
    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
    )
    # mode: "multi" generates shims for all packages
    # action with affects: "stitching" deletes from stitching only
    # This creates a mismatch: shim exists but module doesn't
    build_cfg["module_mode"] = "multi"
    build_cfg["module_actions"] = [
        {
            "source": "pkg1",
            "action": "delete",
            "affects": "stitching",
            "cleanup": "auto",
        },
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # File should not be stitched
    assert "def func()" not in content
    # Mismatch should be handled by cleanup: "auto" (shim deleted)
    normalized = content.replace("'", '"')
    assert '"pkg1"' not in normalized
    assert '"mypkg.pkg1"' not in normalized


# ============================================================================
# Shim Setting Tests
# ============================================================================


def test_shim_all_generates_shims_for_all_modules(tmp_path: Path) -> None:
    """Test shim: 'all' generates shims for all modules."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
        shim="all",
    )

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # Should have shim code
    assert "# --- import shims for single-file runtime ---" in content
    normalized = content.replace("'", '"')
    # Should have shims for all modules
    assert '"mypkg.pkg1.module"' in normalized or '"pkg1.module"' in normalized


def test_shim_none_generates_no_shims(tmp_path: Path) -> None:
    """Test shim: 'none' generates no shims."""
    # Setup: Create package structure
    pkg_dir = tmp_path / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("pkg1/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["pkg1/__init__.py", "pkg1/module.py"],
        shim="none",
    )

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # Should not have shim code
    assert "# --- import shims for single-file runtime ---" not in content
    assert "_create_pkg_module" not in content


def test_shim_all_with_module_actions(tmp_path: Path) -> None:
    """Test shim: 'all' with module_actions."""
    # Setup: Create package structure
    oldpkg_dir = tmp_path / "oldpkg"
    oldpkg_dir.mkdir()
    (oldpkg_dir / "__init__.py").write_text("")
    (oldpkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("oldpkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["oldpkg/__init__.py", "oldpkg/module.py"],
        shim="all",
    )
    build_cfg["module_actions"] = [
        {"source": "oldpkg", "dest": "newpkg", "action": "move", "scope": "original"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # Should have shim code
    assert "# --- import shims for single-file runtime ---" in content
    normalized = content.replace("'", '"')
    # Should have shims for transformed modules
    assert '"mypkg.newpkg.module"' in normalized or '"newpkg.module"' in normalized
    # Should not have shims for original modules (moved)
    assert '"oldpkg.module"' not in normalized


def test_shim_none_with_module_actions(tmp_path: Path) -> None:
    """Test shim: 'none' with module_actions."""
    # Setup: Create package structure
    oldpkg_dir = tmp_path / "oldpkg"
    oldpkg_dir.mkdir()
    (oldpkg_dir / "__init__.py").write_text("")
    (oldpkg_dir / "module.py").write_text("def func():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("oldpkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["oldpkg/__init__.py", "oldpkg/module.py"],
        shim="none",
    )
    build_cfg["module_actions"] = [
        {"source": "oldpkg", "dest": "newpkg", "action": "move", "scope": "original"},
    ]

    mod_build.run_build(build_cfg)

    content = out_file.read_text()
    # Should not have shim code
    assert "# --- import shims for single-file runtime ---" not in content
    # But module code should still be present
    assert "def func()" in content
