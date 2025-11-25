# checkpoint

Create checkpoint commit now. Stage all changes and commit with `checkpoint(scope): brief description`. For saving progress during debugging - tests don't need to pass.

## Behavior

1. Check modified/added files
2. Stage all changes (or user-specified files)
3. Commit with format: `checkpoint(scope): brief description`
4. **Do NOT run `poetry run poe check:fix`** - intermediate saves only
5. Message should describe current debugging state

## Examples

- `checkpoint(debug): attempt to fix level number resolution issue`
- `checkpoint(test): partial fix for handler configuration tests`
- `checkpoint(logger): debugging custom level registration`

## Notes

- Creates commit immediately - no permission asked
- Intermediate saves - don't need to pass checks
- Still meaningful - describe current state
- Incorporate user context if provided

