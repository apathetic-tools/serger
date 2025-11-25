# ci

Use GitHub CLI (`gh`) to check CI status, view failing runs, and examine build errors.

## Behavior

1. Use `gh` commands to check status and view failing runs
2. Examine error messages
3. Analyze to understand failures
4. Diagnose and fix issues
5. Provide guidance if needed

## Commands

- `gh run list` - Recent runs
- `gh run view <run-id>` - Run details
- `gh run view <run-id> --log` - Logs
- `gh run list --status failure` - Failed runs only
- `gh run watch` - Watch latest run

## Workflow

1. `gh run list` - Check recent runs
2. Identify failures (❌ or failed status)
3. `gh run view <run-id>` - View details
4. `gh run view <run-id> --log` or `--log-failed` - Examine logs
5. Analyze errors for root cause
6. Fix locally or provide recommendations

## Notes

- Check most recent failing run first
- Look for test/linting errors in logs
- Compare with local `poetry run poe check:fix` if available
- Examine full log if unclear
- Check multiple failed runs if issue persists

