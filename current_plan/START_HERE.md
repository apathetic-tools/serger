# Start Here: Module Actions Implementation

**Next iteration**: Iteration 08 - `current_plan/08_create_mode_to_actions_conversion.md`

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

**Completed**: Iterations 01, 02, 03, 03.5, 04, 05, 06, 07 ✓

**Key decisions** (from iteration 03.5):
- Defaults applied at config resolution - all fields present in `BuildConfigResolved`
- User actions: `scope: "shim"` at config resolution
- Mode-generated actions: `scope: "original"` when created (via `set_mode_generated_action_defaults()`)
- Validation functions ready in `src/serger/module_actions.py` (not yet integrated)
- Action application functions ready in `src/serger/module_actions.py` (not yet integrated)
