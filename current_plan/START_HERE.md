# Start Here: Module Actions Implementation

**Next iteration**: All `source_path` issues resolved. Module actions implementation is complete.

**Context**:
- See `current_plan/00_overview.md` for overall strategy and principles
- See `current_plan/plan_module_actions_design.md` for complete design reference

**Important principles**:
- Each iteration must pass `poetry run poe check:fix` before committing
- Add unit tests for each section as we go
- **Review at end of iteration** - document any clarifying questions before proceeding

**Completed**: Iterations 01, 02, 03, 03.5, 04, 05, 06, 07, 08, 09, 10, 11, 12, 12.5, 12.6, 13, 14, 14.5, 14.6, 14.7, 15, 16, 16.1, 16.2 ✓

**Iteration 16.1 Summary**: Fixed remaining `source_path` issues. Updated test source names from `"internal.utils"` to `"utils"` to match actual module names at build time (package root is `tmp_path`, not `src/internal`). Fixed `module.public` accessibility when imported via `importlib` by restructuring the shim code to always set the attribute on the current module object (using `sys.modules.get(__name__)`) regardless of whether the root package exists, ensuring `module.public` works when the file is imported via `importlib.util.spec_from_file_location()`. All three previously failing tests now pass.

**Iteration 16.2 Summary**: Fixed `detect_runtime_mode()` to correctly detect standalone mode when the script is loaded via `importlib` in test mode. Updated the function to check multiple locations for `__STANDALONE__`: current module's globals, package module (`serger`), and `__main__` module. Also updated the runtime swap to remove `apathetic_utils` modules from `sys.modules` before loading the standalone script, ensuring all modules are loaded from the standalone script when `RUNTIME_MODE=singlefile`. The test `test_pytest_runtime_cache_integrity` now passes in both installed and singlefile modes.
