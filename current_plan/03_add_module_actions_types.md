# Iteration 03: Add `module_actions` Types

> **Context**: See `current_plan/00_overview.md` for overall strategy and principles.

## Goal
Add all type definitions for `module_actions` configuration. This includes the full TypedDict structure and union types.

## Changes

### 1. Add Type Definitions (`src/serger/config/config_types.py`)
```python
ModuleActionType = Literal["move", "copy", "delete", "none"]
ModuleActionMode = Literal["preserve", "flatten"]
ModuleActionScope = Literal["original", "shim"]
ModuleActionAffects = Literal["shims", "stitching", "both"]
ModuleActionCleanup = Literal["auto", "error", "ignore"]

class ModuleActionFull(TypedDict, total=False):
    source: str  # required
    source_path: NotRequired[str]  # optional filesystem path
    dest: NotRequired[str]  # required for move/copy
    action: NotRequired[ModuleActionType]  # default: "move"
    mode: NotRequired[ModuleActionMode]  # default: "preserve"
    scope: NotRequired[ModuleActionScope]  # default: "shim" for user, "original" for mode-generated
    affects: NotRequired[ModuleActionAffects]  # default: "shims"
    cleanup: NotRequired[ModuleActionCleanup]  # default: "auto"

# Simple format: dict[str, str | None]
ModuleActionSimple = dict[str, str | None]

# Union type for config
ModuleActions = ModuleActionSimple | list[ModuleActionFull]
```

### 2. Add to Config Types
- Add `module_actions: NotRequired[ModuleActions]` to `BuildConfig`
- Add `module_actions: NotRequired[ModuleActions]` to `RootConfig`
- Add `module_actions: NotRequired[list[ModuleActionFull]]` to `BuildConfigResolved` (normalized to list format)

### 3. Update Config Resolution (`src/serger/config/config_resolve.py`)
- In `resolve_build_config()`, accept `module_actions` from config
- Validate structure (basic validation - full validation comes later):
  - If dict: validate keys are strings, values are strings or None
  - If list: validate each item has `source` key, validate action types
- Store in `BuildConfigResolved` (normalized to list format, but don't parse yet)

### 4. Add Tests
- `tests/5_core/test_config_types.py`: Test type definitions
- `tests/5_core/test_config_resolve.py`: Test `module_actions` acceptance
  - Test dict format is accepted
  - Test list format is accepted
  - Test invalid formats raise errors
  - Test basic structure validation

## Notes
- Types are added but not yet used in stitch logic
- Config is accepted and validated but not parsed/applied yet
- Full parsing logic comes in later iteration

## Testing
- Run `poetry run poe check:fix` - must pass
- New tests for type definitions and config acceptance
- Existing tests should still pass

## Commit Message
```
feat(config): add module_actions type definitions

- Add ModuleActionType, ModuleActionMode, ModuleActionScope, etc.
- Add ModuleActionFull TypedDict with all optional fields
- Add ModuleActionSimple and ModuleActions union types
- Add module_actions to BuildConfig, RootConfig, BuildConfigResolved
- Add basic validation in config resolution
- Add tests for type definitions and config acceptance
- Not yet parsed or applied (coming in later iteration)
```

