# Start Here: Module Actions Implementation

I'm implementing the Module Actions feature for serger. The implementation plan is in `current_plan/` with 14 iterations.

**Start with Iteration 01**: `current_plan/01_rename_shim_mode_to_module_mode.md`

**Context**:
- See `current_plan/00_overview.md` for the overall strategy and principles
- See `current_plan/plan_module_actions_design.md` for the complete design reference
- See `current_plan/coverage_validation.md` to verify all features are covered

**Important principles**:
- Each iteration must pass `poetry run poe check:fix` before committing
- Preserve code that will be needed later, even if not called yet
- Add unit tests for each section as we go
- Follow the iteration file exactly - it has all the details

Please implement Iteration 01: Rename `shim_mode` → `module_mode`.

