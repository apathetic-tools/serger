# src/serger/utils/__init__.py

import importlib
from typing import TYPE_CHECKING, Any

# Re-export all public utilities from submodules
# Import modules that don't depend on logs.py at module level
from .utils_logs import (
    LEVEL_ORDER,
    RESET,
    TEST_TRACE,
    ApatheticCLILogger,
    safe_log,
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


# Modules that depend on logs.py (directly or transitively) are imported lazily
# via __getattr__ to avoid circular dependency when logs.py imports from
# .utils.utils_logs. This works in stitched mode because __getattr__ is called
# at runtime, not import time.
_modules_with_logs_dependency = {
    "derive_module_name": (".utils_modules", "derive_module_name"),
    "fnmatchcase_portable": (".utils_matching", "fnmatchcase_portable"),
    "get_glob_root": (".utils_paths", "get_glob_root"),
    "has_glob_chars": (".utils_paths", "has_glob_chars"),
    "is_excluded": (".utils_matching", "is_excluded"),
    "is_excluded_raw": (".utils_matching", "is_excluded_raw"),
    "load_jsonc": (".utils_files", "load_jsonc"),
    "load_toml": (".utils_files", "load_toml"),
    "normalize_path_string": (".utils_paths", "normalize_path_string"),
    "SchemaErrorAggregator": (".utils_schema", "SchemaErrorAggregator"),
    "ValidationSummary": (".utils_schema", "ValidationSummary"),
    "check_schema_conformance": (".utils_schema", "check_schema_conformance"),
    "collect_msg": (".utils_schema", "collect_msg"),
    "flush_schema_aggregators": (".utils_schema", "flush_schema_aggregators"),
    "warn_keys_once": (".utils_schema", "warn_keys_once"),
}


def __getattr__(name: str) -> Any:
    """Lazy import for modules that depend on logs.py to avoid circular dependency."""
    if name in _modules_with_logs_dependency:
        module_path, attr_name = _modules_with_logs_dependency[name]
        # Convert relative import path to absolute
        # (e.g., ".utils_modules" -> "serger.utils.utils_modules")
        full_module_path = f"serger.utils{module_path}"
        module = importlib.import_module(full_module_path)
        return getattr(module, attr_name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


# Type stubs for lazy-loaded attributes (via __getattr__) to help type checkers
# These are not actually assigned here, but are available at runtime via __getattr__
if TYPE_CHECKING:
    from .utils_files import load_jsonc, load_toml
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
