# tests/utils/config_validate.py

from apathetic_schema.types import ApatheticSchema_ValidationSummary


def make_summary(
    *,
    valid: bool = True,
    errors: list[str] | None = None,
    strict_warnings: list[str] | None = None,
    warnings: list[str] | None = None,
    strict: bool = True,
) -> ApatheticSchema_ValidationSummary:
    """Helper to create a clean ValidationSummary."""
    return ApatheticSchema_ValidationSummary(
        valid=valid,
        errors=errors or [],
        strict_warnings=strict_warnings or [],
        warnings=warnings or [],
        strict=strict,
    )
