# tests/utils/config_validate.py


import apathetic_schema.schema as amod_schema


def make_summary(
    *,
    valid: bool = True,
    errors: list[str] | None = None,
    strict_warnings: list[str] | None = None,
    warnings: list[str] | None = None,
    strict: bool = True,
) -> amod_schema.ValidationSummary:
    """Helper to create a clean ValidationSummary."""
    return amod_schema.ValidationSummary(
        valid=valid,
        errors=errors or [],
        strict_warnings=strict_warnings or [],
        warnings=warnings or [],
        strict=strict,
    )
