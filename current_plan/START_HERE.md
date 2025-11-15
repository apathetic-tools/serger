# Start Here: Module Actions Implementation

I'm implementing the Module Actions feature for serger. The implementation plan is in `current_plan/` with 14 iterations.

**Start with Iteration 03**: `current_plan/03_add_module_actions_types.md`

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

**Current status**:
- `ShimSetting` type added (`"all" | "public" | "none"`)
- `shim` field added to `BuildConfig`, `RootConfig`, and `BuildConfigResolved`
- Config resolution implemented with cascade and validation using `literal_to_set()`
- Tests added for `shim` setting resolution
- All checks passing (`poetry run poe check:fix`)

Please implement Iteration 03: Add `module_actions` types.

