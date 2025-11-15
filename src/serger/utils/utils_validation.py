# src/serger/utils/utils_validation.py


from typing import Any, cast


def validate_required_keys(
    config: dict[str, Any] | Any,
    required_keys: set[str],
    param_name: str,
) -> None:
    """Validate that a config dict contains all required keys.

    Args:
        config: The config dict to validate (TypedDict or dict)
        required_keys: Set of required key names
        param_name: Name of the parameter (for error messages)

    Raises:
        TypeError: If any required keys are missing
    """
    if not required_keys:
        return

    # TypedDict is a dict at runtime, but type checkers need help
    config_dict = cast("dict[str, Any]", config)
    missing = required_keys - config_dict.keys()
    if missing:
        missing_str = ", ".join(sorted(missing))
        xmsg = (
            f"Missing required keys in {param_name}: {missing_str}. "
            f"Required keys: {', '.join(sorted(required_keys))}"
        )
        raise TypeError(xmsg)
