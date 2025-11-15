# Start Here: Module Actions Implementation

I'm implementing the Module Actions feature for serger. The implementation plan is in `current_plan/` with 14 iterations.

**Start with Iteration 05**: `current_plan/05_create_module_actions_parsing.md`

**Context**:
- See `current_plan/00_overview.md` for the overall strategy and principles
- See `current_plan/plan_module_actions_design.md` for the complete design reference
- See `current_plan/coverage_validation.md` to verify all features are covered

**Important principles**:
- Each iteration must pass `poetry run poe check:fix` before committing
- Preserve code that will be needed later, even if not called yet
- Add unit tests for each section as we go
- **Update documentation as we go** - each iteration includes documentation updates that must be completed as part of that step
- Follow the iteration file exactly - it has all the details
- **Review at end of iteration** - After implementing changes, review for ambiguous decisions, edge cases, or unclear behavior. Document any clarifying questions and resolve them before proceeding to the next iteration (see `current_plan/00_overview.md` for details)

**Completed**:
- Iteration 01 - Rename `shim_mode` → `module_mode` ✓
- Iteration 02 - Add `shim` setting types ✓
- Iteration 03 - Add `module_actions` types ✓
- Iteration 03.5 - Resolve clarifying questions ✓
- Iteration 04 - Validate and normalize `module_actions` config ✓
- Iteration 05 - Create `module_actions.py` with parsing functions ✓

**Current status**:
- `ModuleActionType`, `ModuleActionMode`, `ModuleActionScope`, `ModuleActionAffects`, `ModuleActionCleanup` literal types added
- `ModuleActionFull` TypedDict with all optional fields added
- `ModuleActionSimple` and `ModuleActions` union types added
- `module_actions` field added to `BuildConfig`, `RootConfig`, and `BuildConfigResolved`
- `BuildConfigResolved.module_actions` is always present (empty list `[]` if not provided)
- Full validation and normalization implemented in `_validate_and_normalize_module_actions()`:
  - Dict format converted to list format with all defaults applied
  - List format validated and normalized with all defaults applied
  - `source` validated as non-empty string
  - `dest` validated based on action type (required for move/copy, not allowed for delete)
  - `action` validated and normalized ("none" → "delete")
  - `mode`, `scope`, `affects`, `cleanup` validated if present
  - `source_path` validated as non-empty string if present (basic validation)
  - All defaults applied: `action: "move"`, `mode: "preserve"`, `scope: "shim"`, `affects: "shims"`, `cleanup: "auto"`
- Comprehensive tests added for all validation cases
- Created `src/serger/module_actions.py` with `set_mode_generated_action_defaults()` helper function:
  - Sets defaults for mode-generated actions: `action: "move"`, `mode: "preserve"`, `scope: "original"` (always), `affects: "shims"`, `cleanup: "auto"`
  - Always sets `scope: "original"` for mode-generated actions (per Q3 decision)
  - Preserves existing fields (except scope which is always overridden)
  - Does not mutate input action
- Comprehensive unit tests added in `tests/5_core/test_module_actions.py`
- All checks passing (`poetry run poe check:fix`)

**Next step**: Iteration 06 - Add validation functions (upfront and incremental).

**Iteration 03.5 complete**: All clarifying questions have been answered. See `current_plan/03.5_resolve_clarifying_questions.md` for the full decisions.

**Key decisions from iteration 03.5** (affect implementation):
- **Q1/Q2**: Defaults applied at config resolution time - all fields present in `BuildConfigResolved`
- **Q3**: User actions get `scope: "shim"` at config resolution; mode-generated actions set `scope: "original"` when created
- **Q4**: Dict format explicitly sets `scope: "shim"` when converting
- **Q5**: `dest` validation happens in iteration 04 (upfront validation)
- **Q6**: `source_path` handling deferred to later iteration (basic validation only for now)
- **Q7**: `shim: "public"` accepted as valid but treated same as `"all"` for now
