# src/serger/utils/__init__.py

from .utils_files import load_jsonc, load_toml

# Re-export all public utilities from submodules
from .utils_logs import (
    LEVEL_ORDER,
    RESET,
    TEST_TRACE,
    ApatheticCLILogger,
    get_logger,
    safe_log,
)
from .utils_matching import (
    fnmatchcase_portable,
    is_excluded,
    is_excluded_raw,
)
from .utils_modules import derive_module_name
from .utils_paths import get_glob_root, has_glob_chars, normalize_path_string
from .utils_schema import (
    SchemaErrorAggregator,
    ValidationSummary,
    check_schema_conformance,
    collect_msg,
    flush_schema_aggregators,
    warn_keys_once,
)
from .utils_system import (
    CapturedOutput,
    capture_output,
    detect_runtime_mode,
    get_sys_version_info,
    is_running_under_pytest,
)
from .utils_text import plural, remove_path_in_error_message
from .utils_types import (
    cast_hint,
    make_includeresolved,
    make_pathresolved,
    safe_isinstance,
    schema_from_typeddict,
)


__all__ = [
    "LEVEL_ORDER",
    "RESET",
    "TEST_TRACE",
    "ApatheticCLILogger",
    "CapturedOutput",
    "SchemaErrorAggregator",
    "ValidationSummary",
    "capture_output",
    "cast_hint",
    "check_schema_conformance",
    "collect_msg",
    "derive_module_name",
    "detect_runtime_mode",
    "flush_schema_aggregators",
    "fnmatchcase_portable",
    "get_glob_root",
    "get_logger",
    "get_sys_version_info",
    "has_glob_chars",
    "is_excluded",
    "is_excluded_raw",
    "is_running_under_pytest",
    "load_jsonc",
    "load_toml",
    "make_includeresolved",
    "make_pathresolved",
    "normalize_path_string",
    "plural",
    "remove_path_in_error_message",
    "safe_isinstance",
    "safe_log",
    "schema_from_typeddict",
    "warn_keys_once",
]
