# tests/95_integration_output/test_standalone__contents.py
"""Verify that the standalone standalone version (`bin/script.py`)
was generated correctly — includes metadata, license header,
and matches the declared version from pyproject.toml.
"""

import re
import sys
from typing import Any, cast

from tests.utils import PROJ_ROOT, is_ci


if sys.version_info >= (3, 11):
    # tomllib has no type stubs
    import tomllib  # type: ignore[import-not-found]
else:
    # tomli (fallback for Python <3.11); also has no type stubs
    import tomli as tomllib  # type: ignore[import-not-found,unused-ignore]

import serger.meta as mod_meta


# --- only for singlefile runs ---
__runtime_mode__ = "singlefile"


def test_standalone_script_metadata_and_execution() -> None:  # noqa: PLR0912, PLR0915
    """Ensure the generated script.py script is complete and functional."""
    # --- setup ---
    script = PROJ_ROOT / "dist" / f"{mod_meta.PROGRAM_SCRIPT}.py"
    pyproject = PROJ_ROOT / "pyproject.toml"

    # --- execute and verify ---

    # - Basic existence checks -
    assert script.exists(), (
        "Standalone script not found — run `poetry run poe build:single` first."
    )
    assert pyproject.exists(), "pyproject.toml missing — project layout inconsistent."

    # - Load declared version from pyproject.toml -
    with pyproject.open("rb") as f:
        # tomllib/tomli lack type stubs; cast and ignore unknown member types
        pyproject_data = cast(  # type: ignore[redundant-cast,unused-ignore]
            "dict[str, Any]",
            tomllib.load(f),  # pyright: ignore[reportUnknownMemberType]
        )

    project_section = cast("dict[str, Any]", pyproject_data.get("project", {}))
    declared_version = cast("str", project_section.get("version"))
    assert declared_version, "Version not found in pyproject.toml"

    # - Read standalone script text -
    # Debug: log script path and metadata in CI
    if is_ci():
        print(f"\n[DEBUG] Script path: {script}")
        print(f"[DEBUG] Script exists: {script.exists()}")
        if script.exists():
            script_text_full = script.read_text(encoding="utf-8")
            script_lines = script_text_full.split("\n")
            print(
                f"[DEBUG] Script size: {len(script_text_full)} chars, "
                f"{len(script_lines)} lines"
            )

            # Show first 30 lines
            print("[DEBUG] First 30 lines of script:")
            for i, line in enumerate(script_lines[:30], 1):
                print(f"  {i:3d}: {line}")

            # Find all commit-related lines
            commit_lines_with_nums = [
                (i, line)
                for i, line in enumerate(script_lines, 1)
                if "commit" in line.lower()
            ]
            num_commit_lines = len(commit_lines_with_nums)
            print(f"[DEBUG] Found {num_commit_lines} lines containing 'commit':")
            for line_num, line_content in commit_lines_with_nums[:10]:  # Show first 10
                print(f"  Line {line_num:4d}: {line_content}")

            # Extract metadata constants
            version_const = re.search(
                r'__version__\s*=\s*["\']([^"\']+)["\']', script_text_full
            )
            commit_const = re.search(
                r'__commit__\s*=\s*["\']([^"\']+)["\']', script_text_full
            )
            build_date_const = re.search(
                r'__build_date__\s*=\s*["\']([^"\']+)["\']', script_text_full
            )

            print("[DEBUG] Python constants found:")
            if version_const:
                print(f"  __version__ = {version_const.group(1)}")
            else:
                print("  __version__ = NOT FOUND")
            if commit_const:
                print(f"  __commit__ = {commit_const.group(1)}")
            else:
                print("  __commit__ = NOT FOUND")
            if build_date_const:
                print(f"  __build_date__ = {build_date_const.group(1)}")
            else:
                print("  __build_date__ = NOT FOUND")

            # Extract header metadata
            header_version = re.search(
                r"^# Version:\s*([^\n]+)", script_text_full, re.MULTILINE
            )
            header_commit = re.search(
                r"^# Commit:\s*([^\n]+)", script_text_full, re.MULTILINE
            )
            header_build_date = re.search(
                r"^# Build Date:\s*([^\n]+)", script_text_full, re.MULTILINE
            )

            print("[DEBUG] Header comments found:")
            if header_version:
                print(f"  # Version: {header_version.group(1)}")
            else:
                print("  # Version: NOT FOUND")
            if header_commit:
                print(f"  # Commit: {header_commit.group(1)}")
            else:
                print("  # Commit: NOT FOUND")
            if header_build_date:
                print(f"  # Build Date: {header_build_date.group(1)}")
            else:
                print("  # Build Date: NOT FOUND")

            print()  # Blank line for readability

    text = script.read_text(encoding="utf-8").lower()

    # - Metadata presence checks -
    assert ("# " + mod_meta.PROGRAM_DISPLAY).lower() in text
    assert "License: MIT-aNOAI".lower() in text
    assert "Version:".lower() in text
    assert "Repo:".lower() in text
    assert "auto-generated".lower() in text

    # - Version and commit format checks -
    version_match = re.search(
        r"^# Version:\s*([\w.\-]+)", text, re.MULTILINE | re.IGNORECASE
    )

    if is_ci():
        commit_match = re.search(
            r"^# Commit:\s*([0-9a-f]{4,})", text, re.MULTILINE | re.IGNORECASE
        )
        # Debug: show what commit lines exist
        if not commit_match:
            commit_lines = [
                line
                for line in text.split("\n")
                if "commit" in line.lower() and line.strip().startswith("#")
            ]
            print(
                "[DEBUG] Commit match failed. "
                "Searching for pattern: ^# Commit:\\s*([0-9a-f]{4,})"
            )
            print(f"[DEBUG] Found {len(commit_lines)} commit-related comment lines:")
            for i, line in enumerate(commit_lines[:10], 1):
                print(f"  {i}: {line}")
            msg = f"Missing commit stamp. Found commit lines: {commit_lines[:5]}"
            raise AssertionError(msg)
        print(f"[DEBUG] Commit match successful: {commit_match.group(1)}")
    else:
        commit_match = re.search(
            r"^# Commit:\s*unknown \(local build\)",
            text,
            re.MULTILINE | re.IGNORECASE,
        )

    assert version_match, "Missing version stamp"
    assert commit_match, "Missing commit stamp"

    standalone_version = version_match.group(1)
    assert standalone_version.lower() == declared_version.lower(), (
        f"Standalone version '{standalone_version}'"
        f" != pyproject version '{declared_version}'"
    )


def test_standalone_script_has_python_constants_and_parses_them() -> None:
    """Ensure __version__ and __commit__ constants exist and match header."""
    # --- setup ---
    script = PROJ_ROOT / "dist" / f"{mod_meta.PROGRAM_SCRIPT}.py"

    # --- execute ---
    text = script.read_text(encoding="utf-8")

    # --- verify ---
    # Check constants exist
    version_const = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", text)
    commit_const = re.search(r"__commit__\s*=\s*['\"]([^'\"]+)['\"]", text)
    assert version_const, "Missing __version__ constant"
    assert commit_const, "Missing __commit__ constant"

    # Check they match header comments
    header_version = re.search(r"^# Version:\s*([\w.\-]+)", text, re.MULTILINE)
    header_commit = re.search(r"^# Commit:\s*(.+)$", text, re.MULTILINE)
    assert header_version, "Missing # Version header"
    assert header_commit, "Missing # Commit header"

    assert version_const.group(1) == header_version.group(1)
    assert commit_const.group(1) == header_commit.group(1)
