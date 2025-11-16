# Start Here: Module Actions Implementation

**Next iteration**: Iteration 13 - `current_plan/13_update_documentation.md`

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

**Completed**: Iterations 01, 02, 03, 03.5, 04, 05, 06, 07, 08, 09, 10, 11, 12, 12.5, 12.6 ✓

**Iteration 12 Summary**: Added affects and cleanup handling for module actions. Implemented support for affects key (shims/stitching/both) to control action scope and cleanup key (auto/error/ignore) for shim-stitching mismatches. Added functions to separate actions by affects, track deleted modules, detect mismatches, and apply cleanup behavior. Updated stitch logic to filter files based on affects: stitching actions and apply cleanup after shim generation. Added comprehensive tests. **Note**: 3 tests are failing due to module name derivation issue when package_root is a package directory - see iteration 12.5 for fix.

**Iteration 12.5 Summary**: Fixed module name derivation for shim generation. When package_root is a package directory itself, derive_module_name() was losing the package structure. Fixed by preserving package paths in _original_order_names_for_shims, handling __init__.py special case, and improving mismatch detection logic. Fixed 3 of 4 failing tests.

**Iteration 12.6 Summary**: Fixed delete action matching for shim generation. The issue was that when a detected package (e.g., "pkg1") appeared as the first component in a module name (e.g., "pkg1.module"), the prepending logic incorrectly treated it as a separate package and kept it as-is instead of prepending the package_name. Fixed by checking if the first part is actually a subpackage of package_name (i.e., if it appears as a top-level module in transformed_names) before treating it as a separate package. This ensures that "pkg1.module" becomes "mypkg.pkg1.module" instead of staying as "pkg1.module", allowing delete actions to correctly match shim names via component matching.
