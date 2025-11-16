# Iteration 15: Implement `source_path` Feature
> **Context**: See `current_plan/00_overview.md` for overall strategy and principles.

## Goal
Complete the implementation of the `source_path` key in module actions to allow re-including excluded modules or referencing modules from different locations. This enables actions to reference files that weren't included initially or were excluded.

## Background

The `source_path` field was added to `ModuleActionFull` TypedDict in iteration 03 and has basic validation in iteration 04, but the functionality to actually use it to re-include files is not yet implemented. According to `plan_module_actions_design.md` Section 19, this feature should:

- Allow referencing modules that weren't included initially or were excluded
- Validate file exists and is parseable
- Extract module name from file (must match `source` or be derivable)
- Add file to stitching set if `affects` includes "stitching"
- Handle edge cases (path doesn't exist, module name mismatch, already included, conflicts with exclude)

## Changes

### 1. Enhance `source_path` Validation (`src/serger/config/config_resolve.py`)

Update `_validate_and_normalize_module_actions()` to add full validation for `source_path`:

- Validate `source_path` is a valid filesystem path (if present)
- Check that file exists (if `affects` includes "stitching")
- Validate file is parseable Python (basic check - must have `.py` extension)
- Extract module name from file and verify it matches `source` (or can be derived from it)
- Store resolved absolute path in normalized action

**Implementation details**:
```python
# In _validate_and_normalize_module_actions(), when processing list format:
if "source_path" in action:
    source_path_val = action["source_path"]
    # ... existing basic validation (non-empty string) ...
    
    # Resolve to absolute path
    source_path_resolved = Path(source_path_val).resolve()
    
    # Validate file exists (if affects includes "stitching")
    affects_val = action.get("affects", "shims")
    if "stitching" in affects_val or affects_val == "both":
        if not source_path_resolved.exists():
            msg = (
                f"module_actions[{idx}]['source_path'] file does not exist: "
                f"{source_path_resolved}"
            )
            raise ValueError(msg)
        
        # Validate is Python file
        if source_path_resolved.suffix != ".py":
            msg = (
                f"module_actions[{idx}]['source_path'] must be a Python file "
                f"(.py extension), got: {source_path_resolved}"
            )
            raise ValueError(msg)
        
        # Extract module name from file and verify it matches source
        # Use derive_module_name() from utils_modules.py
        # Verify source matches or can be derived from file's module name
```

**Note**: Module name extraction and matching logic should use existing `derive_module_name()` function from `serger.utils.utils_modules`.

### 2. Add Helper Function for Module Name Extraction (`src/serger/module_actions.py`)

Add a helper function to extract and validate module name from `source_path`:

```python
def extract_module_name_from_source_path(
    source_path: Path,
    package_root: Path,
    expected_source: str,
) -> str:
    """Extract module name from source_path and verify it matches expected_source.
    
    Args:
        source_path: Path to Python file
        package_root: Root directory for module name derivation
        expected_source: Expected module name from action source field
    
    Returns:
        Extracted module name
    
    Raises:
        ValueError: If module name doesn't match expected_source or file is invalid
    """
```

**Implementation**:
- Use `derive_module_name()` from `serger.utils.utils_modules` to get module name from file
- Compare with `expected_source` (must match exactly or be derivable)
- Handle edge cases (package root is file's parent, etc.)

### 3. Update File Collection Logic (`src/serger/build.py`)

Update `run_build()` to collect files from `source_path` when `affects` includes "stitching":

**Location**: After `collect_included_files()` and before filtering by `exclude_paths`

**Implementation**:
```python
# After collect_included_files() and before exclude_paths filtering
included_files, file_to_include = collect_included_files(includes, excludes)

# Collect files from source_path in module_actions
module_actions = build_cfg.get("module_actions", [])
source_path_files: set[Path] = set()
for action in module_actions:
    if "source_path" in action:
        affects_val = action.get("affects", "shims")
        if "stitching" in affects_val or affects_val == "both":
            source_path_str = action["source_path"]
            source_path_resolved = Path(source_path_str).resolve()
            
            # Validate file exists (should have been validated in config resolution)
            if not source_path_resolved.exists():
                # This should not happen if validation worked, but check anyway
                msg = (
                    f"source_path file does not exist: {source_path_resolved}. "
                    f"This should have been caught during config validation."
                )
                raise ValueError(msg)
            
            source_path_files.add(source_path_resolved)
            
            # Add to file_to_include if not already present
            if source_path_resolved not in file_to_include:
                # Create a synthetic IncludeResolved for this file
                # Use the file's parent directory as root
                synthetic_include: IncludeResolved = {
                    "path": str(source_path_resolved),
                    "root": source_path_resolved.parent,
                    "origin": "code",  # Mark as code-generated
                }
                file_to_include[source_path_resolved] = synthetic_include

# Merge source_path files into included_files
all_included_files = sorted(set(included_files) | source_path_files)
```

**Important**: `source_path` files should be added to the file set **after** initial collection but **before** `exclude_paths` filtering, so they override excludes.

### 4. Update Stitching Logic (`src/serger/stitch.py`)

Ensure `stitch_modules()` handles `source_path` files correctly:

- Files from `source_path` should be included in `file_paths` passed to `stitch_modules()`
- Module name derivation should work correctly for `source_path` files
- Actions should be able to reference modules from `source_path` files

**Note**: Most of this should work automatically if files are added to `file_paths` in `run_build()`, but verify:
- Module name derivation works for `source_path` files
- Actions can match modules from `source_path` files
- No duplicate processing of files that are both included and in `source_path`

### 5. Handle Edge Cases

#### 5.1. Already Included Files
- If a file specified in `source_path` is already in the include set, use existing behavior (no duplicate)
- Log a debug message indicating the file was already included

#### 5.2. Conflicts with Exclude
- `source_path` should override exclude for that specific file
- File should be included even if it matches an exclude pattern
- Log a debug message indicating exclude was overridden

#### 5.3. Module Name Mismatch
- If extracted module name doesn't match `source`, raise `ValueError` with clear message
- Allow for package name differences (e.g., file has `internal.utils` but `source` is `utils` if package is `internal`)
- Document expected matching rules

#### 5.4. Path Resolution
- Resolve `source_path` relative to config root (if relative)
- Handle absolute paths correctly
- Validate path is within project boundaries (optional security check)

### 6. Add Tests

#### 6.1. Unit Tests (`tests/5_core/test_module_actions.py` or new file)

Add tests for `extract_module_name_from_source_path()`:
- Test module name extraction from file
- Test module name matching with expected source
- Test error cases (file doesn't exist, not Python file, name mismatch)

#### 6.2. Integration Tests (`tests/9_integration/test_module_actions_integration.py`)

Add comprehensive integration tests:
- Test re-including excluded file via `source_path`
- Test referencing file not in initial include set
- Test `affects: "stitching"` with `source_path` adds file to stitching
- Test `affects: "shims"` with `source_path` doesn't add file to stitching
- Test `affects: "both"` with `source_path` adds file to stitching
- Test already included file (no duplicate)
- Test exclude override (file included despite exclude pattern)
- Test module name mismatch error
- Test end-to-end: excluded file → `source_path` action → stitched file → import test

**Example test case**:
```python
def test_source_path_re_includes_excluded_file(tmp_path: Path) -> None:
    """Test that source_path can re-include an excluded file."""
    # Setup: Create file structure
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    internal_dir = src_dir / "internal"
    internal_dir.mkdir()
    utils_file = internal_dir / "utils.py"
    utils_file.write_text('def helper(): pass\n')
    
    # Config: Exclude internal, but re-include via source_path
    config = {
        "package": "mypkg",
        "include": [str(src_dir / "**/*.py")],
        "exclude": [str(internal_dir / "**/*.py")],
        "module_actions": [
            {
                "source": "internal.utils",
                "source_path": str(utils_file),
                "dest": "public.utils",
                "affects": "both",
            }
        ],
        "out": str(tmp_path / "output.py"),
    }
    
    # Run build and verify file is stitched
    # ...
```

### 7. Update Documentation (`docs/configuration-reference.md`)

Add documentation for `source_path` parameter:

- Explain use case (re-including excluded files, referencing files not in include set)
- Document when file is added to stitching (only if `affects` includes "stitching")
- Document validation rules (file must exist, must be Python file, module name must match)
- Provide examples:
  - Re-including excluded file
  - Referencing file from different location
  - Using with `affects: "stitching"` vs `affects: "shims"`

## Notes

- **Validation timing**: Full validation (file existence, module name matching) happens at config resolution time, not at stitch time
- **File collection**: Files from `source_path` are added to the file set in `run_build()`, before exclude filtering
- **Module name matching**: Must be exact match or derivable (e.g., if package is `internal` and file has module `internal.utils`, `source` can be `internal.utils` or just `utils` if context allows)
- **Performance**: File existence and module name extraction happen once at config resolution, not during stitching
- **Backward compatibility**: `source_path` is optional, so existing configs continue to work

## Testing

- Run `poetry run poe check:fix` - must pass
- Comprehensive tests for all `source_path` scenarios
- Test edge cases (already included, exclude override, name mismatch)
- Test with different `affects` values
- End-to-end tests verify files are actually stitched

## Review and Clarifying Questions

**After implementing this iteration**, review the changes and document any questions that arise:

1. **Review the implementation**:
   - Check that `source_path` validation works correctly
   - Verify files are added to stitching set when `affects` includes "stitching"
   - Check that module name matching works correctly
   - Verify edge cases are handled (already included, exclude override)
   - Test that files are actually stitched and accessible

2. **Document any questions**:
   - Are there edge cases in module name matching that need clarification?
   - How should we handle files that are both included and in `source_path`?
   - Should `source_path` files be validated against project boundaries?
   - Are there performance concerns with file existence checks?

3. **Resolve before proceeding**:
   - Answer all questions before considering this feature complete
   - Update implementation if needed
   - Update documentation if behavior differs from plan

**Questions to consider**:
- Should `source_path` support glob patterns, or only single files?
- How should we handle relative vs absolute paths in `source_path`?
- Should we validate that `source_path` files are within the project root?
- How should module name matching work for nested packages?

## Commit Message
```
feat(module_actions): implement source_path feature for re-including files

- Add full validation for source_path (file existence, Python file, module name matching)
- Extract module name from source_path files and verify against source
- Add source_path files to stitching set when affects includes "stitching"
- Handle edge cases (already included, exclude override, name mismatch)
- Add helper function extract_module_name_from_source_path()
- Update file collection logic in run_build() to include source_path files
- Add comprehensive tests for source_path functionality
- Update documentation with source_path examples and use cases
```

## Final Step: Update START_HERE.md

After completing this iteration, update `current_plan/START_HERE.md`:
- Mark iteration 15 as completed ✓
- Update the "Current status" section with what was accomplished in this iteration
- Update "Next step" to point to next iteration (if any)
- Include a brief summary of what was done (e.g., "Implemented source_path feature to allow re-including excluded files or referencing files not in include set")

This ensures the next chat session can pick up where this one left off.

