# Start Here: Module Actions Implementation

**Next iteration**: Iteration 12.5 - `current_plan/12.5_fix_module_name_derivation_for_shims.md`

**Context**:
- See `current_plan/00_overview.md` for overall strategy and principles
- See `current_plan/plan_module_actions_design.md` for complete design reference
- See `current_plan/coverage_validation.md` to verify all features are covered
- See `current_plan/03.5_resolve_clarifying_questions.md` for key decisions

**Important principles**:
- Each iteration must pass `poetry run poe check:fix` before committing
- Follow the iteration file exactly - it has all the details
- Preserve code that will be needed later, even if not called yet
- Add unit tests for each section as we go
- **Review at end of iteration** - document any clarifying questions before proceeding

**Completed**: Iterations 01, 02, 03, 03.5, 04, 05, 06, 07, 08, 09, 10, 11, 12 ✓
**In Progress**: Iteration 12.5 - Fix module name derivation for shim generation

**Iteration 10 Summary**: Integrated module_actions into stitch logic, replacing shim_mode processing. Actions are now generated from module_mode and combined with user actions, applied in scope order (original first, then shim). Fixed force_flat mode to properly flatten all intermediate levels by generating actions for all first components of multi-level module names.

**Iteration 11 Summary**: Refined scope handling with proper validation timing and action ordering. Improved error messages to include scope information. Added integration tests for scope handling edge cases (incremental validation, mixed scopes, none mode with original scope). Verified that scope: "original" actions are validated upfront and scope: "shim" actions are validated incrementally.

**Iteration 12 Summary**: Added affects and cleanup handling for module actions. Implemented support for affects key (shims/stitching/both) to control action scope and cleanup key (auto/error/ignore) for shim-stitching mismatches. Added functions to separate actions by affects, track deleted modules, detect mismatches, and apply cleanup behavior. Updated stitch logic to filter files based on affects: stitching actions and apply cleanup after shim generation. Added comprehensive tests. **Note**: 3 tests are failing due to module name derivation issue when package_root is a package directory - see iteration 12.5 for fix.

**Iteration 12.5 Summary**: (In Progress) Fix module name derivation for shim generation. When package_root is a package directory itself, derive_module_name() loses the package structure, causing scope validation and cleanup mismatch detection to fail. Need to preserve package paths in _original_order_names_for_shims and improve mismatch detection logic.
