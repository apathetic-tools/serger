# Coverage Validation: Plan vs Iterations

This document validates that all items in `plan_module_actions_design.md` are covered in the iteration steps.

## Section 0: Feature Naming and Shim Setting

### 0.1. Decision: Feature Renamed to Module Actions
- ✅ **Covered in**: Iteration 01 (rename `shim_mode` → `module_mode`)
- ✅ **Covered in**: Iteration 03 (add `module_actions` types)

### 0.2. Decision: Shim Setting
- ✅ **Covered in**: Iteration 02 (add `shim` setting types)
- ✅ **Covered in**: Iteration 10 (integrate `shim` setting into stitch logic)

## Section 1: Configuration Location

- ✅ **Covered in**: Iteration 03 (add `module_actions` to config types)
- ✅ **Covered in**: Iteration 04 (validate and resolve config)

## Section 2: Action Types

- ✅ **Covered in**: Iteration 03 (add `ModuleActionType` with `move`, `copy`, `delete`, `none`)
- ✅ **Covered in**: Iteration 07 (implement action application functions)

## Section 3: Flattening Mode

- ✅ **Covered in**: Iteration 03 (add `ModuleActionMode` with `preserve`, `flatten`)
- ✅ **Covered in**: Iteration 07 (implement preserve/flatten logic in `_apply_move_action`)

## Section 4: Configuration Format

- ✅ **Covered in**: Iteration 03 (add `ModuleActionSimple` and `ModuleActions` union types)
- ✅ **Covered in**: Iteration 04 (validate dict and list formats)
- ✅ **Covered in**: Iteration 05 (parse and normalize dict format to list format)

## Section 5: Processing Order

- ✅ **Covered in**: Iteration 08 (generate actions from mode)
- ✅ **Covered in**: Iteration 10 (integrate into stitch.py with correct order)

## Section 6: Relationship to `module_mode`

- ✅ **Covered in**: Iteration 08 (create `generate_actions_from_mode()`)
- ✅ **Covered in**: Iteration 10 (combine mode-generated and user actions)

### 6.1. Decision: Keep Both Keys, Modes Generate Actions
- ✅ **Covered in**: Iteration 08 (mode-to-actions conversion)
- ✅ **Covered in**: Iteration 10 (prepend mode-generated actions to user actions)

## Section 7: Action Scope

### 7.1. Decision: Configurable Scope with Smart Defaults
- ✅ **Covered in**: Iteration 03 (add `ModuleActionScope` type)
- ✅ **Covered in**: Iteration 05 (set default scope: "original" for mode-generated, "shim" for user)
- ✅ **Covered in**: Iteration 10 (separate actions by scope, apply in order)
- ✅ **Covered in**: Iteration 11 (refine scope handling and validation timing)

## Section 8: Validation Rules

- ✅ **Covered in**: Iteration 06 (add validation functions)
  - Source doesn't exist → `validate_action_source_exists()`
  - Dest conflicts → `validate_action_dest()`
  - Circular moves → `validate_no_circular_moves()`
  - Delete conflicts → `validate_no_conflicting_operations()`
  - Invalid dest for delete → validation in `_normalize_module_actions()`
  - Missing dest for move/copy → validation in `_normalize_module_actions()`

### Validation Timing
- ✅ **Covered in**: Iteration 06 (upfront validation for scope: "original")
- ✅ **Covered in**: Iteration 11 (incremental validation for scope: "shim")

## Section 9: Implementation Details

### 9.1. Action Processing Functions
- ✅ **Covered in**: Iteration 05 (`parse_module_actions()`)
- ✅ **Covered in**: Iteration 06 (`validate_module_actions()`)
- ✅ **Covered in**: Iteration 07 (`apply_module_actions()`, `apply_single_action()`)
- ✅ **Covered in**: Iteration 08 (`generate_actions_from_mode()`)

### 9.2. Name Transformation Logic
- ✅ **Covered in**: Iteration 07 (`_transform_module_name()`, `_apply_move_action()` with preserve/flatten)
- ✅ **Covered in**: Iteration 07 (`_apply_copy_action()`, `_apply_delete_action()`)

### 9.3. Package Path Creation
- ✅ **Covered in**: Iteration 07 (note: handled by existing `_create_pkg_module` logic)

### 9.4. Integration Point
- ✅ **Covered in**: Iteration 10 (full integration flow in `_build_final_script()`)

## Section 10: Type Definitions

- ✅ **Covered in**: Iteration 03 (all type definitions)
  - `ModuleActionType`, `ModuleActionMode`, `ModuleActionScope`
  - `ModuleActionAffects`, `ModuleActionCleanup`
  - `ModuleActionFull`, `ModuleActionSimple`, `ModuleActions`
- ✅ **Covered in**: Iteration 03 (add to `BuildConfig`, `RootConfig`, `BuildConfigResolved`)

## Section 11: Examples

- ✅ **Covered in**: Iteration 13 (update documentation with examples)
- ✅ **Covered in**: Iteration 14 (integration tests verify examples work)

## Section 12: Testing Strategy

### Unit Tests
- ✅ **Covered in**: Iterations 05-09 (unit tests for each function)
  - Parsing (Iteration 05)
  - Validation (Iteration 06)
  - Application (Iteration 07)
  - Mode-to-actions (Iterations 08-09)

### Integration Tests
- ✅ **Covered in**: Iteration 14 (comprehensive integration tests)

## Section 13: Documentation

- ✅ **Covered in**: Iteration 13 (update `configuration-reference.md`)

## Section 14: Compatibility with Existing Code

- ✅ **Covered in**: Iteration 01 (rename maintains compatibility)
- ✅ **Covered in**: Iteration 10 (module_mode behavior preserved through action generation)

## Section 15: Code Organization

- ✅ **Covered in**: Iteration 05 (create `module_actions.py`)
- ✅ **Covered in**: Iterations 03, 04 (update config files)
- ✅ **Covered in**: Iteration 10 (update `stitch.py`)
- ✅ **Covered in**: Iteration 13 (update documentation)

## Section 16: Edge Cases

- ✅ **Covered in**: Iteration 06 (validation handles edge cases)
- ✅ **Covered in**: Iteration 07 (application functions handle edge cases)
- ✅ **Covered in**: Iteration 14 (integration tests cover edge cases)

## Section 17: Glob Pattern Support

- ✅ **Covered in**: Plan (explicitly deferred - not in initial implementation)
- ✅ **Covered in**: Iteration 13 (documentation notes future phases)
- ✅ **Note**: This is intentionally not in iterations (future work)

## Section 18: Module Actions and Include/Exclude Relationship

- ✅ **Covered in**: Iteration 03 (add `affects` key to types)
- ✅ **Covered in**: Iteration 12 (implement `affects` and `cleanup` handling)
  - Configurable `affects` key
  - Module-to-file mapping
  - File selection logic
  - Cleanup behavior (auto/error/ignore)

## Section 19: Specifying Filesystem Paths in Actions

- ✅ **Covered in**: Iteration 03 (add `source_path` to `ModuleActionFull`)
- ✅ **Covered in**: Iteration 04 (validate `source_path` in config resolution)
- ✅ **Covered in**: Iteration 12 (implement `source_path` handling in affects/cleanup logic)

## Section 20: Future Considerations

- ✅ **Covered in**: Plan (explicitly marked as future work)
- ✅ **Note**: These are intentionally not in iterations (future enhancements)

## Summary

✅ **All sections covered**: Every section in `plan_module_actions_design.md` is covered in at least one iteration step.

✅ **No gaps identified**: All features, decisions, and requirements are addressed.

✅ **Future work clearly marked**: Sections 17 and 20 are explicitly deferred and documented.

## Notes

- Some features span multiple iterations (e.g., types added early, implementation later)
- Integration tests come at the end (Iteration 14) but unit tests are added incrementally
- Documentation is updated in Iteration 13 with the complete end goal
- The plan serves as the design reference, iterations are the implementation steps

