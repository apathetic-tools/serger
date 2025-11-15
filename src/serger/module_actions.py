"""Module actions processing for renaming, moving, copying, and deleting modules."""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from serger.config.config_types import (
        ModuleActionFull,
        ModuleActionMode,
        ModuleActionScope,
    )


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


def validate_action_source_exists(
    action: "ModuleActionFull",
    available_modules: set[str],
) -> None:
    """Validate that action source exists in available modules.

    Args:
        action: Action to validate
        available_modules: Set of available module names

    Raises:
        ValueError: If source does not exist in available modules
    """
    source = action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
    if source not in available_modules:
        msg = f"Module action source '{source}' does not exist in available modules"
        raise ValueError(msg)


def validate_action_dest(
    action: "ModuleActionFull",
    existing_modules: set[str],
    *,
    allowed_destinations: set[str] | None = None,
) -> None:
    """Validate action destination (conflicts, required for move/copy, etc.).

    Args:
        action: Action to validate
        existing_modules: Set of existing module names (for conflict checking)
        allowed_destinations: Optional set of destinations that are allowed
            even if they exist in existing_modules (e.g., target package for
            mode-generated actions). If None, no special exceptions.

    Raises:
        ValueError: If destination is invalid
    """
    action_type = action.get("action", "move")
    dest = action.get("dest")

    # Delete actions must not have dest
    if action_type == "delete" and dest is not None:
        msg = (
            f"Module action 'delete' must not have 'dest' field, but got dest='{dest}'"
        )
        raise ValueError(msg)
    if action_type == "delete":
        return

    # Move and copy actions require dest
    if action_type in ("move", "copy"):
        if dest is None:
            msg = (
                f"Module action '{action_type}' requires 'dest' field, "
                f"but it is missing"
            )
            raise ValueError(msg)

        # For move, dest must not conflict with existing modules
        # Exception: if dest is in allowed_destinations, it's allowed
        # (e.g., target package for mode-generated actions)
        # For copy, dest can conflict (it's allowed to overwrite)
        if (
            action_type == "move"
            and dest in existing_modules
            and (allowed_destinations is None or dest not in allowed_destinations)
        ):
            msg = (
                f"Module action 'move' destination '{dest}' "
                f"conflicts with existing module"
            )
            raise ValueError(msg)


def validate_no_circular_moves(
    actions: list["ModuleActionFull"],
) -> None:
    """Validate no circular move operations.

    Detects direct and indirect circular move chains (e.g., A -> B, B -> A
    or A -> B, B -> C, C -> A).

    Args:
        actions: List of actions to validate

    Raises:
        ValueError: If circular move chain is detected
    """
    # Build a mapping of source -> dest for move operations only
    move_map: dict[str, str] = {}
    for action in actions:
        action_type = action.get("action", "move")
        if action_type == "move":
            source = action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
            dest = action.get("dest")
            if dest is not None:
                move_map[source] = dest

    # Check for circular chains using DFS
    visited: set[str] = set()
    path: set[str] = set()

    def has_cycle(node: str) -> bool:
        """Check if there's a cycle starting from node."""
        if node in path:
            return True  # Found a cycle
        if node in visited:
            return False  # Already checked, no cycle from here

        visited.add(node)
        path.add(node)

        # Follow the move chain
        if node in move_map:
            next_node = move_map[node]
            if has_cycle(next_node):
                return True

        path.remove(node)
        return False

    # Check each node for cycles
    for source in move_map:
        if source not in visited and has_cycle(source):
            # Find the cycle path for error message
            cycle_path: list[str] = []
            current = source
            seen_in_cycle: set[str] = set()
            while current not in seen_in_cycle:
                seen_in_cycle.add(current)
                cycle_path.append(current)
                if current in move_map:
                    current = move_map[current]
                else:
                    break
            # Add the closing link
            if cycle_path:
                cycle_path.append(cycle_path[0])
            cycle_str = " -> ".join(cycle_path)
            msg = f"Circular move chain detected: {cycle_str}"
            raise ValueError(msg)


def validate_no_conflicting_operations(  # noqa: PLR0912
    actions: list["ModuleActionFull"],
) -> None:
    """Validate no conflicting operations (delete then move, etc.).

    Checks for conflicts like:
    - Can't delete something that's being moved/copied
    - Can't move/copy to something that's being deleted
    - Can't move/copy to something that's being moved/copied from
      (unless it's a copy, which allows overwriting)

    Args:
        actions: List of actions to validate

    Raises:
        ValueError: If conflicting operations are detected
    """
    # Collect all sources and destinations
    sources: set[str] = set()
    dests: set[str] = set()
    deleted: set[str] = set()
    moved_from: set[str] = set()
    copied_from: set[str] = set()

    for action in actions:
        source = action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        action_type = action.get("action", "move")
        dest = action.get("dest")

        sources.add(source)

        if action_type == "delete":
            deleted.add(source)
        elif action_type == "move":
            moved_from.add(source)
            if dest is not None:
                dests.add(dest)
        elif action_type == "copy":
            copied_from.add(source)
            if dest is not None:
                dests.add(dest)

    # Check: Can't delete something that's being moved/copied
    for action in actions:
        source = action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        action_type = action.get("action", "move")
        if action_type == "delete" and (source in moved_from or source in copied_from):
            msg = (
                f"Cannot delete module '{source}' because it is "
                f"being moved or copied in another action"
            )
            raise ValueError(msg)

    # Check: Can't move/copy to something that's being deleted
    for action in actions:
        action_type = action.get("action", "move")
        dest = action.get("dest")
        if dest is not None and dest in deleted:
            msg = (
                f"Cannot {action_type} to '{dest}' because it is "
                f"being deleted in another action"
            )
            raise ValueError(msg)

    # Check: Can't move to something that's being moved/copied from
    # (copy is allowed to overwrite, but move is not)
    # Exception: If a module is only a destination (not a source) in other
    # actions, it's allowed to move it (e.g., moving target package after
    # mode actions have moved things into it)
    for action in actions:
        action_type = action.get("action", "move")
        dest = action.get("dest")
        # Check if dest is being moved/copied FROM (not just TO)
        # Only error if dest is a source of another action
        if (
            action_type == "move"
            and dest is not None
            and (dest in moved_from or dest in copied_from)
        ):
            # But allow if dest is also a destination in other actions
            # (it's being moved into, then moved from - this is valid)
            # Only error if dest is ONLY a source (not also a destination)
            # Check if dest appears as a destination in any other action
            dest_is_also_destination = any(
                other_action.get("dest") == dest
                for other_action in actions
                if other_action is not action
            )
            if not dest_is_also_destination:
                msg = (
                    f"Cannot move to '{dest}' because it is being "
                    f"moved or copied from in another action"
                )
                raise ValueError(msg)


def validate_module_actions(
    actions: list["ModuleActionFull"],
    original_modules: set[str],
    _detected_packages: set[str],
    *,
    scope: "ModuleActionScope | None" = None,
) -> None:
    """Validate module actions upfront.

    For scope: "original" actions, validates against original module tree.
    For scope: "shim" actions, validates incrementally (call after each action).

    Args:
        actions: List of actions to validate
        original_modules: Set of original module names (for upfront validation)
        detected_packages: Set of detected package names (for context)
        scope: Optional scope filter - if provided, only validate actions
            with this scope. If None, validate all actions.

    Raises:
        ValueError: For invalid operations
    """
    # Filter by scope if provided
    filtered_actions = actions
    if scope is not None:
        filtered_actions = [
            action for action in actions if action.get("scope") == scope
        ]

    if not filtered_actions:
        return

    # Determine available modules based on scope
    # For "original" scope, use original_modules
    # For "shim" scope, this will be called incrementally with current state
    # For incremental validation, available_modules should be passed
    # as the current state. For now, we'll use original_modules as
    # a fallback, but this should be called with current state.
    # This is a design note: incremental validation should be called
    # with the current transformed module set.
    available_modules = original_modules

    # Validate each action's source exists
    for action in filtered_actions:
        validate_action_source_exists(action, available_modules)

    # Validate no circular moves first (before dest conflicts)
    # Circular moves can cause false dest conflicts
    validate_no_circular_moves(filtered_actions)

    # Validate each action's destination
    # For mode-generated actions (scope: "original"), allow moving into
    # the target package even if it exists. Extract target packages from
    # actions that have scope: "original" and dest in existing_modules.
    allowed_destinations: set[str] | None = None
    if scope == "original" or scope is None:
        # Check if any action is moving into an existing module
        # This is allowed for mode-generated actions (target package)
        for action in filtered_actions:
            if action.get("scope") == "original":
                dest = action.get("dest")
                if dest is not None and dest in available_modules:
                    if allowed_destinations is None:
                        allowed_destinations = set()
                    allowed_destinations.add(dest)

    for action in filtered_actions:
        validate_action_dest(
            action, available_modules, allowed_destinations=allowed_destinations
        )

    # Validate no conflicting operations
    validate_no_conflicting_operations(filtered_actions)


def _transform_module_name(  # noqa: PLR0911
    module_name: str,
    source: str,
    dest: str,
    mode: "ModuleActionMode",
) -> str | None:
    """Transform a single module name based on action.

    Handles preserve vs flatten modes:
    - preserve: Keep structure (apathetic_logs.utils -> grinch.utils)
    - flatten: Remove intermediate levels (apathetic_logs.utils -> grinch)

    Args:
        module_name: The module name to transform
        source: Source module path (e.g., "apathetic_logs")
        dest: Destination module path (e.g., "grinch")
        mode: Transformation mode ("preserve" or "flatten")

    Returns:
        Transformed module name, or None if module doesn't match source
    """
    # Check if module_name starts with source
    if not module_name.startswith(source):
        return None

    # Exact match: source -> dest
    if module_name == source:
        return dest

    # Check if it's a submodule (must have a dot after source)
    if not module_name.startswith(f"{source}."):
        return None

    # Extract the suffix (everything after source.)
    suffix = module_name[len(source) + 1 :]

    if mode == "preserve":
        # Preserve structure: dest + suffix
        return f"{dest}.{suffix}"

    # mode == "flatten"
    # Flatten: dest + last component only
    # e.g., "apathetic_logs.utils.text" -> "grinch.text"
    # e.g., "apathetic_logs.utils.schema.validator" -> "grinch.validator"
    if "." in suffix:
        # Multiple levels: take only the last component
        last_component = suffix.split(".")[-1]
        return f"{dest}.{last_component}"

    # Single level: dest + suffix
    return f"{dest}.{suffix}"


def _apply_move_action(
    module_names: list[str],
    action: "ModuleActionFull",
) -> list[str]:
    """Apply move action with preserve or flatten mode.

    Moves modules from source to dest, removing source modules.
    Handles preserve vs flatten modes.

    Args:
        module_names: List of module names to transform
        action: Move action with source, dest, and mode

    Returns:
        Transformed list of module names
    """
    source = action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
    dest = action.get("dest")
    if dest is None:
        msg = "Move action requires 'dest' field"
        raise ValueError(msg)

    mode = action.get("mode", "preserve")
    if mode not in ("preserve", "flatten"):
        msg = f"Invalid mode '{mode}', must be 'preserve' or 'flatten'"
        raise ValueError(msg)

    result: list[str] = []
    for module_name in module_names:
        transformed = _transform_module_name(module_name, source, dest, mode)
        if transformed is not None:
            # Replace source module with transformed name
            result.append(transformed)
        else:
            # Keep modules that don't match source
            result.append(module_name)

    return result


def _apply_copy_action(
    module_names: list[str],
    action: "ModuleActionFull",
) -> list[str]:
    """Apply copy action (source remains, also appears at dest).

    Copies modules from source to dest, keeping source modules.
    Handles preserve vs flatten modes.

    Args:
        module_names: List of module names to transform
        action: Copy action with source, dest, and mode

    Returns:
        Transformed list of module names (includes both original and copied)
    """
    source = action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
    dest = action.get("dest")
    if dest is None:
        msg = "Copy action requires 'dest' field"
        raise ValueError(msg)

    mode = action.get("mode", "preserve")
    if mode not in ("preserve", "flatten"):
        msg = f"Invalid mode '{mode}', must be 'preserve' or 'flatten'"
        raise ValueError(msg)

    result: list[str] = []
    for module_name in module_names:
        # Always keep the original
        result.append(module_name)

        # Also add transformed version if it matches source
        transformed = _transform_module_name(module_name, source, dest, mode)
        if transformed is not None:
            result.append(transformed)

    return result


def _apply_delete_action(
    module_names: list[str],
    action: "ModuleActionFull",
) -> list[str]:
    """Apply delete action (remove module and all submodules).

    Removes the source module and all modules that start with source.

    Args:
        module_names: List of module names to transform
        action: Delete action with source

    Returns:
        Filtered list of module names (deleted modules removed)
    """
    source = action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]

    result: list[str] = []
    for module_name in module_names:
        # Keep modules that don't start with source
        # Check exact match or submodule (must have dot after source)
        if module_name == source:
            # Exact match: delete it
            continue
        if module_name.startswith(f"{source}."):
            # Submodule: delete it
            continue
        # Keep this module
        result.append(module_name)

    return result


def apply_single_action(
    module_names: list[str],
    action: "ModuleActionFull",
    _detected_packages: set[str],
) -> list[str]:
    """Apply a single action to module names.

    Routes to the appropriate action handler based on action type.

    Args:
        module_names: List of module names to transform
        action: Action to apply
        detected_packages: Set of detected package names (for context)

    Returns:
        Transformed list of module names

    Raises:
        ValueError: If action type is invalid or missing required fields
    """
    action_type = action.get("action", "move")

    if action_type == "move":
        return _apply_move_action(module_names, action)
    if action_type == "copy":
        return _apply_copy_action(module_names, action)
    if action_type == "delete":
        return _apply_delete_action(module_names, action)
    if action_type == "none":
        # No-op action
        return module_names

    msg = (
        f"Invalid action type '{action_type}', must be "
        "'move', 'copy', 'delete', or 'none'"
    )
    raise ValueError(msg)


def apply_module_actions(
    module_names: list[str],
    actions: list["ModuleActionFull"],
    _detected_packages: set[str],
) -> list[str]:
    """Apply module actions to transform module names.

    Applies all actions in sequence to transform the module names list.
    Each action is applied to the result of the previous action.

    Args:
        module_names: Initial list of module names
        actions: List of actions to apply in order
        detected_packages: Set of detected package names (for context)

    Returns:
        Transformed list of module names

    Raises:
        ValueError: For invalid operations
    """
    result = list(module_names)

    # Apply each action in sequence
    for action in actions:
        result = apply_single_action(result, action, _detected_packages)

    return result


def _generate_force_actions(
    detected_packages: set[str],
    package_name: str,
    mode: "ModuleActionMode",
) -> list["ModuleActionFull"]:
    """Generate actions for force/force_flat modes.

    Args:
        detected_packages: Set of all detected package names
        package_name: Target package name (excluded from actions)
        mode: "preserve" or "flatten"

    Returns:
        List of actions for root packages
    """
    actions: list[ModuleActionFull] = []
    root_packages = {pkg for pkg in detected_packages if "." not in pkg}
    for pkg in sorted(root_packages):
        if pkg != package_name:
            action: ModuleActionFull = {
                "source": pkg,
                "dest": package_name,
                "mode": mode,
            }
            actions.append(set_mode_generated_action_defaults(action))
    return actions


def _generate_unify_actions(
    detected_packages: set[str],
    package_name: str,
) -> list["ModuleActionFull"]:
    """Generate actions for unify/unify_preserve modes.

    Args:
        detected_packages: Set of all detected package names
        package_name: Target package name (excluded from actions)

    Returns:
        List of actions for all packages
    """
    actions: list[ModuleActionFull] = []
    for pkg in sorted(detected_packages):
        if pkg != package_name:
            action: ModuleActionFull = {
                "source": pkg,
                "dest": f"{package_name}.{pkg}",
                "mode": "preserve",
            }
            actions.append(set_mode_generated_action_defaults(action))
    return actions


def generate_actions_from_mode(
    module_mode: str,
    detected_packages: set[str],
    package_name: str,
) -> list["ModuleActionFull"]:
    """Generate module_actions equivalent to a module_mode.

    Converts module_mode presets into explicit actions that are prepended to
    user-specified actions. Returns list of actions that would produce the
    same result as the mode.

    All generated actions have scope: "original".

    Args:
        module_mode: Mode value ("force", "force_flat", "unify", "multi", etc.)
        detected_packages: Set of all detected package names
        package_name: Target package name (excluded from actions)

    Returns:
        List of actions equivalent to the mode

    Raises:
        ValueError: For invalid mode values
    """
    if module_mode == "force":
        return _generate_force_actions(detected_packages, package_name, "preserve")

    if module_mode == "force_flat":
        return _generate_force_actions(detected_packages, package_name, "flatten")

    if module_mode in ("unify", "unify_preserve"):
        return _generate_unify_actions(detected_packages, package_name)

    if module_mode in ("multi", "none", "flat"):
        # multi: no actions needed (default behavior)
        # none: no shims (handled separately via shim setting)
        # flat: cannot be expressed as actions (requires file-level detection)
        return []

    msg = (
        f"Invalid module_mode: {module_mode!r}. "
        f"Must be one of: 'none', 'multi', 'force', 'force_flat', "
        f"'unify', 'unify_preserve', 'flat'"
    )
    raise ValueError(msg)
