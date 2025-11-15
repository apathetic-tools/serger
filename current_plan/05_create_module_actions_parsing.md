# Iteration 05: Create `module_actions.py` with Parsing Functions

## Goal
Create the core `module_actions.py` file with parsing and normalization functions. This code will be used later but is not yet integrated.

## Changes

### 1. Create New File (`src/serger/module_actions.py`)
```python
"""Module actions processing for renaming, moving, copying, and deleting modules."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from serger.config.config_types import ModuleActionFull, ModuleActions

def parse_module_actions(
    module_actions: ModuleActions | None,
) -> list[ModuleActionFull]:
    """
    Parse and normalize module_actions config to internal format.
    
    Converts dict format to list format and sets defaults.
    Returns empty list if module_actions is None or empty.
    """
    # Implementation here

def _normalize_dict_format(
    actions_dict: dict[str, str | None],
) -> list[ModuleActionFull]:
    """Convert dict format to list format."""
    # Implementation here

def _set_action_defaults(
    action: ModuleActionFull,
    is_mode_generated: bool = False,
) -> ModuleActionFull:
    """
    Set default values for action fields.
    
    - action: default "move"
    - mode: default "preserve"
    - scope: default "original" for mode-generated, "shim" for user actions
    - affects: default "shims"
    - cleanup: default "auto"
    """
    # Implementation here
```

### 2. Implementation Details
- `parse_module_actions()`:
  - Handle None/empty input
  - If dict format, convert to list
  - If list format, validate structure
  - Set defaults for all optional fields
  - Return normalized list
  
- `_normalize_dict_format()`:
  - Convert `{"old": "new"}` → `[{"source": "old", "dest": "new", ...}]`
  - Convert `{"old": None}` → `[{"source": "old", "action": "delete", ...}]`
  - Set appropriate defaults
  
- `_set_action_defaults()`:
  - Set `action: "move"` if not specified
  - Set `mode: "preserve"` if not specified
  - Set `scope: "original"` if `is_mode_generated=True`, else `"shim"`
  - Set `affects: "shims"` if not specified
  - Set `cleanup: "auto"` if not specified

### 3. Add Tests
- `tests/5_core/test_module_actions.py`: Test parsing functions
  - Test `parse_module_actions()` with None/empty
  - Test dict format parsing
  - Test list format parsing
  - Test default value setting
  - Test mode-generated vs user action defaults (scope)
  - Test that all fields are properly set

## Notes
- This code is not yet called from stitch.py
- Functions are ready to be used when integration happens
- All parsing logic is centralized here

## Testing
- Run `poetry run poe check:fix` - must pass
- Comprehensive unit tests for all parsing functions
- Test edge cases (empty dict, empty list, etc.)

## Commit Message
```
feat(module_actions): add parsing and normalization functions

- Create src/serger/module_actions.py
- Add parse_module_actions() to normalize config to internal format
- Add _normalize_dict_format() to convert dict to list format
- Add _set_action_defaults() to set default values
- Add comprehensive unit tests
- Not yet integrated into stitch logic (coming in later iteration)
```

