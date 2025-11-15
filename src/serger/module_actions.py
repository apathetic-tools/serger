"""Module actions processing for renaming, moving, copying, and deleting modules."""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from serger.config.config_types import ModuleActionFull


def set_mode_generated_action_defaults(
    action: "ModuleActionFull",
) -> "ModuleActionFull":
    """Set default values for mode-generated actions.

    Mode-generated actions are created fresh (not from config), so they need
    defaults applied. All mode-generated actions have:
    - action: "move" (if not specified)
    - mode: "preserve" (if not specified)
    - scope: "original" (always set for mode-generated)
    - affects: "shims" (if not specified)
    - cleanup: "auto" (if not specified)

    Note: User actions from BuildConfigResolved already have all defaults
    applied (including scope: "shim") from config resolution (iteration 04).

    Args:
        action: Action dict that may be missing some fields

    Returns:
        Action dict with all fields present (defaults applied)
    """
    # Create a copy to avoid mutating the input
    result: ModuleActionFull = dict(action)  # type: ignore[assignment]

    # Set defaults for fields that may be missing
    if "action" not in result:
        result["action"] = "move"
    if "mode" not in result:
        result["mode"] = "preserve"
    # Always set scope to "original" for mode-generated actions
    result["scope"] = "original"
    if "affects" not in result:
        result["affects"] = "shims"
    if "cleanup" not in result:
        result["cleanup"] = "auto"

    return result
