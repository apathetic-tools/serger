# Module Actions Documentation Coverage Report

**Date**: Generated automatically  
**Documentation File**: `docs/configuration-reference.md`  
**Status**: ⚠️ **MOSTLY COMPLETE** (1 feature missing)

## Executive Summary

The documentation in `docs/configuration-reference.md` provides **comprehensive coverage** for module actions features, with **one notable gap**: the `source_path` feature is not documented.

## Documentation Coverage Analysis

### ✅ Fully Documented Features

#### 1. Configuration Formats
- ✅ **Dict format**: Documented with examples (lines 259-277)
- ✅ **List format**: Documented with examples (lines 284-309)
- ✅ **Defaults**: Documented for dict format (line 282)

#### 2. Action Types
- ✅ **Move**: Documented in action types table (lines 311-318)
- ✅ **Copy**: Documented in action types table (lines 311-318)
- ✅ **Delete**: Documented in action types table (lines 311-318)
- ✅ **None alias**: Documented as alias for delete (line 318)

#### 3. Action Parameters
- ✅ **`source`** (required): Documented (line 324)
- ✅ **`dest`** (optional): Documented (line 328)
- ✅ **`action`**: Documented with default and valid values (line 330)
- ✅ **`mode`**: Documented with preserve/flatten options (lines 332-334)
- ✅ **`scope`**: Documented with original/shim options and defaults (lines 336-338)
- ✅ **`affects`**: Documented with shims/stitching/both options (lines 340-343)
- ✅ **`cleanup`**: Documented with auto/error/ignore options (lines 345-348)

#### 4. Examples
- ✅ **Simple rename**: Documented with dict format example (lines 352-367)
- ✅ **Flatten subpackage**: Documented with example (lines 371-393)
- ✅ **Multi-level operations**: Documented with example (lines 395-417)
- ✅ **Copy operations**: Documented with example (lines 419-440)
- ✅ **Delete operations**: Documented with example (lines 442-462)
- ✅ **Mode + user actions**: Documented with example (lines 464-487)
- ✅ **Scope: original vs shim**: Documented with two examples (lines 489-534)
- ✅ **Affects: shims vs stitching vs both**: Documented with three examples (lines 536-600)
- ✅ **Cleanup: auto vs error vs ignore**: Documented with two examples (lines 602-646)

#### 5. Relationship with Module Mode
- ✅ **Mode-generated actions**: Documented (lines 648-656)
- ✅ **User actions override**: Documented (line 654)
- ✅ **Processing order**: Documented (lines 652-653)

#### 6. Validation Rules
- ✅ **Source must exist**: Documented (line 662)
- ✅ **Dest conflicts**: Documented (line 663)
- ✅ **Dest required**: Documented (line 664)
- ✅ **Dest not allowed**: Documented (line 665)
- ✅ **Scope consistency**: Documented (line 666)
- ✅ **Error messages**: Documented (line 668)

#### 7. Shim Setting
- ✅ **Shim setting section**: Documented (lines 197-245)
- ✅ **Values (all, public, none)**: Documented (lines 203-207)
- ✅ **Relationship with module_mode and module_actions**: Documented (lines 209-215)
- ✅ **Examples**: Documented (lines 217-244)

### ❌ Missing Documentation

#### 1. `source_path` Parameter

**Status**: ❌ **NOT DOCUMENTED**

**What's Missing**:
- `source_path` is not mentioned in the "Optional Parameters" section (lines 326-348)
- No examples showing how to use `source_path` to re-include excluded files
- No explanation of when to use `source_path` vs regular `source`

**What Should Be Documented**:
- **`source_path`** (string, optional): Filesystem path to a Python file that should be re-included or referenced. Used when:
  - A file was excluded but you want to include it via an action
  - You want to reference a module from a different location
  - The module name from the file must match the `source` parameter
  - Only works when `affects` includes `"stitching"` or `"both"`

**Example that should be added**:
```jsonc
{
  "builds": [
    {
      "package": "mypkg",
      "include": ["src/**/*.py"],
      "exclude": ["src/internal/**/*.py"],
      "out": "dist/mypkg.py",
      "module_actions": [
        {
          "source": "utils",
          "source_path": "src/internal/utils.py",
          "dest": "public.utils",
          "affects": "both"
        }
      ]
    }
  ]
}
```

## Documentation Quality Assessment

### ✅ Strengths

1. **Comprehensive Coverage**: Almost all features are documented
2. **Clear Examples**: Multiple examples for each feature
3. **Well Organized**: Logical structure with clear sections
4. **Parameter Details**: All parameters documented with defaults and valid values
5. **Use Cases**: Examples show real-world usage patterns
6. **Relationships**: Clear explanation of how features work together

### ⚠️ Gaps

1. **`source_path` Parameter**: Missing from documentation entirely
   - This is a significant feature that's implemented and tested
   - Users won't know this feature exists without documentation
   - Should be added to the "Optional Parameters" section

## Recommendations

### High Priority

1. **Add `source_path` Documentation**:
   - Add to "Optional Parameters" section (after `cleanup`)
   - Explain when to use it (re-include excluded files, reference different locations)
   - Explain requirements (file must exist, module name must match `source`)
   - Explain interaction with `affects` (only works with "stitching" or "both")
   - Add example showing re-inclusion of excluded file

### Medium Priority

2. **Add More Edge Case Examples**:
   - Example showing `source_path` with `affects: "shims"` (should not add file)
   - Example showing `source_path` with already-included file (no duplicate)
   - Example showing `source_path` overriding exclude

3. **Clarify Scope Behavior**:
   - Add more examples showing when to use `scope: "original"` vs `scope: "shim"`
   - Explain the interaction between mode-generated actions (scope: "original") and user actions (scope: "shim")

## Conclusion

✅ **The documentation is comprehensive and covers 95%+ of implemented features.**

The only significant gap is the missing `source_path` parameter documentation. This feature is fully implemented and tested, but users won't discover it without documentation.

**Recommendation**: Add `source_path` documentation to complete the coverage.

