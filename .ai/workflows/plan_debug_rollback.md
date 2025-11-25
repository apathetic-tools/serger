# Troubleshooting: Isolated Changes from Last Passing Commit

When troubleshooting becomes difficult and you need to isolate the problem, follow this workflow to systematically rebuild changes from the last passing commit, one isolated feature/change at a time.

## Workflow

1. **Create implementation plan**
   - Create a plan file in `.plan/` following the format in `.ai/templates/plan_debug_rollback.tmpl.md`
   - Name it something descriptive like `troubleshooting_YYYYMMDD_description.md`
   - Keep the plan updated as you progress

2. **Identify expected phases/features/changes**
   - Based on the current chat session, list what you think are the phases/features/changes that should be covered since the last breaking commit
   - The last breaking commit is the last time in this chat where all tests passed and you committed
   - Document these in the plan under "Phases/Features/Changes Since Last Passing Commit"

3. **Find the actual last passing commit** (First task)
   - Check git history to find the last commit where tests passed
   - Verify by running `poetry run poe check:fix` at that commit
   - Document the commit hash, message, and date in the plan

4. **Revise the list of changes**
   - Review all commits between the last passing commit and the current state
   - Review any stashed changes
   - Revise the list of phases/features/changes in the plan to reflect both:
     - Commits made since the last passing commit
     - Changes in stashed work
   - Present a summarized point-form list to the user
   - Wait for their response - they may revise your list
   - Update the plan document based on their feedback

5. **Stash current changes** (if not already stashed)
   ```bash
   git stash push -m "WIP: troubleshooting [brief description]"
   ```

6. **Rollback to the last passing commit**
   ```bash
   git reset --hard <last-passing-commit-hash>
   ```

7. **Verify tests pass**
   ```bash
   poetry run poe check:fix
   ```
   Ensure everything passes before proceeding.

8. **Implement changes one at a time**
   - Start with the first feature/change from the approved list
   - Make ONE isolated change
   - Run tests after each change:
     ```bash
     poetry run poe check:fix
     ```
   - **If tests pass**: Update the plan, then ask the user for a checkpoint commit:
     ```bash
     git add <changed-files>
     git commit -m "checkpoint(scope): brief description"
     ```
   - **If tests fail**: Investigate that specific change before proceeding
   - Update the plan document with progress

9. **Repeat** for each feature/change in the approved list

10. **Request regular commit** when the plan is complete
    - Once all phases/features/changes are implemented and tested
    - Ask the user if they want to squash checkpoint commits (per git conventions)
    - Proceed with regular commit

## Plan Maintenance

- **Keep the plan updated**: As you progress, update the plan document with:
  - Current phase and task
  - Completion status of tasks
  - Any notes or observations
  - Timestamp of last update

- **Checkpoint commits**: After each isolated feature/change that passes tests, request a checkpoint commit before moving to the next item

## Benefits

- **Isolates the problem**: You'll know exactly which change caused the issue
- **Maintains clean history**: Each passing change is committed separately
- **Easier debugging**: Smaller, focused changes are easier to understand and fix
- **Prevents compound issues**: Multiple changes can interact in unexpected ways
- **Clear documentation**: The plan provides a clear record of what was done

## When to Use This Workflow

- When you've made multiple changes and tests are failing
- When you're unsure which change caused the problem
- When troubleshooting has become difficult and you need a systematic approach
- When you want to ensure each change is independently correct

