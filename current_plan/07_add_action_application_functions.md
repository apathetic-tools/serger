# Iteration 07: Add Action Application Functions
> **Context**: See `current_plan/00_overview.md` for overall strategy and principles.


## Goal
Add functions to apply module actions (move, copy, delete) to transform module names. This includes handling `preserve` and `flatten` modes.

## Changes

### 1. Add Application Functions (`src/serger/module_actions.py`)
```python
def apply_module_actions(
    module_names: list[str],
    actions: list[ModuleActionFull],
    detected_packages: set[str],
) -> list[str]:
    """
    Apply module actions to transform module names.
    
    Returns transformed module_names list.
    Raises ValueError for invalid operations.
    """

def apply_single_action(
    module_names: list[str],
    action: ModuleActionFull,
    detected_packages: set[str],
) -> list[str]:
    """Apply a single action to module names."""

def _apply_move_action(
    module_names: list[str],
    action: ModuleActionFull,
) -> list[str]:
    """Apply move action with preserve or flatten mode."""

def _apply_copy_action(
    module_names: list[str],
    action: ModuleActionFull,
) -> list[str]:
    """Apply copy action (source remains, also appears at dest)."""

def _apply_delete_action(
    module_names: list[str],
    action: ModuleActionFull,
) -> list[str]:
    """Apply delete action (remove module and all submodules)."""

def _transform_module_name(
    module_name: str,
    source: str,
    dest: str,
    mode: ModuleActionMode,
) -> str | None:
    """
    Transform a single module name based on action.
    
    Returns transformed name or None if module doesn't match source.
    Handles preserve vs flatten modes.
    """
```

### 2. Implementation Details
- **Move with preserve**: `apathetic_logs.utils` → `grinch.utils` (keep structure)
- **Move with flatten**: `apathetic_logs.utils` → `grinch` (remove intermediate levels)
- **Copy**: Source remains, also appears at destination
- **Delete**: Remove module and all submodules (e.g., `pkg.sub` removes `pkg.sub`, `pkg.sub.module`, etc.)

### 3. Handle Package Creation
- When destination path doesn't exist (e.g., `grinch.xmas.topper`), intermediate packages are created
- This happens during shim generation (existing logic), but we need to track what packages exist

### 4. Add Tests
- `tests/5_core/test_module_actions.py`: Test application functions
  - Test move with preserve mode
  - Test move with flatten mode
  - Test copy action (source remains)
  - Test delete action (removes module and submodules)
  - Test multi-level paths (e.g., `grinch.xmas.topper`)
  - Test multiple actions in sequence
  - Test that original modules are preserved correctly
  - Test edge cases (empty list, no matching modules, etc.)

## Notes
- Functions are ready but not yet called from stitch logic
- All transformation logic is centralized here
- Functions work on module name lists, not file paths

## Testing
- Run `poetry run poe check:fix` - must pass
- Comprehensive tests for all action types and modes
- Test complex scenarios (multiple actions, nested packages, etc.)

## Review and Clarifying Questions

**After implementing this iteration**, review the changes and document any questions that arise:

1. **Review the implementation**:
   - Check that all action types (move, copy, delete) work correctly
   - Verify preserve vs flatten modes work as expected
   - Check that copy actions keep source in place
   - Verify delete actions remove module and all submodules
   - Check that multi-level paths are handled correctly

2. **Document any questions**:
   - Are there edge cases in action application that need clarification?
   - How should we handle overlapping actions (e.g., move then delete same module)?
   - Are there any performance concerns with large module lists?
   - Should we validate module names after transformation?

3. **Resolve before proceeding**:
   - Answer all questions before moving to iteration 08
   - Update implementation if needed
   - Update iteration 08 plan if decisions affect it

**Questions to consider**:
- How should we handle intermediate package creation (e.g., `grinch.xmas.topper` when `grinch.xmas` doesn't exist)?
- Should we track which packages were created vs which existed originally?
- Are there any edge cases with flatten mode and deeply nested packages?

## Commit Message
```
feat(module_actions): add action application functions

- Add apply_module_actions() to transform module names
- Add apply_single_action() for incremental application
- Add _apply_move_action() with preserve/flatten modes
- Add _apply_copy_action() to duplicate modules
- Add _apply_delete_action() to remove modules
- Add _transform_module_name() for name transformation logic
- Add comprehensive unit tests for all action types
- Not yet integrated into stitch logic (coming in later iteration)
```

## Final Step: Update START_HERE.md

After completing this iteration, update `current_plan/START_HERE.md`:
- Mark iteration 07 as completed ✓
- Update the "Current status" section with what was accomplished in this iteration
- Update "Next step" to point to iteration 08
- Include a brief summary of what was done (e.g., "Added action application functions for move, copy, and delete with preserve/flatten modes")

This ensures the next chat session can pick up where this one left off.

