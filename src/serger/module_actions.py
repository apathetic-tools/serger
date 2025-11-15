"""Module actions processing for renaming, moving, copying, and deleting modules."""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from serger.config.config_types import (
        ModuleActionFull,
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
) -> None:
    """Validate action destination (conflicts, required for move/copy, etc.).

    Args:
        action: Action to validate
        existing_modules: Set of existing module names (for conflict checking)

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
        # For copy, dest can conflict (it's allowed to overwrite)
        if action_type == "move" and dest in existing_modules:
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


def validate_no_conflicting_operations(
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
    for action in actions:
        action_type = action.get("action", "move")
        dest = action.get("dest")
        if (
            action_type == "move"
            and dest is not None
            and (dest in moved_from or dest in copied_from)
        ):
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
    for action in filtered_actions:
        validate_action_dest(action, available_modules)

    # Validate no conflicting operations
    validate_no_conflicting_operations(filtered_actions)
