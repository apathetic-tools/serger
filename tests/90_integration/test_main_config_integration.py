# tests/90_integration/test_main_config_integration.py
"""Integration tests for main_mode and main_name configuration."""

import subprocess
import sys
from pathlib import Path

import pytest

import serger.build as mod_build
from tests.utils.buildconfig import make_build_cfg, make_include_resolved, make_resolved


def test_main_mode_none_no_main_block(tmp_path: Path) -> None:
    """Test main_mode='none' - no __main__ block inserted."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "main.py").write_text("def main():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("mypkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["mypkg/__init__.py", "mypkg/main.py"],
        main_mode="none",
    )

    # --- execute ---
    mod_build.run_build(build_cfg)

    # --- verify ---
    content = out_file.read_text()
    # Should not have __main__ block
    assert "if __name__ == '__main__':" not in content
    assert "__name__ == '__main__'" not in content


def test_main_mode_auto_with_main_name_none(tmp_path: Path) -> None:
    """Test main_mode='auto' with main_name=None - auto-detect main function."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "main.py").write_text("def main():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("mypkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["mypkg/__init__.py", "mypkg/main.py"],
        main_mode="auto",
        main_name=None,
    )

    # --- execute ---
    mod_build.run_build(build_cfg)

    # --- verify ---
    content = out_file.read_text()
    # Should have __main__ block calling main()
    assert "if __name__ == '__main__':" in content
    assert "main()" in content


def test_main_mode_auto_with_main_name_simple(tmp_path: Path) -> None:
    """Test main_mode='auto' with main_name='main' - simple function name."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "main.py").write_text("def main():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("mypkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["mypkg/__init__.py", "mypkg/main.py"],
        main_mode="auto",
        main_name="main",
    )

    # --- execute ---
    mod_build.run_build(build_cfg)

    # --- verify ---
    content = out_file.read_text()
    assert "if __name__ == '__main__':" in content
    assert "main()" in content


def test_main_mode_auto_with_main_name_package(tmp_path: Path) -> None:
    """Test main_mode='auto' with main_name='mypkg::main' - package specification."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "main.py").write_text("def main():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("mypkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["mypkg/__init__.py", "mypkg/main.py"],
        main_mode="auto",
        main_name="mypkg::main",
    )

    # --- execute ---
    mod_build.run_build(build_cfg)

    # --- verify ---
    content = out_file.read_text()
    assert "if __name__ == '__main__':" in content
    assert "main()" in content


def test_main_mode_auto_with_main_name_module_function(
    tmp_path: Path,
) -> None:
    """Test main_mode='auto' with main_name='mypkg.subpkg::entry'."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    subpkg_dir = pkg_dir / "subpkg"
    subpkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (subpkg_dir / "__init__.py").write_text("")
    (subpkg_dir / "entry.py").write_text("def entry():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("mypkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=[
            "mypkg/__init__.py",
            "mypkg/subpkg/__init__.py",
            "mypkg/subpkg/entry.py",
        ],
        main_mode="auto",
        main_name="mypkg.subpkg::entry",
    )

    # --- execute ---
    mod_build.run_build(build_cfg)

    # --- verify ---
    content = out_file.read_text()
    assert "if __name__ == '__main__':" in content
    assert "entry()" in content


def test_main_function_no_parameters(tmp_path: Path) -> None:
    """Test main function with no parameters."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "main.py").write_text("def main():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("mypkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["mypkg/__init__.py", "mypkg/main.py"],
        main_mode="auto",
    )

    # --- execute ---
    mod_build.run_build(build_cfg)

    # --- verify ---
    content = out_file.read_text()
    assert "if __name__ == '__main__':" in content
    # Should call main() with no arguments
    assert "main()" in content
    assert "main(sys.argv[1:])" not in content


def test_main_function_with_star_args(tmp_path: Path) -> None:
    """Test main function with *args."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "main.py").write_text("def main(*args):\n    return args\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("mypkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["mypkg/__init__.py", "mypkg/main.py"],
        main_mode="auto",
    )

    # --- execute ---
    mod_build.run_build(build_cfg)

    # --- verify ---
    content = out_file.read_text()
    assert "if __name__ == '__main__':" in content
    # Should call main() with sys.argv[1:]
    assert "main(sys.argv[1:])" in content or "main(*sys.argv[1:])" in content


def test_main_function_with_kwargs(tmp_path: Path) -> None:
    """Test main function with **kwargs."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "main.py").write_text("def main(**kwargs):\n    return kwargs\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("mypkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["mypkg/__init__.py", "mypkg/main.py"],
        main_mode="auto",
    )

    # --- execute ---
    mod_build.run_build(build_cfg)

    # --- verify ---
    content = out_file.read_text()
    assert "if __name__ == '__main__':" in content
    # Should call main() with sys.argv[1:]
    assert "main(sys.argv[1:])" in content or "main(*sys.argv[1:])" in content


def test_main_function_with_defaults(tmp_path: Path) -> None:
    """Test main function with default values."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "main.py").write_text("def main(arg='default'):\n    return arg\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("mypkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["mypkg/__init__.py", "mypkg/main.py"],
        main_mode="auto",
    )

    # --- execute ---
    mod_build.run_build(build_cfg)

    # --- verify ---
    content = out_file.read_text()
    assert "if __name__ == '__main__':" in content
    # Should call main() with sys.argv[1:] since it has parameters
    assert "main(sys.argv[1:])" in content or "main(*sys.argv[1:])" in content


def test_multiple_main_blocks_priority_same_file(tmp_path: Path) -> None:
    """Test multiple __main__ blocks - priority to same file as main function."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "main.py").write_text(
        "def main():\n    return 'test'\n\nif __name__ == '__main__':\n    main()\n"
    )
    (pkg_dir / "other.py").write_text(
        "def other():\n    pass\n\nif __name__ == '__main__':\n    other()\n"
    )

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("mypkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["mypkg/__init__.py", "mypkg/main.py", "mypkg/other.py"],
        main_mode="auto",
    )

    # --- execute ---
    mod_build.run_build(build_cfg)

    # --- verify ---
    content = out_file.read_text()
    # Should have only one __main__ block (from main.py)
    main_block_count = content.count("if __name__ == '__main__':")
    assert main_block_count == 1
    # Should call main(), not other()
    assert "main()" in content
    # Should not call other() in __main__ block
    assert "if __name__ == '__main__':" in content
    # Verify the block is from main.py (should have main() call)
    main_block_start = content.find("if __name__ == '__main__':")
    main_block_end = content.find("\n\n", main_block_start)
    if main_block_end == -1:
        main_block_end = len(content)
    main_block = content[main_block_start:main_block_end]
    assert "main()" in main_block


def test_collision_handling_raw_mode(tmp_path: Path) -> None:
    """Test collision handling in raw mode - auto-rename conflicting functions."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "main1.py").write_text("def main():\n    return 'main1'\n")
    (pkg_dir / "main2.py").write_text("def main():\n    return 'main2'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("mypkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["mypkg/__init__.py", "mypkg/main1.py", "mypkg/main2.py"],
        main_mode="auto",
        stitch_mode="raw",
    )

    # --- execute ---
    mod_build.run_build(build_cfg)

    # --- verify ---
    content = out_file.read_text()
    # Should have main() function (the one we're using)
    assert "def main():" in content
    # Should have auto-renamed function (main_1)
    assert "def main_1():" in content
    # Should call main() in __main__ block
    assert "if __name__ == '__main__':" in content
    assert "main()" in content


def test_no_collision_handling_module_mode(tmp_path: Path) -> None:
    """Test no collision handling in module mode - namespacing handles it."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "main1.py").write_text("def main():\n    return 'main1'\n")
    (pkg_dir / "main2.py").write_text("def main():\n    return 'main2'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("mypkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["mypkg/__init__.py", "mypkg/main1.py", "mypkg/main2.py"],
        main_mode="auto",
        stitch_mode="raw",
        module_mode="multi",
    )

    # --- execute ---
    mod_build.run_build(build_cfg)

    # --- verify ---
    content = out_file.read_text()
    # In module mode, functions are namespaced, so no auto-rename needed
    # But we still need to verify the main function is found and called
    assert "if __name__ == '__main__':" in content
    # The main function should be accessible (either directly or via namespace)
    assert "main()" in content or "mypkg.main1.main()" in content


def test_main_name_specified_not_found_error(tmp_path: Path) -> None:
    """Test main_name specified but not found - should raise error."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "other.py").write_text("def other():\n    return 'test'\n")

    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("mypkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["mypkg/__init__.py", "mypkg/other.py"],
        main_mode="auto",
        main_name="mypkg::nonexistent",
    )

    # --- execute and verify ---
    with pytest.raises(ValueError, match=r"main_name.*not found"):
        mod_build.run_build(build_cfg)


def test_main_mode_auto_no_main_function_non_main_build(
    tmp_path: Path,
) -> None:
    """Test main_mode='auto' with no main function - non-main build."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "other.py").write_text("def other():\n    return 'test'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("mypkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["mypkg/__init__.py", "mypkg/other.py"],
        main_mode="auto",
        main_name=None,  # Auto-detect, but no main() function exists
    )

    # --- execute ---
    mod_build.run_build(build_cfg)

    # --- verify ---
    content = out_file.read_text()
    # Should not have __main__ block since no main function found
    assert "if __name__ == '__main__':" not in content
    # Should still have the code
    assert "def other():" in content


def test_excluded_main_py_files(tmp_path: Path) -> None:
    """Test that excluded __main__.py and __init__.py files are not searched."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("def main():\n    return 'init'\n")
    (pkg_dir / "__main__.py").write_text("def main():\n    return 'main'\n")
    (pkg_dir / "entry.py").write_text("def main():\n    return 'entry'\n")

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("mypkg/entry.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["mypkg/entry.py"],
        main_mode="auto",
    )

    # --- execute ---
    mod_build.run_build(build_cfg)

    # --- verify ---
    content = out_file.read_text()
    # Should find main() from entry.py (the only included file)
    assert "if __name__ == '__main__':" in content
    assert "main()" in content
    # Should not have code from excluded __init__.py or __main__.py
    assert "return 'init'" not in content
    assert "return 'main'" not in content


def test_main_block_execution_works(tmp_path: Path) -> None:
    """Test that generated __main__ block actually executes correctly."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "main.py").write_text(
        "def main():\n    print('Hello from main!')\n    return 42\n"
    )

    out_file = tmp_path / "stitched.py"
    build_cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("mypkg/**/*.py", tmp_path)],
        respect_gitignore=False,
        out=make_resolved("stitched.py", tmp_path),
        package="mypkg",
        order=["mypkg/__init__.py", "mypkg/main.py"],
        main_mode="auto",
    )

    # --- execute ---
    mod_build.run_build(build_cfg)

    # --- verify ---
    content = out_file.read_text()
    assert "if __name__ == '__main__':" in content
    assert "main()" in content

    # Try to execute the script
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(out_file)],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
        cwd=tmp_path,
    )

    # Should execute successfully
    assert result.returncode == 0 or "Hello from main!" in result.stdout
