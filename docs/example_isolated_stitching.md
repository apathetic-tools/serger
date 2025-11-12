# Example: Isolated Module Stitching

## Original Source Files

### `src/mypkg/utils.py`
```python
def helper():
    return "Hello from utils"
```

### `src/mypkg/core.py`
```python
from .utils import helper  # Relative import

def process():
    return helper() + " processed"
```

### `src/mypkg/__main__.py`
```python
from .core import process  # Relative import

def main(args):
    result = process()
    print(result)
    return 0
```

---

## Stitched Output (Isolated Module Approach)

### Approach 1: Direct exec() with __package__ setup

```python
#!/usr/bin/env python3
# My Package
# Version: 1.0.0

import sys
import types

# Create parent package (required for relative imports)
_pkg_root = types.ModuleType('mypkg')
sys.modules['mypkg'] = _pkg_root

# --- Module: mypkg.utils ---
_mod_utils = types.ModuleType('mypkg.utils')
_mod_utils.__package__ = 'mypkg'  # Required for relative imports
sys.modules['mypkg.utils'] = _mod_utils
# Execute module code in its own namespace
exec('''
def helper():
    return "Hello from utils"
''', _mod_utils.__dict__)

# --- Module: mypkg.core ---
_mod_core = types.ModuleType('mypkg.core')
_mod_core.__package__ = 'mypkg'  # Required for relative imports
sys.modules['mypkg.core'] = _mod_core
# Execute module code in its own namespace
# Relative import resolves via __package__ and sys.modules
exec('''
from .utils import helper  # Relative import works!

def process():
    return helper() + " processed"
''', _mod_core.__dict__)

# --- Module: mypkg.__main__ ---
_mod_main = types.ModuleType('mypkg.__main__')
_mod_main.__package__ = 'mypkg'  # Required for relative imports
sys.modules['mypkg.__main__'] = _mod_main
# Execute module code in its own namespace
exec('''
from .core import process  # Relative import works!

def main(args):
    result = process()
    print(result)
    return 0
''', _mod_main.__dict__)

# --- Import shims for single-file runtime ---
# These allow external code to import as if modules were separate
_pkg = 'mypkg'
# Note: In isolated mode, shims point to the individual module objects
sys.modules[f'{_pkg}.utils'] = _mod_utils
sys.modules[f'{_pkg}.core'] = _mod_core
sys.modules[f'{_pkg}.__main__'] = _mod_main
del _pkg

# Make main() accessible at module level for __main__ execution
main = _mod_main.main

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
```

### Approach 2: Helper function with __package__ setup

```python
#!/usr/bin/env python3
# My Package
# Version: 1.0.0

import sys
import types

def _load_module(name: str, code: str, package: str | None = None):
    """Helper to create and execute a module in isolation.
    
    Args:
        name: Full module name (e.g., 'mypkg.core')
        code: Module source code
        package: Package name for relative imports (e.g., 'mypkg')
    """
    mod = types.ModuleType(name)
    if package:
        mod.__package__ = package  # Required for relative imports
    sys.modules[name] = mod
    exec(code, mod.__dict__)
    return mod

# Create parent package (required for relative imports)
_pkg_root = types.ModuleType('mypkg')
sys.modules['mypkg'] = _pkg_root

# --- Module: mypkg.utils ---
_mod_utils = _load_module('mypkg.utils', '''
def helper():
    return "Hello from utils"
''', package='mypkg')

# --- Module: mypkg.core ---
_mod_core = _load_module('mypkg.core', '''
from .utils import helper  # Relative import works!

def process():
    return helper() + " processed"
''', package='mypkg')

# --- Module: mypkg.__main__ ---
_mod_main = _load_module('mypkg.__main__', '''
from .core import process  # Relative import works!

def main(args):
    result = process()
    print(result)
    return 0
''', package='mypkg')

# --- Import shims for single-file runtime ---
_pkg = 'mypkg'
sys.modules[f'{_pkg}.utils'] = _mod_utils
sys.modules[f'{_pkg}.core'] = _mod_core
sys.modules[f'{_pkg}.__main__'] = _mod_main
del _pkg

# Make main() accessible for __main__ execution
main = _mod_main.main

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
```

## Key Requirements for Relative Imports

Both approaches require:

1. **Parent package in sys.modules**: The parent package (`mypkg`) must exist in `sys.modules` before child modules use relative imports
2. **`__package__` attribute**: Each module needs `__package__` set to its parent package name
3. **Module registration order**: Modules must be registered in dependency order (utils before core, core before __main__)

**Why this works:**
- When Python sees `from .utils import helper`, it:
  1. Checks `__package__` (which is `'mypkg'`)
  2. Resolves `.utils` relative to `mypkg` → `mypkg.utils`
  3. Looks up `sys.modules['mypkg.utils']` (which we registered)
  4. Imports `helper` from that module

---

## Key Differences from Current Approach

### Current (Flat Namespace):
```python
# All code in one namespace
def helper():
    return "Hello from utils"

def process():
    return helper() + " processed"  # Direct call, no import needed

def main(args):
    result = process()  # Direct call
    print(result)
    return 0
```

### Proposed (Isolated Modules):
```python
# Each module in its own namespace
_mod_utils = types.ModuleType('mypkg.utils')
sys.modules['mypkg.utils'] = _mod_utils
# ... utils code executes in _mod_utils namespace ...

_mod_core = types.ModuleType('mypkg.core')
sys.modules['mypkg.core'] = _mod_core
from mypkg.utils import helper  # Resolves via sys.modules
# ... core code executes in _mod_core namespace ...
```

---

## Benefits

1. **No name collisions**: Each module has its own namespace
   - `utils.helper()` and `core.helper()` can coexist
   
2. **Natural imports**: Both absolute and relative imports work as expected
   - `from mypkg.utils import helper` (absolute) resolves correctly
   - `from .utils import helper` (relative) resolves correctly with `__package__` set
   
3. **Module isolation**: Each module's globals don't pollute others
   - Variables in `utils.py` aren't visible to `core.py`

4. **Shims still work**: External code can still do `from mypkg.core import process`

