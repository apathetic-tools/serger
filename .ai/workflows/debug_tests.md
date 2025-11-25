# Debugging Failing Tests

When tests are failing and standard debugging approaches aren't sufficient, use these troubleshooting techniques to get visibility into what's happening.

## When to Use This Workflow

- Tests are failing and you need more visibility
- Standard debugging (print statements, basic logging) isn't sufficient
- You need to see execution flow or variable values during test execution
- Logging output is being captured by pytest and not visible
- The logging system itself might be broken

## Troubleshooting Techniques

### 1. Set LOG_LEVEL=test

The `test` log level is the most verbose and bypasses pytest's log capture, allowing you to see all TRACE and DEBUG logs even when tests fail.

**Usage:**
```bash
LOG_LEVEL=test poetry run poe test:pytest:installed tests/path/to/test.py::test_name -xvs
```

**What it does:**
- Sets the logger to the most verbose level (TEST level)
- Bypasses pytest's log capture system
- Shows all TRACE and DEBUG logs in the output
- Useful for seeing detailed execution flow

**When to use:**
- When you need to see detailed logging output during test execution
- When pytest's capture is hiding important log messages
- When you want to trace execution flow through the code

### 2. Add Copious logger.trace() Statements

Add `logger.trace()` statements throughout the code to trace execution flow and variable values during debugging.

**Usage:**
```python
logger.trace("Entering function with param=%r", param)
logger.trace("Variable state: x=%s, y=%s", x, y)
logger.trace("Exiting function with result=%r", result)
```

**What it does:**
- Provides detailed execution trace
- Shows variable values at key points
- Helps identify where execution diverges from expected path

**When to use:**
- When you need to trace execution flow
- When you need to see variable values at specific points
- When you're not sure which code path is being taken

**Best practices:**
- Add traces at function entry/exit points
- Trace important variable values
- Trace decision points (if/else branches)
- Trace loop iterations for small loops
- Use descriptive messages that explain context

### 3. Use safe_trace() for Unavailable Logging

When logging is not available or captured even with `LOG_LEVEL=test`, use `apathetic_logging.safe_trace()`. This writes directly to `sys.__stderr__` and bypasses all logging frameworks and capture systems.

**Usage:**
```python
from apathetic_logging import safe_trace

safe_trace("label", value1, value2, icon="🔍")
```

**What it does:**
- Writes directly to `sys.__stderr__`
- Bypasses all logging frameworks
- Bypasses pytest's capture system
- Works even when logging system is broken

**When to use:**
- Pre-logging framework initialization debugging
- When pytest's capture is interfering even with `LOG_LEVEL=test`
- When the logging system itself might be broken
- When you need guaranteed output visibility

**Use cases:**
- Debugging module-level code that runs before logging is initialized
- When pytest's capture is too aggressive
- When logging handlers aren't configured correctly
- Emergency debugging when nothing else works

### 4. Create Custom Trace Functions with make_safe_trace()

Use `apathetic_logging.make_safe_trace(icon)` to create custom trace functions with specific icons for easier visual scanning.

**Usage:**
```python
from apathetic_logging import make_safe_trace

trace = make_safe_trace("🔍")
trace("Entering function", param1, param2)

trace_data = make_safe_trace("📊")
trace_data("Data state", data_dict)

trace_error = make_safe_trace("❌")
trace_error("Error occurred", error_details)
```

**What it does:**
- Creates a trace function with a custom icon
- Makes it easier to visually scan output for specific types of traces
- Provides consistent icon usage throughout debugging

**When to use:**
- When you want to categorize different types of traces
- When you need to visually distinguish trace types in output
- When debugging complex flows with multiple trace points

**Icon suggestions:**
- 🔍 - General investigation/tracing
- 📊 - Data state inspection
- ⚙️ - Configuration/setup
- ❌ - Error conditions
- ✅ - Success conditions
- 🔄 - Loop iterations
- 🎯 - Key decision points

### 5. Enable safe_trace() Output with SAFE_TRACE Environment Variable

Enable `safe_trace()` output by setting the `SAFE_TRACE` environment variable. This is required because `safe_trace()` is disabled by default.

**Usage:**
```bash
SAFE_TRACE=1 poetry run poe test:pytest:installed tests/path/to/test.py::test_name -xvs
```

**Combined with LOG_LEVEL=test:**
```bash
LOG_LEVEL=test SAFE_TRACE=1 poetry run poe test:pytest:installed tests/path/to/test.py::test_name -xvs
```

**What it does:**
- Enables `safe_trace()` output (it's disabled by default)
- Works in combination with `LOG_LEVEL=test` for maximum visibility
- Provides both logging and safe_trace output

**When to use:**
- When you've added `safe_trace()` calls but don't see output
- When you need both logging and safe_trace visibility
- When you want maximum debugging output

## Workflow: Systematic Debugging Approach

1. **Start with standard debugging**
   - Add print statements or basic logging
   - Check test output for obvious errors

2. **If standard debugging isn't enough, try LOG_LEVEL=test**
   ```bash
   LOG_LEVEL=test poetry run poe test:pytest:installed tests/path/to/test.py::test_name -xvs
   ```
   - This often reveals hidden logging output

3. **Add logger.trace() statements**
   - Add traces at key points in the code
   - Trace variable values and execution flow
   - Re-run tests with `LOG_LEVEL=test`

4. **If logging is still not visible, use safe_trace()**
   - Add `safe_trace()` calls at critical points
   - Enable with `SAFE_TRACE=1`
   - Use custom icons for different trace types

5. **Combine techniques for maximum visibility**
   ```bash
   LOG_LEVEL=test SAFE_TRACE=1 poetry run poe test:pytest:installed tests/path/to/test.py::test_name -xvs
   ```

## Common Scenarios

### Scenario: Test fails but no error message is clear
- **Solution**: Use `LOG_LEVEL=test` to see detailed logging
- **Add**: `logger.trace()` statements around the failing code path

### Scenario: Logging output is being captured by pytest
- **Solution**: Use `LOG_LEVEL=test` to bypass capture
- **If still captured**: Use `safe_trace()` with `SAFE_TRACE=1`

### Scenario: Need to debug code before logging is initialized
- **Solution**: Use `safe_trace()` - it works before logging is set up
- **Enable**: Set `SAFE_TRACE=1` environment variable

### Scenario: Complex execution flow is hard to follow
- **Solution**: Add `logger.trace()` at key decision points
- **Enhance**: Use `make_safe_trace()` with different icons for different trace types
- **Run**: With `LOG_LEVEL=test` to see all traces

### Scenario: Variable values are unexpected
- **Solution**: Add `logger.trace()` to log variable values
- **Use**: `safe_trace()` if logging isn't visible
- **Pattern**: Trace before and after operations that modify variables

## Tips

- **Remove traces after debugging**: Don't leave debugging traces in committed code
- **Use meaningful labels**: Make trace messages descriptive
- **Trace systematically**: Don't add random traces - trace key execution points
- **Combine techniques**: Often using multiple techniques together provides the best visibility
- **Start simple**: Try `LOG_LEVEL=test` first before adding traces

## When to Escalate

If after using all these techniques you're still stuck:
1. Review the troubleshooting workflow in `.ai/workflows/plan_debug_rollback.md` for isolated changes approach
2. Consider making a checkpoint commit (see `.ai/workflows/checkpoint_commit.md`) and continuing in a new chat

