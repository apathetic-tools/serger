# Bug Report: Exclude Pattern Matching Fails for Relative Paths Outside Exclude Root

## Problem Description

When using exclude patterns with relative paths (containing `../`) that reference files outside the exclude root directory, the exclusion matching fails. Patterns that don't start with `**/` are skipped when the file path is outside the exclude root, even if the pattern itself is designed to match those files.

## Root Cause

In `is_excluded_raw()` (around lines 2217-2219), when a file path is outside the exclude root and the pattern doesn't start with `**/`, the pattern matching is skipped entirely:

```python
# If path is outside root and pattern doesn't start with **/, skip
if path_outside_root:
    continue
```

This means patterns like `../../src/**/__init__.py` cannot match files that are outside the exclude root, even though the pattern explicitly uses relative navigation (`../`) to target those files.

## Example Configuration That Fails

Here's a real-world example configuration file that demonstrates the issue:

**File:** `mode_verify/embedded_example/.serger-embeded-example.jsonc`

```jsonc
// mode_verify/embedded_example/.serger-embeded-example.jsonc
// Serger's configuration
// This file defines how to stitch apathetic_logging into a single-file python script

{
    "builds": [
      {
        // Stitching configuration for the main serger package
        "package": "embedded_example",
  
        // Source modules to include in the stitch
        // These are glob patterns relative to the source directory
        "include": [
          "source_to_join/*.py",
          "../../src/apathetic_*/**/*.py"       
        ],
  
        // Files to exclude from stitching
        // These are often development-only or auto-generated utilities
        "exclude": [
          "__pycache__/**",
          "*.pyc",
          "../../src/**/__init__.py",    // ❌ THIS PATTERN DOES NOT WORK
          "**/__main__.py"     // Entry point, not stitched
        ],
  
        // Output file path (relative to project root)
        // This will be the final single-file executable
        "out": "../../dist/embedded_example.py"
      }
    ]
}
```

## Expected Behavior

With the exclude pattern `../../src/**/__init__.py`:
- **Expected:** Files matching `src/**/__init__.py` (relative to project root) should be excluded
- **Expected:** The pattern should match `src/apathetic_logging/__init__.py` even though it's outside the config directory

## Actual Behavior

With the exclude pattern `../../src/**/__init__.py`:
- **Actual:** Files matching `src/**/__init__.py` are **NOT** excluded
- **Actual:** Both `src/apathetic_logging/__init__.py` and `mode_verify/embedded_example/source_to_join/__init__.py` are included in the output
- **Actual:** 15 modules are stitched (should be 13)

## Workaround

Using `**/__init__.py` (without relative path prefix) works correctly:
- **Works:** All `__init__.py` files are excluded regardless of location
- **Works:** 13 modules are stitched (correct)

However, this workaround is less precise - it excludes ALL `__init__.py` files, not just those under a specific directory.

## Technical Details

### Context
- **Config file location:** `mode_verify/embedded_example/.serger-embeded-example.jsonc`
- **Config root (exclude root):** `mode_verify/embedded_example/`
- **Files to exclude:** `src/apathetic_logging/__init__.py` (relative to project root)
- **File path relative to exclude root:** `../../src/apathetic_logging/__init__.py`

### Code Flow
1. Exclude patterns are resolved relative to `config_dir` (line 4114 in `_resolve_excludes`)
2. When checking exclusion, `is_excluded_raw()` is called with:
   - `path`: Absolute path to the file (e.g., `/project/src/apathetic_logging/__init__.py`)
   - `root`: Config directory (e.g., `/project/mode_verify/embedded_example/`)
   - `pattern`: `../../src/**/__init__.py` (as resolved from config)
3. The file path is outside the exclude root, so `path_outside_root = True`
4. The pattern `../../src/**/__init__.py` doesn't start with `**/`, so it's skipped (line 2218-2219)
5. The file is not excluded

### Why `**/__init__.py` Works
Patterns starting with `**/` get special handling (lines 2188-2215):
- They match against the filename directly
- They match against the absolute path
- This works even when the file is outside the exclude root

## Proposed Solution

The exclude pattern matching should handle relative paths (with `../`) that target files outside the exclude root. Possible approaches:

1. **Resolve relative patterns before matching:** When a pattern contains `../`, resolve it relative to the exclude root first, then check if the file path matches the resolved pattern.

2. **Match against absolute paths for relative patterns:** If a pattern starts with `../` or contains relative navigation, try matching it against the absolute file path after resolving the pattern.

3. **Normalize pattern relative to project root:** If the pattern uses `../` to navigate outside the exclude root, compute what it resolves to relative to a common root (like project root), then match against that.

## Test Case

To verify the fix:

1. Use the configuration above with `"../../src/**/__init__.py"` in exclude
2. Run: `python dev/serger.py --config mode_verify/embedded_example/.serger-embeded-example.jsonc`
3. Check output: `grep -E "(=== .*\.__init__ ===)" dist/embedded_example.py`
4. **Expected:** No `__init__.py` files should appear in the output
5. **Expected:** Should stitch 13 modules (not 15)

## Related Code Locations

- `is_excluded_raw()`: `dev/serger.py` lines 2129-2243
- `_resolve_excludes()`: `dev/serger.py` lines 4086-4155
- `collect_included_files()`: `dev/serger.py` lines 6250-6296

