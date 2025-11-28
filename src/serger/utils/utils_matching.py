# src/serger/utils/utils_matching.py


from apathetic_utils import is_excluded_raw

from serger.config.config_types import PathResolved
from serger.logs import getAppLogger
from serger.utils.utils_validation import validate_required_keys


def is_excluded(path_entry: PathResolved, exclude_patterns: list[PathResolved]) -> bool:
    """High-level helper for internal use.
    Accepts PathResolved entries and delegates to the smart matcher.
    """
    validate_required_keys(path_entry, {"path", "root"}, "path_entry")
    for exc in exclude_patterns:
        validate_required_keys(exc, {"path", "root"}, "exclude_patterns item")
    logger = getAppLogger()
    path = path_entry["path"]
    root = path_entry["root"]
    # Patterns are always normalized to PathResolved["path"] under config_resolve
    patterns = [str(e["path"]) for e in exclude_patterns]
    result = is_excluded_raw(path, patterns, root)
    logger.trace(
        f"[is_excluded] path={path}, root={root},"
        f" patterns={len(patterns)}, excluded={result}"
    )
    return result
