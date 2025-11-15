# Start Here: Module Actions Implementation

I'm implementing the Module Actions feature for serger. The implementation plan is in `current_plan/` with 14 iterations.

**Start with Iteration 04**: `current_plan/04_validate_module_actions_config.md`

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

**Completed**:
- Iteration 01 - Rename `shim_mode` → `module_mode` ✓
- Iteration 02 - Add `shim` setting types ✓
- Iteration 03 - Add `module_actions` types ✓

**Current status**:
- `ModuleActionType`, `ModuleActionMode`, `ModuleActionScope`, `ModuleActionAffects`, `ModuleActionCleanup` literal types added
- `ModuleActionFull` TypedDict with all optional fields added
- `ModuleActionSimple` and `ModuleActions` union types added
- `module_actions` field added to `BuildConfig`, `RootConfig`, and `BuildConfigResolved`
- `BuildConfigResolved.module_actions` is always present (empty list `[]` if not provided)
- Basic validation in config resolution implemented (dict/list format validation, action type validation)
- Tests added for type definitions and config acceptance
- All checks passing (`poetry run poe check:fix`)

**Next step**: Iteration 03.5 - Resolve clarifying questions before proceeding to iteration 04.

Several clarifying questions were identified during review of iterations 01-03 that should be answered before implementing iteration 04. These questions affect design decisions around default values, validation timing, and implementation approach.

Please review and answer the questions in `current_plan/03.5_resolve_clarifying_questions.md`, then update the implementation plan accordingly before proceeding to iteration 04.

