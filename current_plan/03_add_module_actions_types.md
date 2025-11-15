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
- Add `module_actions: list[ModuleActionFull]` to `BuildConfigResolved` (normalized to list format, always present - empty list if not provided)

### 3. Update Config Resolution (`src/serger/config/config_resolve.py`)
- In `resolve_build_config()`, accept `module_actions` from config
- Validate structure (basic validation - full validation comes later):
  - If dict: validate keys are strings, values are strings or None
  - If list: validate each item has `source` key, validate action types using `literal_to_set()` for Literal types
- Store in `BuildConfigResolved` (normalized to list format, always set to empty list `[]` if not provided)

### 4. Add Tests
- `tests/5_core/test_config_types.py`: Test type definitions
- `tests/5_core/test_config_resolve.py`: Test `module_actions` acceptance
  - Test dict format is accepted
  - Test list format is accepted
  - Test invalid formats raise errors
  - Test basic structure validation

## Clarifying Questions

**Q1: When should default values be applied to module actions?**
- The design doc mentions defaults for optional fields (action: "move", mode: "preserve", scope: "shim"/"original", affects: "shims", cleanup: "auto").
- **Decision needed**: Should defaults be applied at config resolution time or later when processing actions?
- **Answer**: [To be determined - see iteration 03.5]

**Q2: Should `BuildConfigResolved.module_actions` have all fields present with defaults?**
- `BuildConfigResolved` is a "Resolved" TypedDict, meaning it should have all fields present with final values.
- **Decision needed**: Should all fields be present with defaults, or keep optional fields optional?
- **Answer**: [To be determined - see iteration 03.5]

**Q3: When should `scope` defaults be set?**
- The design doc says user actions default to `scope: "shim"`, mode-generated actions default to `scope: "original"`.
- **Decision needed**: Should we set scope defaults at config resolution or later when we know if actions are mode-generated?
- **Answer**: [To be determined - see iteration 03.5]

**Q4: Should dict format actions have `scope: "shim"` set explicitly?**
- The design doc says dict format defaults to `scope: "shim"` for user actions.
- **Decision needed**: Should we explicitly set `scope: "shim"` when converting dict format to list format?
- **Answer**: [To be determined - see iteration 03.5]

**Q5: When should `dest` validation happen?**
- The design doc says `dest` is required for `move`/`copy`, must not be present for `delete`.
- **Decision needed**: Should we validate this in iteration 04 (config resolution) or later when processing actions?
- **Answer**: [To be determined - see iteration 03.5]

**Q6: Is `source_path` needed in iteration 03/04?**
- The design doc mentions `source_path` for re-including excluded modules.
- **Decision needed**: Should we include `source_path` validation in iteration 04 or defer to later?
- **Answer**: [To be determined - see iteration 03.5]

## Notes
- Types are added but not yet used in stitch logic
- Config is accepted and validated but not parsed/applied yet
- Full parsing logic comes in later iteration
- **Important**: See iteration 03.5 to resolve clarifying questions before proceeding to iteration 04

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

