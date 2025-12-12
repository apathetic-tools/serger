# tests/95_integration_output/test_stitched__contents.py
"""Verify that the stitched version (`dist/serger.py`)
was generated correctly — includes metadata, license header,
and matches the declared version from pyproject.toml.
"""

import re
from typing import Any, cast

import apathetic_utils

import serger.meta as mod_meta
from tests.utils import PROJ_ROOT


# --- only for stitched runs ---
__runtime_mode__ = "stitched"


def test_stitched_script_metadata_and_execution() -> None:
    """Ensure the generated stitched script is complete and functional."""
    # --- setup ---
    script = PROJ_ROOT / "dist" / f"{mod_meta.PROGRAM_SCRIPT}.py"
    pyproject = PROJ_ROOT / "pyproject.toml"

    # --- execute and verify ---

    # - Basic existence checks -
    assert script.exists(), (
        "Stitched script not found — run `poetry run poe build:script` first."
    )
    assert pyproject.exists(), "pyproject.toml missing — project layout inconsistent."

    # - Load declared version from pyproject.toml -
    pyproject_data = apathetic_utils.load_toml(pyproject, required=True)
    assert pyproject_data is not None
    project_section = cast("dict[str, Any]", pyproject_data.get("project", {}))
    declared_version = cast("str", project_section.get("version"))
    assert declared_version, "Version not found in pyproject.toml"

    # - Read stitched script text -
    text = script.read_text(encoding="utf-8").lower()

    # - Metadata presence checks -
    assert ("# " + mod_meta.PROGRAM_DISPLAY).lower() in text
    assert "License: MIT-a-NOAI".lower() in text
    assert "Version:".lower() in text
    assert "Repo:".lower() in text
    assert "auto-generated".lower() in text

    # - Version and commit format checks -
    version_match = re.search(
        r"^# Version:\s*([\w.\-]+)", text, re.MULTILINE | re.IGNORECASE
    )

    if apathetic_utils.is_ci():
        commit_match = re.search(
            r"^# Commit:\s*([0-9a-f]{4,})", text, re.MULTILINE | re.IGNORECASE
        )
        if not commit_match:
            commit_lines = [
                line
                for line in text.split("\n")
                if "commit" in line.lower() and line.strip().startswith("#")
            ]
            msg = f"Missing commit stamp. Found commit lines: {commit_lines[:5]}"
            raise AssertionError(msg)
    else:
        commit_match = re.search(
            r"^# Commit:\s*unknown \(local build\)",
            text,
            re.MULTILINE | re.IGNORECASE,
        )

    assert version_match, "Missing version stamp"
    assert commit_match, "Missing commit stamp"

    stitched_version = version_match.group(1)
    assert stitched_version.lower() == declared_version.lower(), (
        f"Stitched version '{stitched_version}'"
        f" != pyproject version '{declared_version}'"
    )


def test_stitched_script_has_python_constants_and_parses_them() -> None:
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
