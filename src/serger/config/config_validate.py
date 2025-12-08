# src/serger/config/config_validate.py


from typing import Any

from apathetic_schema import (
    ApatheticSchema_SchemaErrorAggregator,
    ApatheticSchema_ValidationSummary,
    check_schema_conformance,
    collect_msg,
    flush_schema_aggregators,
    warn_keys_once,
)
from apathetic_utils import schema_from_typeddict

from serger.constants import DEFAULT_STRICT_CONFIG
from serger.logs import getAppLogger

from .config_types import RootConfig


# Create aliases (needed for both installed and stitched modes)
SchemaErrorAggregator = ApatheticSchema_SchemaErrorAggregator
ValidationSummary = ApatheticSchema_ValidationSummary


# --- constants ------------------------------------------------------

DRYRUN_KEYS = {"dry-run", "dry_run", "dryrun", "no-op", "no_op", "noop"}
DRYRUN_MSG = (
    "Ignored config key(s) {keys} {ctx}: this tool has no config option for it. "
    "Use the CLI flag '--dry-run' instead."
)

ROOT_ONLY_KEYS = {"watch_interval"}
ROOT_ONLY_MSG = "Ignored {keys} {ctx}: these options only apply at the root level."

# Field-specific type examples for better error messages
# Dict format: {field_pattern: example_value}
# Wildcard patterns (with *) are supported for matching multiple fields
FIELD_EXAMPLES: dict[str, str] = {
    "root.include": '["src/", "lib/"]',
    "root.out": '"dist/script.py"',
    "root.display_name": '"MyProject"',
    "root.description": '"A description of the project"',
    "root.repo": '"https://github.com/user/project"',
    "root.internal_imports": '"force_strip"',
    "root.external_imports": '"top"',
    "root.watch_interval": "1.5",
    "root.log_level": '"debug"',
    "root.strict_config": "true",
}


# ---------------------------------------------------------------------------
# main validator
# ---------------------------------------------------------------------------


def _set_valid_and_return(
    *,
    flush: bool = True,
    summary: ValidationSummary,  # could be modified
    agg: SchemaErrorAggregator,  # could be modified
) -> ValidationSummary:
    if flush:
        flush_schema_aggregators(summary=summary, agg=agg)
    summary.valid = not summary.errors and not summary.strict_warnings
    return summary


def _validate_root(
    parsed_cfg: dict[str, Any],
    *,
    strict_arg: bool | None,
    summary: ValidationSummary,  # modified
    agg: SchemaErrorAggregator,  # modified
) -> ValidationSummary | None:
    logger = getAppLogger()
    logger.trace(f"[validate_root] Validating root with {len(parsed_cfg)} keys")

    strict_config: bool = summary.strict
    # --- Determine strictness from arg or root config or default ---
    strict_from_root: Any = parsed_cfg.get("strict_config")
    if strict_arg is not None and strict_arg:
        strict_config = strict_arg
    elif strict_arg is None and isinstance(strict_from_root, bool):
        strict_config = strict_from_root

    if strict_config:
        summary.strict = True

    # --- Validate root-level keys ---
    root_schema = schema_from_typeddict(RootConfig)
    prewarn_root: set[str] = set()
    ok, found = warn_keys_once(
        "dry-run",
        DRYRUN_KEYS,
        parsed_cfg,
        "in top-level configuration",
        DRYRUN_MSG,
        strict_config=strict_config,
        summary=summary,
        agg=agg,
    )
    prewarn_root |= found

    ok = check_schema_conformance(
        parsed_cfg,
        root_schema,
        "in top-level configuration",
        strict_config=strict_config,
        summary=summary,
        prewarn=prewarn_root,
        ignore_keys={"builds"},
        base_path="root",
        field_examples=FIELD_EXAMPLES,
    )
    if not ok and not (summary.errors or summary.strict_warnings):
        collect_msg(
            "Top-level configuration invalid.",
            strict=True,
            summary=summary,
            is_error=True,
        )

    return None


def _validate_builds(
    parsed_cfg: dict[str, Any],
    *,
    strict_arg: bool | None,  # noqa: ARG001
    summary: ValidationSummary,  # modified
    agg: SchemaErrorAggregator,  # modified
) -> ValidationSummary | None:
    """Validate that 'builds' key is not present (multi-build not supported)."""
    logger = getAppLogger()
    logger.trace("[validate_builds] Checking for unsupported 'builds' key")

    if "builds" in parsed_cfg:
        collect_msg(
            "The 'builds' key is not supported. "
            "Please use a single flat configuration object with all options "
            "at the root level.",
            strict=True,
            summary=summary,
            is_error=True,
        )
        return _set_valid_and_return(summary=summary, agg=agg)

    return None


def validate_config(
    parsed_cfg: dict[str, Any],
    *,
    strict: bool | None = None,
) -> ValidationSummary:
    """Validate normalized config. Returns True if valid.

    strict=True  →  warnings become fatal, but still listed separately
    strict=False →  warnings remain non-fatal

    The `strict_config` key in the root config (and optionally in each build)
    controls strictness. CLI flags are not considered.

    Returns a ValidationSummary object.
    """
    logger = getAppLogger()
    logger.trace(f"[validate_config] Starting validation (strict={strict})")

    summary = ValidationSummary(
        valid=True,
        errors=[],
        strict_warnings=[],
        warnings=[],
        strict=DEFAULT_STRICT_CONFIG,
    )
    agg: SchemaErrorAggregator = {}

    # --- Validate root structure ---
    ret = _validate_root(
        parsed_cfg,
        strict_arg=strict,
        summary=summary,
        agg=agg,
    )
    if ret is not None:
        return ret

    # --- Validate builds structure ---
    ret = _validate_builds(parsed_cfg, strict_arg=strict, summary=summary, agg=agg)
    if ret is not None:
        return ret

    # --- finalize result ---
    return _set_valid_and_return(
        summary=summary,
        agg=agg,
    )
