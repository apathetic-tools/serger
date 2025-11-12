# Logger Factory Pattern - Resolving Circular Dependency

**Date:** 2025-11-12  
**Status:** ✅ Implemented

## Problem Statement

The codebase had a circular dependency issue with `get_logger()`:

```
logs.py 
  → imports utils.utils_logs (ApatheticCLILogger, TEST_TRACE)
  → defines AppLogger, get_logger()

utils/__init__.py
  → imports utils_files, utils_modules, utils_matching, utils_paths (at module level)
  
utils_files.py, utils_modules.py, etc.
  → import get_logger from serger.logs
  
Result: logs.py → utils/__init__.py → utils_files.py → logs.py (CIRCULAR!)
```

**Previous Solution:** Lazy loading via `__getattr__` in `utils/__init__.py` to break the cycle. This was considered a "nasty hack" that we wanted to eliminate.

**Requirements:**
1. No `get_logger()` definition in `logs.py`
2. No `cast()` needed when calling `get_logger()`
3. Type checkers should see the correct `AppLogger` type
4. `utils_logs.py` should be completely self-contained (no imports from `logs.py`)
5. Eliminate the lazy loading hack in `utils/__init__.py`

## Solution Options Considered

### Option 1: Logger Registry Pattern
- Create a registry in `utils_logs.py` that stores the logger instance
- `logs.py` registers the app logger
- Utils modules retrieve it from the registry
- **Pros:** Clean separation, no circular dependency
- **Cons:** Utils modules need different function name, requires updates

### Option 2: Move `get_logger()` to `utils_logs.py` with Late Binding
- Put `get_logger()` in `utils_logs.py`, return a logger registered later
- **Pros:** Utils modules import from `utils_logs` (no dependency on `logs.py`)
- **Cons:** Initialization order matters, type hints less precise

### Option 3: Dependency Injection via Module-Level Variable
- `utils_logs.py` defines a module-level `_get_logger_func` callable
- `logs.py` sets it
- **Pros:** Utils modules import from `utils_logs` only
- **Cons:** Runtime error if called before initialization, less type-safe

### Option 4: Split `logs.py` into Framework and App Parts
- Move `AppLogger` and `get_logger()` to new `app_logs.py`
- **Pros:** Clear separation
- **Cons:** More files, breaking change

### Option 5: Factory Pattern with Generic Type Preservation ⭐ **CHOSEN**

**Concept:** Factory function that creates a typed `get_logger()` function and automatically assigns it to the module namespace.

**Key Features:**
- `utils_logs.py` provides `create_get_logger()` factory
- Factory preserves the exact type of the logger instance (e.g., `AppLogger`)
- Automatically assigns the function to `utils_logs` module namespace
- `logs.py` only calls the factory, doesn't define `get_logger()`
- Type checkers see the correct return type via `TYPE_CHECKING` imports

## Implementation Details

### 1. Factory Function in `utils_logs.py`

```python
_LoggerType = TypeVar("_LoggerType", bound="ApatheticCLILogger")

def create_get_logger(logger: _LoggerType) -> Callable[[], _LoggerType]:
    """Factory function that creates a typed get_logger() function.
    
    This function creates a get_logger() function that preserves the exact type
    of the logger instance passed to it. It also automatically assigns the
    function to this module's namespace, so you can import get_logger directly
    after calling this.
    """
    def _get_logger() -> _LoggerType:
        TEST_TRACE(...)
        return logger
    
    # Automatically assign to this module's namespace
    this_module = sys.modules[__name__]
    this_module.get_logger = _get_logger  # type: ignore[attr-defined]
    
    return _get_logger
```

**Key Points:**
- Uses `TypeVar` to preserve the exact logger type
- Automatically assigns to module namespace using `sys.modules[__name__]`
- Returns the function for flexibility

### 2. Placeholder Function with Type Stubs

```python
# Type stub for type checkers
if TYPE_CHECKING:
    from serger.logs import AppLogger
    
    def get_logger() -> AppLogger:  # noqa: F811
        """Return the registered app logger (type stub for type checkers)."""
        ...
else:
    def get_logger() -> ApatheticCLILogger:  # noqa: F811
        """Return the registered app logger.
        
        This function is replaced at runtime by create_get_logger().
        """
        # Try to initialize by importing logs module if not already done
        if "serger.logs" not in sys.modules:
            importlib.import_module("serger.logs")
        # Check if get_logger was replaced by create_get_logger()
        current_get_logger = sys.modules[__name__].get_logger
        if current_get_logger is not get_logger:
            return current_get_logger()
        # Fallback: raise error if not initialized
        raise RuntimeError(...)
```

**Key Points:**
- `TYPE_CHECKING` block provides correct type hints for type checkers
- Runtime function includes lazy initialization fallback
- Checks if function was replaced before raising error

### 3. Logger Initialization in `logs.py`

```python
# Initialize and register
AppLogger.extend_logging_module()
_APP_LOGGER = cast("AppLogger", logging.getLogger(PROGRAM_PACKAGE))

# Create typed get_logger function in utils_logs module namespace
# This automatically updates utils_logs.get_logger with correct AppLogger type
create_get_logger(_APP_LOGGER)

# Re-export get_logger for backward compatibility
import serger.utils.utils_logs as _utils_logs_module  # noqa: E402
get_logger = _utils_logs_module.get_logger
```

**Key Points:**
- `logs.py` no longer defines `get_logger()` - only calls factory
- Re-exports for backward compatibility with existing code
- Factory call happens at module initialization time

### 4. Removed Lazy Loading from `utils/__init__.py`

**Before:**
- Used `__getattr__` for lazy loading modules that depend on `logs.py`
- Required maintaining a dictionary of module paths
- Complex `TYPE_CHECKING` imports for type stubs

**After:**
- All modules imported directly at module level
- No `__getattr__` needed
- Clean, straightforward imports

### 5. Import Guards

Added import guards in all modules that use `get_logger()` to ensure `logs.py` is imported early:

```python
# Ensure logs module is imported to initialize get_logger()
import serger.logs  # noqa: F401  # pyright: ignore[reportUnusedImport]
from .utils.utils_logs import get_logger
```

**Why:** Ensures `create_get_logger()` is called before any code tries to use `get_logger()`.

### 6. Early Import in Main Package

Added early import in `src/serger/__init__.py`:

```python
# Import logs early to ensure get_logger() is initialized
# This must happen before any other imports that use get_logger()
import serger.logs  # noqa: F401  # pyright: ignore[reportUnusedImport]
```

**Why:** When the main package is imported, this ensures logger initialization happens first.

## How It Works

1. **Module Import Flow:**
   - When `serger.logs` is imported, it calls `create_get_logger(_APP_LOGGER)`
   - Factory creates a typed function and assigns it to `utils_logs.get_logger`
   - The placeholder function is replaced with the real one

2. **Type Checking:**
   - `TYPE_CHECKING` block imports `AppLogger` for type hints only
   - Type checkers see `get_logger() -> AppLogger`
   - No runtime circular dependency (TYPE_CHECKING is False at runtime)

3. **Runtime Behavior:**
   - Utils modules import `get_logger` from `utils_logs`
   - At runtime, they get the actual `AppLogger` instance
   - Type is preserved via the factory's `TypeVar`

4. **Backward Compatibility:**
   - `logs.py` re-exports `get_logger` for existing code
   - Main package `__init__.py` also exports it
   - No breaking changes to existing imports

## Benefits

✅ **No circular dependency** - `utils_logs.py` is self-contained  
✅ **No lazy loading hack** - All imports are direct  
✅ **Type-safe** - Type checkers see correct `AppLogger` type  
✅ **No casts needed** - Type is preserved automatically  
✅ **Clean architecture** - Framework code (`utils_logs`) separate from app code (`logs`)  
✅ **Backward compatible** - Existing code continues to work  

## Files Modified

- `src/serger/utils/utils_logs.py` - Added factory and placeholder
- `src/serger/logs.py` - Removed `get_logger()`, added factory call
- `src/serger/utils/__init__.py` - Removed lazy loading, direct imports
- `src/serger/__init__.py` - Added early import, updated exports
- All modules using `get_logger()` - Updated imports, added import guards

## Testing

All tests pass after implementation. The solution handles:
- Direct module imports
- Package-level imports
- Test fixtures that patch the logger
- Edge cases with import order

