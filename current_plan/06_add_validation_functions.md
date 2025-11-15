# Iteration 06: Add Validation Functions
> **Context**: See `current_plan/00_overview.md` for overall strategy and principles.


## Goal
Add validation functions for module actions. This includes upfront validation for `scope: "original"` actions and incremental validation for `scope: "shim"` actions.

## Changes

### 1. Add Validation Functions (`src/serger/module_actions.py`)
```python
def validate_module_actions(
    actions: list[ModuleActionFull],
    original_modules: set[str],
    detected_packages: set[str],
    *,
    scope: ModuleActionScope | None = None,
) -> None:
    """
    Validate module actions upfront.
    
    For scope: "original" actions, validates against original module tree.
    For scope: "shim" actions, validates incrementally (call after each action).
    
    Raises ValueError for invalid operations.
    """

def validate_action_source_exists(
    action: ModuleActionFull,
    available_modules: set[str],
) -> None:
    """Validate that action source exists in available modules."""

def validate_action_dest(
    action: ModuleActionFull,
    existing_modules: set[str],
) -> None:
    """Validate action destination (conflicts, required for move/copy, etc.)."""

def validate_no_circular_moves(
    actions: list[ModuleActionFull],
) -> None:
    """Validate no circular move operations."""

def validate_no_conflicting_operations(
    actions: list[ModuleActionFull],
) -> None:
    """Validate no conflicting operations (delete then move, etc.)."""
```

### 2. Validation Rules
1. **Source exists**: `source` must exist in available modules
2. **Dest conflicts**: `dest` must not conflict with existing (unless `action: "copy"`)
3. **Circular moves**: No circular move chains
4. **Delete conflicts**: Can't delete something being moved/copied
5. **Invalid dest for delete**: `dest` must not be present for `delete`
6. **Missing dest for move/copy**: `dest` required for `move`/`copy`

### 3. Validation Strategy
- **Upfront validation** (for `scope: "original"`):
  - Validate all actions at once
  - Check sources exist in original module tree
  - Check for circular moves
  - Check for conflicting operations
  
- **Incremental validation** (for `scope: "shim"`):
  - Validate each action after previous actions are applied
  - Check source exists in current transformed state
  - Check dest doesn't conflict with current state

### 4. Add Tests
- `tests/5_core/test_module_actions.py`: Test validation functions
  - Test source doesn't exist → error
  - Test dest conflicts → error (unless copy)
  - Test circular moves → error
  - Test delete conflicts → error
  - Test invalid dest for delete → error
  - Test missing dest for move/copy → error
  - Test upfront validation for scope: "original"
  - Test incremental validation for scope: "shim"
  - Test validation passes for valid actions

## Notes
- Validation functions are ready but not yet called from stitch logic
- Functions handle both upfront and incremental validation
- Clear error messages for all validation failures

## Testing
- Run `poetry run poe check:fix` - must pass
- Comprehensive tests for all validation rules
- Test both upfront and incremental validation

## Review and Clarifying Questions

**After implementing this iteration**, review the changes and document any questions that arise:

1. **Review the implementation**:
   - Check that validation functions handle all edge cases correctly
   - Verify upfront validation works for `scope: "original"` actions
   - Verify incremental validation works for `scope: "shim"` actions
   - Check that error messages are clear and helpful
   - Verify validation catches all invalid operations (circular moves, conflicts, etc.)

2. **Document any questions**:
   - Are there edge cases in validation that need clarification?
   - Are there validation scenarios that are ambiguous?
   - Are there any inconsistencies with existing code patterns?
   - Should validation be more strict or more lenient in certain cases?

3. **Resolve before proceeding**:
   - Answer all questions before moving to iteration 07
   - Update implementation if needed
   - Update iteration 07 plan if decisions affect it

**Questions to consider**:
- How should we handle validation when a module is deleted then moved in the same action list?
- Should we validate that `dest` paths are valid module names (no invalid characters)?
- Are there any performance concerns with upfront validation for large action lists?

## Commit Message
```
feat(module_actions): add validation functions

- Add validate_module_actions() for upfront validation
- Add validate_action_source_exists() to check source exists
- Add validate_action_dest() to check dest conflicts
- Add validate_no_circular_moves() to detect circular operations
- Add validate_no_conflicting_operations() to detect conflicts
- Support both upfront (scope: "original") and incremental (scope: "shim") validation
- Add comprehensive validation tests
- Not yet integrated into stitch logic (coming in later iteration)
```

