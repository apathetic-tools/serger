# checkfix

Run `poetry run poe check:fix` and iteratively fix all errors until the check passes completely.

## Behavior

1. Run `poetry run poe check:fix` to check for and auto-fix issues
2. If errors remain after auto-fix, analyze and fix them manually
3. Continue iterating until `poetry run poe check:fix` passes with exit code 0
4. Fix ALL errors, even if they seem unrelated to the current task
5. If you encounter an error you cannot fix or are unsure how to fix, stop and ask the user for guidance

## Important Notes

- Do not skip errors that seem unrelated - fix everything
- The goal is a completely clean `poetry run poe check:fix` run
- If stuck or uncertain about a fix, ask the user rather than guessing
- This command should be thorough and complete
- CI will not pass if any errors remain and code cannot be pushed

