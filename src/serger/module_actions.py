"""Module actions processing for renaming, moving, copying, and deleting modules."""

from pathlib import Path
from typing import TYPE_CHECKING

from serger.logs import getAppLogger
from serger.utils.utils_modules import derive_module_name


if TYPE_CHECKING:
    from serger.config.config_types import (
        ModuleActionFull,
        ModuleActionMode,
        ModuleActionScope,
    )


def extract_module_name_from_source_path(
    source_path: Path,
    package_root: Path,
    expected_source: str,
) -> str:
    """Extract module name from source_path and verify it matches expected_source.

    Args:
        source_path: Path to Python file
        package_root: Root directory for module name derivation
        expected_source: Expected module name from action source field

    Returns:
        Extracted module name

    Raises:
        ValueError: If module name doesn't match expected_source or file is invalid
    """
    logger = getAppLogger()

    # Validate file exists
    if not source_path.exists():
        msg = f"source_path file does not exist: {source_path}"
        raise ValueError(msg)

    # Validate is Python file
    if source_path.suffix != ".py":
        msg = f"source_path must be a Python file (.py extension), got: {source_path}"
        raise ValueError(msg)

    # Extract module name using derive_module_name
    # Use None for include since source_path files don't have include metadata
    extracted_module_name = derive_module_name(source_path, package_root, include=None)

    # Verify extracted module name matches expected_source
    # Allow exact match or derivable (e.g., if package is "internal" and file
    # has module "internal.utils", source can be "internal.utils" or just "utils")
    if extracted_module_name == expected_source:
        # Exact match
        logger.trace(
            f"[source_path] Module name matches: "
            f"{extracted_module_name} == {expected_source}"
        )
        return extracted_module_name

    # Check if expected_source is a suffix of extracted_module_name
    # (e.g., extracted="internal.utils", expected="utils")
    # Also check if extracted_module_name ends with expected_source
    # (e.g., extracted="other.utils", expected="utils")
    if extracted_module_name.endswith((f".{expected_source}", expected_source)):
        # Suffix match - this is allowed
        logger.trace(
            f"[source_path] Module name suffix matches: "
            f"{extracted_module_name} ends with {expected_source}"
        )
        return extracted_module_name

    # Check if extracted_module_name is a prefix of expected_source
    # (e.g., extracted="utils", expected="internal.utils")
    # This means the file has a shorter module name than expected
    # We don't allow this - the file's module name should match or be longer
    # (e.g., file has "internal.utils", source can be "internal.utils" or "utils")

    # No match - raise error
    msg = (
        f"Module name extracted from source_path ({extracted_module_name}) "
        f"does not match expected source ({expected_source}). "
        f"File: {source_path}, package_root: {package_root}"
    )
    raise ValueError(msg)


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

    Note: User actions from RootConfigResolved already have all defaults
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
    *,
    scope: "ModuleActionScope | None" = None,
) -> None:
    """Validate that action source exists in available modules.

    Args:
        action: Action to validate
        available_modules: Set of available module names
        scope: Optional scope for error message context

    Raises:
        ValueError: If source does not exist in available modules
    """
    source = action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
    if source not in available_modules:
        scope_str = f" (scope: '{scope}')" if scope else ""
        msg = (
            f"Module action source '{source}' does not exist in available modules"
            f"{scope_str}"
        )
        raise ValueError(msg)


def validate_rename_action(
    action: "ModuleActionFull",
    *,
    scope: "ModuleActionScope | None" = None,
) -> None:
    """Validate rename action constraints.

    Rename actions can only rename the last node in the dot sequence.
    The dest must be just the new name (no dots allowed).

    Args:
        action: Rename action to validate
        scope: Optional scope for error message context

    Raises:
        ValueError: If rename action is invalid
    """
    dest = action.get("dest")
    scope_str = f" (scope: '{scope}')" if scope else ""

    if dest is None:
        msg = (
            f"Module action 'rename' requires 'dest' field, "
            f"but it is missing{scope_str}"
        )
        raise ValueError(msg)

    # Dest must not contain dots (only the new name for the last node)
    if "." in dest:
        msg = (
            f"Module action 'rename' dest must not contain dots. "
            f"Got dest='{dest}'. Use 'move' action to move modules down the tree"
            f"{scope_str}"
        )
        raise ValueError(msg)


def validate_action_dest(
    action: "ModuleActionFull",
    existing_modules: set[str],
    *,
    allowed_destinations: set[str] | None = None,
    scope: "ModuleActionScope | None" = None,
) -> None:
    """Validate action destination (conflicts, required for move/copy, etc.).

    Args:
        action: Action to validate
        existing_modules: Set of existing module names (for conflict checking)
        allowed_destinations: Optional set of destinations that are allowed
            even if they exist in existing_modules (e.g., target package for
            mode-generated actions). If None, no special exceptions.
        scope: Optional scope for error message context

    Raises:
        ValueError: If destination is invalid
    """
    action_type = action.get("action", "move")
    dest = action.get("dest")
    scope_str = f" (scope: '{scope}')" if scope else ""

    # Delete actions must not have dest
    if action_type == "delete" and dest is not None:
        msg = (
            f"Module action 'delete' must not have 'dest' field, but got dest='{dest}'"
            f"{scope_str}"
        )
        raise ValueError(msg)
    if action_type == "delete":
        return

    # Rename actions have special validation
    if action_type == "rename":
        validate_rename_action(action, scope=scope)
        # After validating rename constraints, check if the constructed
        # destination conflicts with existing modules
        source = action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        if dest is not None:
            # Construct full destination path: replace last component of source
            if "." in source:
                parent = ".".join(source.split(".")[:-1])
                full_dest = f"{parent}.{dest}"
            else:
                # Top-level module: just use dest
                full_dest = dest

            # Check for conflicts (rename acts like move - can't conflict)
            if full_dest in existing_modules and (
                allowed_destinations is None or full_dest not in allowed_destinations
            ):
                msg = (
                    f"Module action 'rename' destination '{full_dest}' "
                    f"(from source '{source}' + dest '{dest}') "
                    f"conflicts with existing module{scope_str}"
                )
                raise ValueError(msg)
        return

    # Move and copy actions require dest
    if action_type in ("move", "copy"):
        if dest is None:
            msg = (
                f"Module action '{action_type}' requires 'dest' field, "
                f"but it is missing{scope_str}"
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
                f"conflicts with existing module{scope_str}"
            )
            raise ValueError(msg)


def validate_no_circular_moves(  # noqa: C901, PLR0912
    actions: list["ModuleActionFull"],
) -> None:
    """Validate no circular move operations.

    Detects direct and indirect circular move chains (e.g., A -> B, B -> A
    or A -> B, B -> C, C -> A). Includes rename actions (which act like moves).

    Args:
        actions: List of actions to validate

    Raises:
        ValueError: If circular move chain is detected
    """
    # Build a mapping of source -> dest for move and rename operations
    move_map: dict[str, str] = {}
    for action in actions:
        action_type = action.get("action", "move")
        if action_type in ("move", "rename"):
            source = action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
            dest = action.get("dest")
            if dest is not None:
                # For rename, construct full destination path
                if action_type == "rename":
                    if "." in source:
                        parent = ".".join(source.split(".")[:-1])
                        full_dest = f"{parent}.{dest}"
                    else:
                        full_dest = dest
                    move_map[source] = full_dest
                else:
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


def validate_no_conflicting_operations(  # noqa: C901, PLR0912, PLR0915
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
        elif action_type in ("move", "rename"):
            moved_from.add(source)
            if dest is not None:
                # For rename, construct full destination path
                if action_type == "rename":
                    if "." in source:
                        parent = ".".join(source.split(".")[:-1])
                        full_dest = f"{parent}.{dest}"
                    else:
                        full_dest = dest
                    dests.add(full_dest)
                else:
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
        # For rename, construct full destination path
        computed_dest: str | None
        if action_type == "rename" and dest is not None:
            source = action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
            if "." in source:
                parent = ".".join(source.split(".")[:-1])
                computed_dest = f"{parent}.{dest}"
            else:
                computed_dest = dest
        else:
            computed_dest = dest
        # Check if dest is being moved/copied FROM (not just TO)
        # Only error if dest is a source of another action
        if (
            action_type in ("move", "rename")
            and computed_dest is not None
            and (computed_dest in moved_from or computed_dest in copied_from)
        ):
            # But allow if dest is also a destination in other actions
            # (it's being moved into, then moved from - this is valid)
            # Only error if dest is ONLY a source (not also a destination)
            # Check if dest appears as a destination in any other action
            dest_is_also_destination = False
            for other_action in actions:
                if other_action is action:
                    continue
                other_dest = other_action.get("dest")
                if other_dest is not None:
                    # For rename actions, construct full destination path
                    other_action_type = other_action.get("action", "move")
                    if other_action_type == "rename":
                        other_source = other_action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
                        if "." in other_source:
                            other_parent = ".".join(other_source.split(".")[:-1])
                            other_computed_dest = f"{other_parent}.{other_dest}"
                        else:
                            other_computed_dest = other_dest
                        if other_computed_dest == computed_dest:
                            dest_is_also_destination = True
                            break
                    elif other_dest == computed_dest:
                        dest_is_also_destination = True
                        break
            if not dest_is_also_destination:
                msg = (
                    f"Cannot {action_type} to '{computed_dest}' because it is being "
                    f"moved or copied from in another action"
                )
                raise ValueError(msg)


def validate_module_actions(
    actions: list["ModuleActionFull"],
    original_modules: set[str],
    detected_packages: set[str],  # noqa: ARG001
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
        action_scope = action.get("scope") or scope
        validate_action_source_exists(action, available_modules, scope=action_scope)

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
        action_scope = action.get("scope") or scope
        validate_action_dest(
            action,
            available_modules,
            allowed_destinations=allowed_destinations,
            scope=action_scope,
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
        # Try component matching: check if all source components appear in module_name
        # (e.g., "mypkg.module" should match "mypkg.pkg1.module")
        source_parts = source.split(".")
        module_parts = module_name.split(".")
        # Check if first and last components of source match first and last of module
        min_components_for_match = 2
        if (
            len(source_parts) >= min_components_for_match
            and len(module_parts) >= min_components_for_match
            and source_parts[0] == module_parts[0]
            and source_parts[-1] == module_parts[-1]
        ):
            # Component matching: extract middle part(s) from module_name
            # For "mypkg.module" matching "mypkg.pkg1.module":
            # - source_parts = ["mypkg", "module"]
            # - module_parts = ["mypkg", "pkg1", "module"]
            # - middle_parts = ["pkg1"]
            middle_parts = module_parts[1:-1]
            if mode == "preserve":
                # Preserve structure: dest + middle + last component
                if middle_parts:
                    return f"{dest}.{'.'.join(middle_parts)}.{source_parts[-1]}"
                return f"{dest}.{source_parts[-1]}"
            # mode == "flatten"
            # Flatten: just dest (remove middle parts and last component)
            return dest
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


def _apply_rename_action(
    module_names: list[str],
    action: "ModuleActionFull",
) -> list[str]:
    """Apply rename action (rename only the last node in the dot sequence).

    Renames the last component of the source module path. The dest field
    contains only the new name (no dots). For example:
    - source: "foo.bar.baz", dest: "new_name" -> "foo.bar.new_name"
    - source: "foo", dest: "new_name" -> "new_name"

    This is essentially a move action with validation that only allows
    renaming the last node.

    Args:
        module_names: List of module names to transform
        action: Rename action with source and dest (new name only)

    Returns:
        Transformed list of module names
    """
    source = action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
    dest = action.get("dest")
    if dest is None:
        msg = "Rename action requires 'dest' field"
        raise ValueError(msg)

    # Construct full destination path: replace last component of source
    if "." in source:
        parent = ".".join(source.split(".")[:-1])
        full_dest = f"{parent}.{dest}"
    else:
        # Top-level module: just use dest
        full_dest = dest

    # Rename acts like a move with preserve mode (keep structure)
    # We use _transform_module_name with preserve mode to handle submodules
    result: list[str] = []
    for module_name in module_names:
        transformed = _transform_module_name(module_name, source, full_dest, "preserve")
        if transformed is not None:
            # Replace source module with transformed name
            result.append(transformed)
        else:
            # Keep modules that don't match source
            result.append(module_name)

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
        # Keep modules that don't match source
        # Check exact match, starts with source., or source appears as component
        if module_name == source:
            # Exact match: delete it
            continue
        if module_name.startswith(f"{source}."):
            # Submodule: delete it
            continue
        # Check if source appears as a component in module_name
        # (e.g., "mypkg.pkg1" contains "pkg1" as a component)
        if source in module_name.split("."):
            # Source is a component: delete it
            continue
        # Keep this module
        result.append(module_name)

    return result


def apply_single_action(
    module_names: list[str],
    action: "ModuleActionFull",
    detected_packages: set[str],  # noqa: ARG001
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
    if action_type == "rename":
        return _apply_rename_action(module_names, action)
    if action_type == "delete":
        return _apply_delete_action(module_names, action)
    if action_type == "none":
        # No-op action
        return module_names

    msg = (
        f"Invalid action type '{action_type}', must be "
        "'move', 'copy', 'delete', 'rename', or 'none'"
    )
    raise ValueError(msg)


def apply_module_actions(
    module_names: list[str],
    actions: list["ModuleActionFull"],
    detected_packages: set[str],
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
        result = apply_single_action(result, action, detected_packages)

    return result


def _generate_force_actions(  # noqa: PLR0912, C901
    detected_packages: set[str],
    package_name: str,
    mode: "ModuleActionMode",
    *,
    module_names: list[str] | None = None,
    source_bases: list[str] | None = None,
) -> list["ModuleActionFull"]:
    """Generate actions for force/force_flat modes.

    For "preserve" mode: Only generates actions for top-level root packages.
    For "flatten" mode: Generates actions for all first components of multi-level
    module names to flatten all intermediate levels.

    Args:
        detected_packages: Set of all detected package names
        package_name: Target package name (excluded from actions)
        mode: "preserve" or "flatten"
        module_names: Optional list of module names (required for flatten mode
            to identify all first components that need flattening)
        source_bases: Optional list of source base directories for detecting
            nested packages

    Returns:
        List of actions for packages/modules to transform
    """
    actions: list[ModuleActionFull] = []

    if mode == "flatten" and module_names is not None:
        # For flatten mode, generate actions for all first components of
        # multi-level module names to flatten all intermediate levels
        first_components: set[str] = set()
        for mod_name in module_names:
            if "." in mod_name:
                first_part = mod_name.split(".", 1)[0]
                if first_part != package_name:
                    first_components.add(first_part)

        # Also include detected root packages that aren't package_name
        root_packages = {pkg for pkg in detected_packages if "." not in pkg}
        for pkg in root_packages:
            if pkg != package_name:
                first_components.add(pkg)

        for component in sorted(first_components):
            component_action: ModuleActionFull = {
                "source": component,
                "dest": package_name,
                "mode": "flatten",
            }
            actions.append(set_mode_generated_action_defaults(component_action))
    else:
        # For preserve mode, only generate actions for top-level root packages
        root_packages = {pkg for pkg in detected_packages if "." not in pkg}
        # Filter to only top-level root packages (not nested under other packages)
        top_level_packages: set[str] = set()
        logger = getAppLogger()
        logger.trace(
            "[FORCE_ACTIONS] preserve mode: detected_packages=%s, "
            "root_packages=%s, source_bases=%s, module_names=%s",
            sorted(detected_packages),
            sorted(root_packages),
            source_bases,
            module_names[:5] if module_names else None,  # First 5 for brevity
        )
        for pkg in root_packages:
            if pkg == package_name:
                continue
            # Check if this package is nested under any other detected package
            is_nested = False
            for other_pkg in detected_packages:
                # Check if pkg is nested under other_pkg
                # e.g., if other_pkg="pkg1" and pkg="sub", check if "pkg1.sub"
                # exists
                if other_pkg not in (pkg, package_name):
                    # Check if "other_pkg.pkg" is in detected_packages
                    if f"{other_pkg}.{pkg}" in detected_packages:
                        is_nested = True
                        break
                    # Check if any module name starts with "other_pkg.pkg."
                    if any(
                        mod.startswith(f"{other_pkg}.{pkg}.")
                        for mod in detected_packages
                    ):
                        is_nested = True
                        break
                    # Check if other_pkg is in source_bases and pkg appears in
                    # module_names, suggesting pkg is nested under other_pkg
                    # This handles cases where pkg1 is in source_bases and contains
                    # sub, but module names are "sub.mod1" not "pkg1.sub.mod1"
                    if source_bases and module_names:
                        # Check if other_pkg appears as a directory name in source_bases
                        other_pkg_in_bases = any(
                            Path(base).name == other_pkg
                            or base.endswith((f"/{other_pkg}", f"\\{other_pkg}"))
                            for base in source_bases
                        )
                        if other_pkg_in_bases:
                            # Check if pkg appears in module_names as a component
                            # under other_pkg (e.g., other_pkg.pkg.X or other_pkg.pkg)
                            # This indicates pkg is nested under other_pkg
                            pkg_nested_under_other = any(
                                mod_name.startswith(f"{other_pkg}.{pkg}.")
                                or mod_name == f"{other_pkg}.{pkg}"
                                for mod_name in module_names
                            )
                            if pkg_nested_under_other:
                                # other_pkg is in source_bases and pkg appears nested
                                # under other_pkg in module_names
                                logger.trace(
                                    "[FORCE_ACTIONS] Detected %s as nested under %s "
                                    "(found %s.%s in module_names)",
                                    pkg,
                                    other_pkg,
                                    other_pkg,
                                    pkg,
                                )
                                is_nested = True
                                break
                            # Also check if pkg appears as standalone in module_names
                            # AND other_pkg is a parent directory in source_bases
                            # (this handles cases where module names are "pkg.X" not
                            # "other_pkg.pkg.X" because derive_module_name used
                            # other_pkg as module_base)
                            # BUT: Only if other_pkg doesn't also appear standalone
                            # (to avoid false positives when both are top-level)
                            pkg_standalone_in_names = any(
                                mod_name == pkg or mod_name.startswith(f"{pkg}.")
                                for mod_name in module_names
                            )
                            other_pkg_standalone_in_names = any(
                                mod_name == other_pkg
                                or mod_name.startswith(f"{other_pkg}.")
                                for mod_name in module_names
                            )
                            # Only consider pkg nested if:
                            # 1. pkg appears standalone in module_names
                            # 2. other_pkg is in source_bases
                            # 3. other_pkg does NOT also appear standalone
                            #    (if both appear standalone, they're siblings)
                            if (
                                pkg_standalone_in_names
                                and not other_pkg_standalone_in_names
                            ):
                                logger.trace(
                                    "[FORCE_ACTIONS] Detected %s as nested under %s "
                                    "(other_pkg in source_bases, pkg standalone "
                                    "but other_pkg isn't)",
                                    pkg,
                                    other_pkg,
                                )
                                is_nested = True
                                break
            if not is_nested:
                top_level_packages.add(pkg)

        for pkg in sorted(top_level_packages):
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
    *,
    module_names: list[str] | None = None,
    source_bases: list[str] | None = None,
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
        module_names: Optional list of module names (required for flatten mode
            to identify all first components that need flattening)
        source_bases: Optional list of source base directories for detecting
            nested packages

    Returns:
        List of actions equivalent to the mode

    Raises:
        ValueError: For invalid mode values
    """
    if module_mode == "force":
        return _generate_force_actions(
            detected_packages,
            package_name,
            "preserve",
            module_names=module_names,
            source_bases=source_bases,
        )

    if module_mode == "force_flat":
        return _generate_force_actions(
            detected_packages,
            package_name,
            "flatten",
            module_names=module_names,
            source_bases=source_bases,
        )

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


def separate_actions_by_affects(
    actions: list["ModuleActionFull"],
) -> tuple[
    list["ModuleActionFull"], list["ModuleActionFull"], list["ModuleActionFull"]
]:
    """Separate actions by affects value.

    Args:
        actions: List of actions to separate

    Returns:
        Tuple of (shims_only_actions, stitching_only_actions, both_actions)
    """
    shims_only: list[ModuleActionFull] = []
    stitching_only: list[ModuleActionFull] = []
    both: list[ModuleActionFull] = []

    for action in actions:
        affects = action.get("affects", "shims")
        if affects == "shims":
            shims_only.append(action)
        elif affects == "stitching":
            stitching_only.append(action)
        elif affects == "both":
            both.append(action)
        else:
            # Default to shims for backward compatibility
            shims_only.append(action)

    return shims_only, stitching_only, both


def get_deleted_modules_from_actions(
    actions: list["ModuleActionFull"],
    initial_modules: list[str],
    detected_packages: set[str],  # noqa: ARG001
) -> set[str]:
    """Get set of modules that are deleted by actions.

    Applies delete actions to determine which modules are removed.

    Args:
        actions: List of actions to apply
        initial_modules: Initial list of module names
        detected_packages: Set of detected package names (for context)

    Returns:
        Set of module names that are deleted
    """
    # Start with all initial modules
    current_modules = set(initial_modules)

    # Apply delete actions to track what gets deleted
    for action in actions:
        action_type = action.get("action", "move")
        if action_type == "delete":
            source = action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
            # Remove source and all submodules
            to_remove: set[str] = set()
            for mod in current_modules:
                if mod == source or mod.startswith(f"{source}."):
                    to_remove.add(mod)
            current_modules -= to_remove

    # Return the difference (what was deleted)
    initial_set = set(initial_modules)
    return initial_set - current_modules


def check_shim_stitching_mismatches(
    shim_modules: set[str],
    stitched_modules: set[str],
    actions: list["ModuleActionFull"],
) -> list[tuple["ModuleActionFull", set[str]]]:
    """Check for shims pointing to modules deleted from stitching.

    Args:
        shim_modules: Set of module names that have shims
        stitched_modules: Set of module names that are in stitched code
        actions: List of actions that were applied

    Returns:
        List of tuples (action, broken_shims) where broken_shims is the set
        of shim module names that point to deleted modules
    """
    mismatches: list[tuple[ModuleActionFull, set[str]]] = []

    # Find modules that have shims but are not in stitched code
    broken_shims = shim_modules - stitched_modules

    if not broken_shims:
        return mismatches

    # For each action, check if it could have caused the mismatch
    # (i.e., if it deleted from stitching but not from shims)
    for action in actions:
        affects = action.get("affects", "shims")
        action_type = action.get("action", "move")

        # Only actions that affect stitching (but not shims) can cause mismatches
        if affects in ("stitching", "both") and action_type == "delete":
            source = action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
            # Check if any broken shims match this action's source
            # broken_shim is a full module path (e.g., "mypkg.pkg1.module"),
            # source is a package/module name (e.g., "pkg1")
            # We need to check if the broken shim belongs to the deleted package
            action_broken_shims: set[str] = set()
            for broken_shim in broken_shims:
                # Check if broken shim matches source exactly
                # Also check if source appears as a path component in broken_shim
                # (e.g., "mypkg.pkg1.module" contains "pkg1" as a component)
                if (
                    broken_shim == source
                    or broken_shim.endswith(f".{source}")
                    or f".{source}." in broken_shim
                    or broken_shim.startswith(f"{source}.")
                    or source in broken_shim.split(".")
                ):
                    action_broken_shims.add(broken_shim)

            if action_broken_shims:
                mismatches.append((action, action_broken_shims))

    return mismatches


def apply_cleanup_behavior(
    mismatches: list[tuple["ModuleActionFull", set[str]]],
    shim_modules: set[str],
) -> tuple[set[str], list[str]]:
    """Apply cleanup behavior for shim-stitching mismatches.

    Args:
        mismatches: List of tuples (action, broken_shims) from
            check_shim_stitching_mismatches
        shim_modules: Set of all shim module names (will be modified)

    Returns:
        Tuple of (updated_shim_modules, warnings) where warnings is a list
        of warning messages

    Raises:
        ValueError: If cleanup: "error" and mismatches exist
    """
    logger = getAppLogger()
    warnings: list[str] = []
    shims_to_remove: set[str] = set()

    for action, broken_shims in mismatches:
        cleanup = action.get("cleanup", "auto")
        source = action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]

        if cleanup == "error":
            # Raise error with clear message
            broken_list = sorted(broken_shims)
            affects_val = action.get("affects", "shims")
            msg = (
                f"Module action on '{source}' with affects='{affects_val}' "
                f"and cleanup='error' created broken shims pointing to "
                f"deleted modules: {', '.join(broken_list)}"
            )
            raise ValueError(msg)

        if cleanup == "auto":
            # Auto-delete broken shims
            shims_to_remove.update(broken_shims)
            if broken_shims:
                broken_list = sorted(broken_shims)
                warning_msg = (
                    f"Auto-deleting broken shims for action on '{source}': "
                    f"{', '.join(broken_list)}"
                )
                warnings.append(warning_msg)
                logger.warning(warning_msg)

        elif cleanup == "ignore":
            # Keep broken shims (no action)
            pass

    # Remove broken shims
    updated_shims = shim_modules - shims_to_remove

    return updated_shims, warnings
