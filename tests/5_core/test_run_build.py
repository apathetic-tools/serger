# tests/5_core/test_run_build.py
"""Tests for run_build() stitch build functionality.

Serger now only handles stitch builds (combining Python modules into
a single executable script). File copying is handled by pocket-build.
"""

import re
from pathlib import Path
from typing import cast

import serger.build as mod_build
import serger.logs as mod_logs
from tests.utils import make_build_cfg, make_include_resolved


def test_run_build_stitch_simple_modules(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Should stitch simple Python modules into a single file."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "base.py").write_text("BASE = 1\n")
    (src / "main.py").write_text("from src.base import BASE\n\nMAIN = BASE\n")

    cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("src/*.py", tmp_path)],
    )
    cfg["package"] = "testpkg"
    cfg["order"] = ["src/base.py", "src/main.py"]

    # --- execute ---
    with module_logger.use_level("info"):
        mod_build.run_build(cfg)

    # --- verify ---
    # Output goes to the 'out' path from config
    out_file = tmp_path / "dist" / "script.py"
    assert out_file.exists()
    content = out_file.read_text()
    assert "BASE = 1" in content
    assert "MAIN = BASE" in content


def test_run_build_skips_non_stitch_build(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Should skip builds without package field (file copying)."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "file.txt").write_text("content")

    cfg = make_build_cfg(tmp_path, [make_include_resolved("src", tmp_path)])
    # No package - should be skipped

    # --- execute ---
    with module_logger.use_level("info"):
        mod_build.run_build(cfg)

    # --- verify ---
    # No output file should be created (file copying is pocket-build's job)
    out_file = tmp_path / "dist" / "testpkg.py"
    assert not out_file.exists()


def test_run_build_respects_order_paths(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Should stitch modules in the order specified by order paths."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("A = 1\n")
    (src / "b.py").write_text("B = 2\n")
    (src / "c.py").write_text("C = 3\n")

    cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("src/*.py", tmp_path)],
    )
    cfg["package"] = "testpkg"
    cfg["order"] = ["src/c.py", "src/a.py", "src/b.py"]  # Custom order

    # --- execute ---
    with module_logger.use_level("info"):
        mod_build.run_build(cfg)

    # --- verify ---
    out_file = tmp_path / "dist" / "script.py"
    assert out_file.exists()
    content = out_file.read_text()
    # Check order is preserved (c before a before b)
    c_pos = content.find("C = 3")
    a_pos = content.find("A = 1")
    b_pos = content.find("B = 2")
    assert c_pos < a_pos < b_pos


def test_run_build_handles_multiple_includes(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Should handle multiple include patterns."""
    # --- setup ---
    src1 = tmp_path / "src1"
    src2 = tmp_path / "src2"
    src1.mkdir()
    src2.mkdir()
    (src1 / "a.py").write_text("A = 1\n")
    (src2 / "b.py").write_text("B = 2\n")

    cfg = make_build_cfg(
        tmp_path,
        [
            make_include_resolved("src1/*.py", tmp_path),
            make_include_resolved("src2/*.py", tmp_path),
        ],
    )
    cfg["package"] = "testpkg"
    cfg["order"] = ["src1/a.py", "src2/b.py"]

    # --- execute ---
    with module_logger.use_level("info"):
        mod_build.run_build(cfg)

    # --- verify ---
    out_file = tmp_path / "dist" / "script.py"
    assert out_file.exists()
    content = out_file.read_text()
    assert "A = 1" in content
    assert "B = 2" in content


def test_run_build_respects_excludes(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Should exclude files matching exclude patterns."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("A = 1\n")
    (src / "skip.py").write_text("SKIP = 1\n")
    (src / "b.py").write_text("B = 2\n")

    cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("src/*.py", tmp_path)],
    )
    cfg["package"] = "testpkg"
    cfg["order"] = ["src/a.py", "src/b.py"]  # skip.py not in order
    cfg["exclude_names"] = ["src/skip.py"]  # type: ignore[typeddict-unknown-key]

    # --- execute ---
    with module_logger.use_level("info"):
        mod_build.run_build(cfg)

    # --- verify ---
    out_file = tmp_path / "dist" / "script.py"
    assert out_file.exists()
    content = out_file.read_text()
    assert "A = 1" in content
    assert "B = 2" in content
    assert "SKIP = 1" not in content


def test_run_build_dry_run_skips_stitching(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Dry-run mode should not create output file."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("MAIN = 1\n")

    cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("src/*.py", tmp_path)],
        dry_run=True,
    )
    cfg["package"] = "testpkg"
    cfg["order"] = ["src/main.py"]

    # --- execute ---
    with module_logger.use_level("info"):
        mod_build.run_build(cfg)

    # --- verify ---
    out_file = tmp_path / "dist" / "script.py"
    assert not out_file.exists()


def test_run_build_uses_timestamp_when_no_version(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Should use timestamp as version when no version is found."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("MAIN = 1\n")

    # Create pyproject.toml without version
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("# no version here\n")

    cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("src/*.py", tmp_path)],
    )
    cfg["package"] = "testpkg"
    cfg["order"] = ["src/main.py"]
    # Ensure no version in config (it's added dynamically, so we need to cast)
    cfg_dict = cast("dict[str, object]", cfg)
    if "_pyproject_version" in cfg_dict:
        del cfg_dict["_pyproject_version"]

    # --- execute ---
    with module_logger.use_level("info"):
        mod_build.run_build(cfg)

    # --- verify ---
    out_file = tmp_path / "dist" / "script.py"
    assert out_file.exists()
    content = out_file.read_text()

    # Version should be a timestamp, not "unknown"
    version_match = re.search(r"^# Version:\s*(.+)$", content, re.MULTILINE)
    assert version_match, "Version line not found in output"
    version = version_match.group(1).strip()

    assert version != "unknown", "Version should not be 'unknown'"
    # Should match timestamp format: YYYY-MM-DD HH:MM:SS UTC
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC", version), (
        f"Version should be a timestamp, got: {version}"
    )

    # Verify __version__ constant also has the timestamp
    version_const_match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    assert version_const_match, "__version__ constant not found"
    version_const = version_const_match.group(1)
    assert version_const == version, (
        f"__version__ constant should match header version: "
        f"{version_const} != {version}"
    )


def test_run_build_auto_discovers_order(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Auto-discover module order via topological sort when order is not specified."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    # Create modules with dependencies: base -> derived -> main
    # Use package name "src" to match directory structure for auto-discovery
    (src / "base.py").write_text("BASE = 1\n")
    (src / "derived.py").write_text("from src.base import BASE\n\nDERIVED = BASE + 1\n")
    (src / "main.py").write_text(
        "from src.derived import DERIVED\n\nMAIN = DERIVED + 1\n"
    )

    cfg = make_build_cfg(
        tmp_path,
        [make_include_resolved("src/*.py", tmp_path)],
    )
    cfg["package"] = "src"  # Package name matches directory for auto-discovery
    # No order specified - should auto-discover

    # --- execute ---
    with module_logger.use_level("info"):
        mod_build.run_build(cfg)

    # --- verify ---
    out_file = tmp_path / "dist" / "script.py"
    assert out_file.exists()
    content = out_file.read_text()

    # Verify all modules are included
    assert "BASE = 1" in content
    assert "DERIVED = BASE + 1" in content
    assert "MAIN = DERIVED + 1" in content

    # Verify order is correct (base before derived before main)
    base_pos = content.find("BASE = 1")
    derived_pos = content.find("DERIVED = BASE + 1")
    main_pos = content.find("MAIN = DERIVED + 1")
    assert base_pos < derived_pos < main_pos, (
        "Auto-discovered order should respect dependencies: "
        f"base at {base_pos}, derived at {derived_pos}, main at {main_pos}"
    )
