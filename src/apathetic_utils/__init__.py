"""Apathetic utilities package."""

from apathetic_utils.ci import CI_ENV_VARS, is_ci
from apathetic_utils.files import load_jsonc, load_toml
from apathetic_utils.matching import fnmatchcase_portable, is_excluded_raw
from apathetic_utils.paths import get_glob_root, has_glob_chars, normalize_path_string
from apathetic_utils.system import (
    CapturedOutput,
    capture_output,
    detect_runtime_mode,
    get_sys_version_info,
    is_running_under_pytest,
)
from apathetic_utils.text import plural, remove_path_in_error_message
from apathetic_utils.types import (
    cast_hint,
    literal_to_set,
    safe_isinstance,
    schema_from_typeddict,
)


__all__ = [  # noqa: RUF022
    # ci
    "CI_ENV_VARS",
    "is_ci",
    # files
    "load_jsonc",
    "load_toml",
    # matching
    "fnmatchcase_portable",
    "is_excluded_raw",
    # paths
    "get_glob_root",
    "has_glob_chars",
    "normalize_path_string",
    # system
    "CapturedOutput",
    "capture_output",
    "detect_runtime_mode",
    "get_sys_version_info",
    "is_running_under_pytest",
    # text
    "plural",
    "remove_path_in_error_message",
    # types
    "cast_hint",
    "literal_to_set",
    "safe_isinstance",
    "schema_from_typeddict",
]
