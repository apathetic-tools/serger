# tests/5_core/test_split_imports.py
"""Tests for split_imports function."""

import serger.stitch as mod_stitch


def test_split_imports_external_only() -> None:
    """Should extract external imports."""
    code = """import sys
import json

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(code, ["serger"])
    expected_count = 2
    assert len(imports) == expected_count
    assert "import sys" in "".join(imports)
    assert "import json" in "".join(imports)
    assert "def foo():" in body


def test_split_imports_internal_removed() -> None:
    """Should remove internal imports from body."""
    code = """import sys
from serger.config import Config

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(code, ["serger"])
    assert "import sys" in "".join(imports)
    assert "from serger.config" not in "".join(imports)
    assert "from serger.config" not in body
    assert "def foo():" in body


def test_split_imports_relative_imports() -> None:
    """Should handle relative imports."""
    code = """from .config import Config

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(code, ["serger"])
    assert "from .config" not in "".join(imports)
    assert "from .config" not in body
    assert "def foo():" in body


def test_split_imports_invalid_syntax() -> None:
    """Should handle syntax errors gracefully."""
    code = "this is not valid python }"
    imports, body = mod_stitch.split_imports(code, ["serger"])
    assert imports == []
    assert body == code


def test_split_imports_function_local_external_stays() -> None:
    """Function-local external imports should stay in place."""
    code = """import sys

def load_toml():
    try:
        import tomllib
        return tomllib.load
    except ImportError:
        import tomli
        return tomli.load
"""
    imports, body = mod_stitch.split_imports(code, ["serger"])
    # Module-level import should be hoisted
    assert "import sys" in "".join(imports)
    # Function-local imports should stay in body
    assert "import tomllib" in body
    assert "import tomli" in body
    assert "def load_toml():" in body


def test_split_imports_function_local_internal_removed() -> None:
    """Function-local internal imports should be removed."""
    code = """import sys

def compute_order():
    from .utils import derive_module_name
    return derive_module_name(Path("test.py"), Path("."), None)
"""
    imports, body = mod_stitch.split_imports(code, ["serger"])
    # Module-level import should be hoisted
    assert "import sys" in "".join(imports)
    # Function-local internal import should be removed
    assert "from .utils import" not in body
    assert "derive_module_name" in body  # Usage should remain
    assert "def compute_order():" in body


def test_split_imports_mixed_scenarios() -> None:
    """Test mixed module-level and function-local imports."""
    code = """import json
from pathlib import Path

def func1():
    from .internal import helper
    return helper()

def func2():
    try:
        import external_lib
        return external_lib.do_something()
    except ImportError:
        pass
"""
    imports, body = mod_stitch.split_imports(code, ["serger"])
    # Module-level externals hoisted
    assert "import json" in "".join(imports)
    assert "from pathlib import Path" in "".join(imports)
    # Function-local internal removed
    assert "from .internal import" not in body
    # Function-local external stays
    assert "import external_lib" in body
    assert "def func1():" in body
    assert "def func2():" in body


def test_split_imports_no_move_comment() -> None:
    """Imports with # serger: no-move comment should stay in place."""
    code = """import sys
import json  # serger: no-move
from pathlib import Path

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(code, ["serger"])
    # sys should be hoisted
    assert "import sys" in "".join(imports)
    # json should NOT be hoisted (has no-move comment)
    assert "import json" not in "".join(imports)
    assert "import json  # serger: no-move" in body
    # Path should be hoisted
    assert "from pathlib import Path" in "".join(imports)
    assert "def foo():" in body


def test_split_imports_no_move_comment_variations() -> None:
    """Test various comment format variations."""
    code = """import sys
import json  # serger:no-move
import os  # serger: no-move
import re  # SERGER: NO-MOVE
"""
    imports, body = mod_stitch.split_imports(code, ["serger"])
    # Only sys should be hoisted (no comment)
    assert "import sys" in "".join(imports)
    # All others should stay in place
    assert "import json" not in "".join(imports)
    assert "import os" not in "".join(imports)
    assert "import re" not in "".join(imports)
    assert "import json" in body
    assert "import os" in body
    assert "import re" in body


def test_split_imports_no_move_multiline() -> None:
    """Test no-move comment with multi-line imports."""
    code = """import sys
from pathlib import (
    Path,
    PurePath,  # serger: no-move
)
from typing import Optional
"""
    imports, body = mod_stitch.split_imports(code, ["serger"])
    # sys and Optional should be hoisted
    assert "import sys" in "".join(imports)
    assert "from typing import Optional" in "".join(imports)
    # Path import should stay in place (has no-move comment)
    assert "from pathlib import" not in "".join(imports)
    assert "from pathlib import" in body
    assert "PurePath" in body


def test_split_imports_multi_package_both_internal() -> None:
    """Should treat imports from any stitched package as internal."""
    code = """import sys
from pkg1.module1 import func1
from pkg2.module2 import func2
from external_lib import something
"""
    imports, body = mod_stitch.split_imports(code, ["pkg1", "pkg2"])
    # External imports should be hoisted
    assert "import sys" in "".join(imports)
    assert "from external_lib import something" in "".join(imports)
    # Internal imports from both packages should be removed
    assert "from pkg1.module1" not in "".join(imports)
    assert "from pkg1.module1" not in body
    assert "from pkg2.module2" not in "".join(imports)
    assert "from pkg2.module2" not in body


def test_split_imports_multi_package_cross_package_import() -> None:
    """Cross-package imports should be treated as internal."""
    code = """import sys
from pkg1.utils import helper
from pkg2.core import processor
from pkg1.core import pkg2_utils  # pkg1 importing from pkg2
"""
    imports, body = mod_stitch.split_imports(code, ["pkg1", "pkg2"])
    # External imports should be hoisted
    assert "import sys" in "".join(imports)
    # All internal imports (including cross-package) should be removed
    assert "from pkg1.utils" not in "".join(imports)
    assert "from pkg1.utils" not in body
    assert "from pkg2.core" not in "".join(imports)
    assert "from pkg2.core" not in body
    assert "from pkg1.core" not in "".join(imports)
    assert "from pkg1.core" not in body


def test_split_imports_multi_package_external_stays() -> None:
    """Imports from non-stitched packages should remain external."""
    code = """import sys
from pkg1.module1 import func1
from pkg2.module2 import func2
from pkg3.external import something  # pkg3 not in stitched packages
"""
    imports, body = mod_stitch.split_imports(code, ["pkg1", "pkg2"])
    # External imports should be hoisted
    assert "import sys" in "".join(imports)
    assert "from pkg3.external import something" in "".join(imports)
    # Internal imports should be removed
    assert "from pkg1.module1" not in "".join(imports)
    assert "from pkg1.module1" not in body
    assert "from pkg2.module2" not in "".join(imports)
    assert "from pkg2.module2" not in body


def test_split_imports_three_packages() -> None:
    """Should handle three or more packages correctly."""
    code = """import sys
from pkg1.module1 import func1
from pkg2.module2 import func2
from pkg3.module3 import func3
from external import something
"""
    imports, body = mod_stitch.split_imports(code, ["pkg1", "pkg2", "pkg3"])
    # External imports should be hoisted
    assert "import sys" in "".join(imports)
    assert "from external import something" in "".join(imports)
    # All internal imports should be removed
    assert "from pkg1.module1" not in "".join(imports)
    assert "from pkg1.module1" not in body
    assert "from pkg2.module2" not in "".join(imports)
    assert "from pkg2.module2" not in body
    assert "from pkg3.module3" not in "".join(imports)
    assert "from pkg3.module3" not in body


def test_split_imports_keep_mode_external_stays() -> None:
    """In 'keep' mode, external imports should stay in place."""
    code = """import sys
import json

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="keep")
    # External imports should NOT be collected
    assert len(imports) == 0
    # External imports should remain in body
    assert "import sys" in body
    assert "import json" in body
    assert "def foo():" in body


def test_split_imports_keep_mode_internal_removed() -> None:
    """In 'keep' mode, internal imports should still be removed."""
    code = """import sys
from serger.config import Config

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="keep")
    # External imports should NOT be collected
    assert len(imports) == 0
    # External import should remain in body
    assert "import sys" in body
    # Internal import should be removed
    assert "from serger.config" not in body
    assert "def foo():" in body


def test_split_imports_keep_mode_function_local() -> None:
    """In 'keep' mode, function-local external imports stay in place."""
    code = """import sys

def load_toml():
    try:
        import tomllib
        return tomllib.load
    except ImportError:
        import tomli
        return tomli.load
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="keep")
    # No imports should be collected
    assert len(imports) == 0
    # Module-level import should stay in body
    assert "import sys" in body
    # Function-local imports should stay in body
    assert "import tomllib" in body
    assert "import tomli" in body
    assert "def load_toml():" in body


def test_split_imports_keep_mode_mixed() -> None:
    """In 'keep' mode, mixed imports are handled correctly."""
    code = """import json
from pathlib import Path

def func1():
    from .internal import helper
    return helper()

def func2():
    try:
        import external_lib
        return external_lib.do_something()
    except ImportError:
        pass
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="keep")
    # No imports should be collected
    assert len(imports) == 0
    # Module-level externals stay in body
    assert "import json" in body
    assert "from pathlib import Path" in body
    # Function-local internal removed
    assert "from .internal import" not in body
    # Function-local external stays
    assert "import external_lib" in body
    assert "def func1():" in body
    assert "def func2():" in body


def test_split_imports_top_mode_module_level_hoisted() -> None:
    """In 'top' mode, module-level external imports should be hoisted."""
    code = """import sys
import json
from pathlib import Path

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="top")
    # Module-level external imports should be hoisted
    expected_import_count = 3
    assert len(imports) == expected_import_count
    assert "import sys" in "".join(imports)
    assert "import json" in "".join(imports)
    assert "from pathlib import Path" in "".join(imports)
    # Imports should be removed from body
    assert "import sys" not in body
    assert "import json" not in body
    assert "from pathlib import Path" not in body
    assert "def foo():" in body


def test_split_imports_top_mode_try_block_not_hoisted() -> None:
    """In 'top' mode, imports inside try blocks should NOT be hoisted."""
    code = """import sys

try:
    import json
    result = json.loads('{}')
except ImportError:
    pass
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="top")
    # Module-level import should be hoisted
    assert "import sys" in "".join(imports)
    # Import inside try block should NOT be hoisted
    assert "import json" not in "".join(imports)
    assert "import json" in body
    assert "try:" in body


def test_split_imports_top_mode_if_block_not_hoisted() -> None:
    """In 'top' mode, imports inside if blocks should NOT be hoisted."""
    code = """import sys

if some_condition:
    import json
    result = json.loads('{}')
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="top")
    # Module-level import should be hoisted
    assert "import sys" in "".join(imports)
    # Import inside if block should NOT be hoisted
    assert "import json" not in "".join(imports)
    assert "import json" in body
    assert "if some_condition:" in body


def test_split_imports_top_mode_type_checking_hoisted() -> None:
    """In 'top' mode, imports inside 'if TYPE_CHECKING:' should be hoisted."""
    code = """import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Optional
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="top")
    # All imports should be hoisted (TYPE_CHECKING is not a conditional)
    assert "import sys" in "".join(imports)
    assert "from pathlib import Path" in "".join(imports)
    assert "from typing import Optional" in "".join(imports)
    # Imports should be removed from body
    assert "from pathlib import Path" not in body
    assert "from typing import Optional" not in body


def test_split_imports_top_mode_nested_conditional_not_hoisted() -> None:
    """In 'top' mode, imports inside nested conditionals should NOT be hoisted."""
    code = """import sys

if condition1:
    if condition2:
        import json
        result = json.loads('{}')
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="top")
    # Module-level import should be hoisted
    assert "import sys" in "".join(imports)
    # Import inside nested if blocks should NOT be hoisted
    assert "import json" not in "".join(imports)
    assert "import json" in body
    assert "if condition1:" in body
    assert "if condition2:" in body


def test_split_imports_top_mode_try_in_if_not_hoisted() -> None:
    """In 'top' mode, imports in try blocks within if blocks should NOT be hoisted."""
    code = """import sys

if some_condition:
    try:
        import json
        result = json.loads('{}')
    except ImportError:
        pass
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="top")
    # Module-level import should be hoisted
    assert "import sys" in "".join(imports)
    # Import inside try/if should NOT be hoisted
    assert "import json" not in "".join(imports)
    assert "import json" in body


def test_split_imports_top_mode_function_local_not_hoisted() -> None:
    """In 'top' mode, function-local external imports should NOT be hoisted."""
    code = """import sys

def load_toml():
    try:
        import tomllib
        return tomllib.load
    except ImportError:
        import tomli
        return tomli.load
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="top")
    # Module-level import should be hoisted
    assert "import sys" in "".join(imports)
    # Function-local imports should NOT be hoisted
    assert "import tomllib" not in "".join(imports)
    assert "import tomli" not in "".join(imports)
    # Function-local imports should stay in body
    assert "import tomllib" in body
    assert "import tomli" in body
    assert "def load_toml():" in body


def test_split_imports_top_mode_mixed_scenarios() -> None:
    """In 'top' mode, mixed scenarios should be handled correctly."""
    code = """import sys
from pathlib import Path

if TYPE_CHECKING:
    from typing import Optional

if some_condition:
    import json

try:
    import os
except ImportError:
    pass

def func():
    import re
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="top")
    # Module-level imports should be hoisted
    assert "import sys" in "".join(imports)
    assert "from pathlib import Path" in "".join(imports)
    # TYPE_CHECKING import should be hoisted
    assert "from typing import Optional" in "".join(imports)
    # Conditional imports should NOT be hoisted
    assert "import json" not in "".join(imports)
    assert "import os" not in "".join(imports)
    # Function-local import should NOT be hoisted
    assert "import re" not in "".join(imports)
    # Conditional imports should stay in body
    assert "import json" in body
    assert "import os" in body
    # Function-local import should stay in body
    assert "import re" in body


def test_split_imports_force_top_mode_module_level_hoisted() -> None:
    """In 'force_top' mode, module-level external imports should be hoisted."""
    code = """import sys
import json
from pathlib import Path

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # Module-level external imports should be hoisted
    expected_import_count = 3
    assert len(imports) == expected_import_count
    assert "import sys" in "".join(imports)
    assert "import json" in "".join(imports)
    assert "from pathlib import Path" in "".join(imports)
    # Imports should be removed from body
    assert "import sys" not in body
    assert "import json" not in body
    assert "from pathlib import Path" not in body
    assert "def foo():" in body


def test_split_imports_force_top_mode_try_block_hoisted() -> None:
    """In 'force_top' mode, imports inside try blocks should be hoisted."""
    code = """import sys

try:
    import json
    result = json.loads('{}')
except ImportError:
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # Module-level import should be hoisted
    assert "import sys" in "".join(imports)
    # Import inside try block SHOULD be hoisted (unlike 'top' mode)
    assert "import json" in "".join(imports)
    assert "import json" not in body
    assert "try:" in body


def test_split_imports_force_top_mode_if_block_hoisted() -> None:
    """In 'force_top' mode, imports inside if blocks should be hoisted."""
    code = """import sys

if some_condition:
    import json
    result = json.loads('{}')
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # Module-level import should be hoisted
    assert "import sys" in "".join(imports)
    # Import inside if block SHOULD be hoisted (unlike 'top' mode)
    assert "import json" in "".join(imports)
    assert "import json" not in body
    assert "if some_condition:" in body


def test_split_imports_force_top_mode_type_checking_hoisted() -> None:
    """In 'force_top' mode, imports inside 'if TYPE_CHECKING:' should be hoisted."""
    code = """import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Optional
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # All imports should be hoisted
    assert "import sys" in "".join(imports)
    assert "from pathlib import Path" in "".join(imports)
    assert "from typing import Optional" in "".join(imports)
    # Imports should be removed from body
    assert "from pathlib import Path" not in body
    assert "from typing import Optional" not in body


def test_split_imports_force_top_mode_function_local_not_hoisted() -> None:
    """In 'force_top' mode, function-local external imports should NOT be hoisted."""
    code = """import sys

def load_toml():
    try:
        import tomllib
        return tomllib.load
    except ImportError:
        import tomli
        return tomli.load
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # Module-level import should be hoisted
    assert "import sys" in "".join(imports)
    # Function-local imports should NOT be hoisted
    assert "import tomllib" not in "".join(imports)
    assert "import tomli" not in "".join(imports)
    # Function-local imports should stay in body
    assert "import tomllib" in body
    assert "import tomli" in body
    assert "def load_toml():" in body


def test_split_imports_type_checking_wrapped_when_hoisted() -> None:
    """Imports from 'if TYPE_CHECKING:' should be wrapped in TYPE_CHECKING at top."""
    code = """from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Optional
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # Imports should be wrapped in if TYPE_CHECKING: block
    imports_text = "".join(imports)
    assert "if TYPE_CHECKING:" in imports_text
    assert "from pathlib import Path" in imports_text
    assert "from typing import Optional" in imports_text
    # Body should not have the TYPE_CHECKING block (it's empty)
    assert "if TYPE_CHECKING:" not in body
    assert "from pathlib import Path" not in body


def test_split_imports_type_checking_grouped_together() -> None:
    """Multiple TYPE_CHECKING imports should be grouped in single block."""
    code = """from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

if TYPE_CHECKING:
    from typing import Optional
"""
    imports, _body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # All TYPE_CHECKING imports should be in a single block
    imports_text = "".join(imports)
    # Should have only one if TYPE_CHECKING: block
    assert imports_text.count("if TYPE_CHECKING:") == 1
    assert "from pathlib import Path" in imports_text
    assert "from typing import Optional" in imports_text
    # Both should be inside the same TYPE_CHECKING block
    type_checking_start = imports_text.find("if TYPE_CHECKING:")
    pathlib_pos = imports_text.find("from pathlib import Path")
    optional_pos = imports_text.find("from typing import Optional")
    assert pathlib_pos > type_checking_start
    assert optional_pos > type_checking_start


def test_split_imports_type_checking_with_other_conditions_not_special() -> None:
    """'if TYPE_CHECKING and something:' should be treated as regular conditional."""
    code = """import sys

if TYPE_CHECKING and some_flag:
    import json
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # sys should be hoisted
    assert "import sys" in "".join(imports)
    # json should be hoisted (force_top hoists from conditionals)
    assert "import json" in "".join(imports)
    # But it should NOT be wrapped in TYPE_CHECKING (it's a regular conditional)
    imports_text = "".join(imports)
    assert "if TYPE_CHECKING:" not in imports_text
    # Body should have the conditional block with pass (not removed)
    assert "if TYPE_CHECKING and some_flag:" in body
    assert "pass" in body


def test_split_imports_type_checking_partial_block_kept() -> None:
    """If TYPE_CHECKING block has other code, keep the block."""
    code = """from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    SOME_CONSTANT = 42
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # Import should be hoisted and wrapped in TYPE_CHECKING
    imports_text = "".join(imports)
    assert "if TYPE_CHECKING:" in imports_text
    assert "from pathlib import Path" in imports_text
    # Body should still have the TYPE_CHECKING block with the constant
    assert "if TYPE_CHECKING:" in body
    assert "SOME_CONSTANT = 42" in body
    assert "from pathlib import Path" not in body


def test_split_imports_type_checking_empty_block_removed() -> None:
    """If TYPE_CHECKING block is empty after removing imports, remove it."""
    code = """from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
"""
    imports, _body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # Import should be hoisted
    assert "from pathlib import Path" in "".join(imports)
    # Empty TYPE_CHECKING block should be removed from body
    assert "if TYPE_CHECKING:" not in _body


def test_split_imports_type_checking_multiple_imports_one_block() -> None:
    """Multiple imports in one TYPE_CHECKING block should stay together."""
    code = """from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Optional
    from collections.abc import Iterator
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # All imports should be in a single TYPE_CHECKING block
    imports_text = "".join(imports)
    assert imports_text.count("if TYPE_CHECKING:") == 1
    assert "from pathlib import Path" in imports_text
    assert "from typing import Optional" in imports_text
    assert "from collections.abc import Iterator" in imports_text
    # Body should not have the block
    assert "if TYPE_CHECKING:" not in body


def test_split_imports_type_checking_top_mode() -> None:
    """TYPE_CHECKING imports should be hoisted in 'top' mode too."""
    code = """from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
"""
    imports, _body = mod_stitch.split_imports(code, ["serger"], external_imports="top")
    # Import should be hoisted and wrapped in TYPE_CHECKING
    imports_text = "".join(imports)
    assert "if TYPE_CHECKING:" in imports_text
    assert "from pathlib import Path" in imports_text
    # Body should not have the block
    assert "if TYPE_CHECKING:" not in _body


def test_split_imports_type_checking_mixed_with_regular() -> None:
    """TYPE_CHECKING imports should be separate from regular imports."""
    code = """import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
"""
    imports, _body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    imports_text = "".join(imports)
    # Regular import should be at top level
    assert "import sys" in imports_text
    # TYPE_CHECKING import should be in its own block
    assert "if TYPE_CHECKING:" in imports_text
    assert "from pathlib import Path" in imports_text
    # Regular import should come before TYPE_CHECKING block
    sys_pos = imports_text.find("import sys")
    type_checking_pos = imports_text.find("if TYPE_CHECKING:")
    assert sys_pos < type_checking_pos


def test_split_imports_type_checking_nested_not_special() -> None:
    """Nested TYPE_CHECKING (like 'if TYPE_CHECKING or False:') not special."""
    code = """import sys

if TYPE_CHECKING or False:
    import json
"""
    imports, _body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # sys should be hoisted
    assert "import sys" in "".join(imports)
    # json should be hoisted (force_top)
    assert "import json" in "".join(imports)
    # But NOT wrapped in TYPE_CHECKING (it's not exactly 'if TYPE_CHECKING:')
    imports_text = "".join(imports)
    assert "if TYPE_CHECKING:" not in imports_text


def test_split_imports_empty_conditional_gets_pass() -> None:
    """Empty conditional blocks (not TYPE_CHECKING) should get 'pass' not removed."""
    code = """import sys

if TYPE_CHECKING and some_flag:
    import json
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # Import should be hoisted
    assert "import json" in "".join(imports)
    # Empty conditional should have 'pass' added, not removed
    assert "if TYPE_CHECKING and some_flag:" in body
    assert "pass" in body
    # Check that pass is indented inside the if block
    body_lines = body.splitlines()
    if_line_idx = None
    for i, line in enumerate(body_lines):
        if "if TYPE_CHECKING and some_flag:" in line:
            if_line_idx = i
            break
    assert if_line_idx is not None
    # Next non-empty line should be indented pass
    for i in range(if_line_idx + 1, len(body_lines)):
        line = body_lines[i]
        if line.strip():
            assert line.startswith("    ")  # Indented
            assert "pass" in line
            break


def test_split_imports_empty_try_gets_pass() -> None:
    """Empty try blocks should get 'pass' not removed."""
    code = """import sys

try:
    import json
except ImportError:
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # Import should be hoisted
    assert "import json" in "".join(imports)
    # Empty try should have 'pass' added, not removed
    assert "try:" in body
    assert "pass" in body
    # Check that pass is in the try block
    body_lines = body.splitlines()
    try_line_idx = None
    for i, line in enumerate(body_lines):
        if line.strip() == "try:":
            try_line_idx = i
            break
    assert try_line_idx is not None
    # Next non-empty line should be indented pass
    for i in range(try_line_idx + 1, len(body_lines)):
        line = body_lines[i]
        if line.strip() and not line.strip().startswith("except"):
            assert line.startswith("    ")  # Indented
            assert "pass" in line
            break


def test_split_imports_empty_try_with_finally_gets_pass() -> None:
    """Empty try blocks with finally should get 'pass' not removed."""
    code = """import sys

try:
    import json
finally:
    cleanup()
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # Import should be hoisted
    assert "import json" in "".join(imports)
    # Empty try with finally should have 'pass' added, not removed
    assert "try:" in body
    assert "finally:" in body
    assert "cleanup()" in body
    # Check that pass is in the try block (between try: and finally:)
    body_lines = body.splitlines()
    try_line_idx = None
    finally_line_idx = None
    for i, line in enumerate(body_lines):
        if line.strip() == "try:":
            try_line_idx = i
        elif line.strip() == "finally:":
            finally_line_idx = i
    assert try_line_idx is not None
    assert finally_line_idx is not None
    # Check that pass is between try and finally
    found_pass = False
    for i in range(try_line_idx + 1, finally_line_idx):
        line = body_lines[i]
        if line.strip() == "pass":
            assert line.startswith("    ")  # Indented
            found_pass = True
            break
    assert found_pass, "pass should be added to empty try block"


def test_split_imports_empty_if_gets_pass() -> None:
    """Empty if blocks (not TYPE_CHECKING) should get 'pass' not removed."""
    code = """import sys

if some_condition:
    import json
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # Import should be hoisted
    assert "import json" in "".join(imports)
    # Empty if should have 'pass' added, not removed
    assert "if some_condition:" in body
    assert "pass" in body
    # Check that pass is indented inside the if block
    body_lines = body.splitlines()
    if_line_idx = None
    for i, line in enumerate(body_lines):
        if "if some_condition:" in line:
            if_line_idx = i
            break
    assert if_line_idx is not None
    # Next non-empty line should be indented pass
    for i in range(if_line_idx + 1, len(body_lines)):
        line = body_lines[i]
        if line.strip():
            assert line.startswith("    ")  # Indented
            assert "pass" in line
            break


def test_split_imports_type_checking_still_removed() -> None:
    """Empty TYPE_CHECKING blocks should still be removed (not get pass)."""
    code = """from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # Import should be hoisted
    assert "from pathlib import Path" in "".join(imports)
    # Empty TYPE_CHECKING block should be removed (not have pass added)
    assert "if TYPE_CHECKING:" not in body
    assert "pass" not in body or ("pass" in body and "if TYPE_CHECKING:" not in body)


# ===== force_strip mode tests =====


def test_split_imports_force_strip_module_level_removed() -> None:
    """In 'force_strip' mode, module-level external imports should be removed."""
    code = """import sys
import json
from pathlib import Path

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_strip"
    )
    # No imports should be collected
    assert len(imports) == 0
    # External imports should be removed from body
    assert "import sys" not in body
    assert "import json" not in body
    assert "from pathlib import Path" not in body
    assert "def foo():" in body


def test_split_imports_force_strip_function_local_removed() -> None:
    """In 'force_strip' mode, function-local external imports should be removed."""
    code = """def load_toml():
    try:
        import tomllib
        return tomllib.load
    except ImportError:
        import tomli
        return tomli.load
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_strip"
    )
    # No imports should be collected
    assert len(imports) == 0
    # Function-local imports should be removed
    assert "import tomllib" not in body
    assert "import tomli" not in body
    assert "def load_toml():" in body
    assert "try:" in body


def test_split_imports_force_strip_try_block_removed() -> None:
    """In 'force_strip' mode, imports inside try blocks should be removed."""
    code = """try:
    import json
    result = json.loads('{}')
except ImportError:
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_strip"
    )
    # No imports should be collected
    assert len(imports) == 0
    # Import should be removed
    assert "import json" not in body
    # Try block should remain but with pass added if empty
    assert "try:" in body


def test_split_imports_force_strip_if_block_removed() -> None:
    """In 'force_strip' mode, imports inside if blocks should be removed."""
    code = """if some_condition:
    import json
    result = json.loads('{}')
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_strip"
    )
    # No imports should be collected
    assert len(imports) == 0
    # Import should be removed
    assert "import json" not in body
    # If block should remain
    assert "if some_condition:" in body


def test_split_imports_force_strip_type_checking_removed() -> None:
    """In 'force_strip' mode, imports inside TYPE_CHECKING blocks should be removed."""
    code = """from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Optional
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_strip"
    )
    # No imports should be collected
    assert len(imports) == 0
    # Imports should be removed
    assert "from pathlib import Path" not in body
    assert "from typing import Optional" not in body
    # Empty TYPE_CHECKING block should be removed entirely
    assert "if TYPE_CHECKING:" not in body


def test_split_imports_force_strip_type_checking_multiple_pass_removed() -> None:
    """Empty TYPE_CHECKING block with multiple pass statements should be removed."""
    code = """from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    pass
    pass
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_strip"
    )
    # No imports should be collected
    assert len(imports) == 0
    # Import should be removed
    assert "from pathlib import Path" not in body
    # Empty TYPE_CHECKING block (even with multiple pass) should be removed
    assert "if TYPE_CHECKING:" not in body


def test_split_imports_force_strip_empty_try_gets_pass() -> None:
    """Empty try blocks should get 'pass' added."""
    code = """try:
    import json
except ImportError:
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_strip"
    )
    # No imports should be collected
    assert len(imports) == 0
    # Import should be removed
    assert "import json" not in body
    # Empty try should have 'pass' added
    assert "try:" in body
    assert "pass" in body
    # Check that pass is in the try block
    body_lines = body.splitlines()
    try_line_idx = None
    for i, line in enumerate(body_lines):
        if line.strip() == "try:":
            try_line_idx = i
            break
    assert try_line_idx is not None
    # Next non-empty line should be indented pass
    for i in range(try_line_idx + 1, len(body_lines)):
        line = body_lines[i]
        if line.strip() and not line.strip().startswith("except"):
            assert line.startswith("    ")  # Indented
            assert "pass" in line
            break


def test_split_imports_force_strip_empty_if_gets_pass() -> None:
    """Empty if blocks should get 'pass' added."""
    code = """if some_condition:
    import json
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_strip"
    )
    # No imports should be collected
    assert len(imports) == 0
    # Import should be removed
    assert "import json" not in body
    # Empty if should have 'pass' added
    assert "if some_condition:" in body
    assert "pass" in body
    # Check that pass is indented inside the if block
    body_lines = body.splitlines()
    if_line_idx = None
    for i, line in enumerate(body_lines):
        if "if some_condition:" in line:
            if_line_idx = i
            break
    assert if_line_idx is not None
    # Next non-empty line should be indented pass
    for i in range(if_line_idx + 1, len(body_lines)):
        line = body_lines[i]
        if line.strip():
            assert line.startswith("    ")  # Indented
            assert "pass" in line
            break


def test_split_imports_force_strip_type_checking_with_content_kept() -> None:
    """TYPE_CHECKING block with non-import content should be kept."""
    code = """from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    SOME_CONSTANT = 42
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_strip"
    )
    # No imports should be collected
    assert len(imports) == 0
    # Import should be removed
    assert "from pathlib import Path" not in body
    # TYPE_CHECKING block should remain with constant
    assert "if TYPE_CHECKING:" in body
    assert "SOME_CONSTANT = 42" in body


def test_split_imports_force_strip_type_checking_with_other_condition_kept() -> None:
    """TYPE_CHECKING block with other conditions should be kept."""
    code = """from typing import TYPE_CHECKING

if TYPE_CHECKING and some_flag:
    from pathlib import Path
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_strip"
    )
    # No imports should be collected
    assert len(imports) == 0
    # Import should be removed
    assert "from pathlib import Path" not in body
    # Block should remain with pass added
    assert "if TYPE_CHECKING and some_flag:" in body
    assert "pass" in body


def test_split_imports_force_strip_mixed_internal_external() -> None:
    """In 'force_strip' mode, only external imports should be removed."""
    code = """import sys
from serger.config import Config

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_strip"
    )
    # No imports should be collected
    assert len(imports) == 0
    # External import should be removed
    assert "import sys" not in body
    # Internal import should also be removed (always removed)
    assert "from serger.config" not in body
    assert "def foo():" in body


def test_split_imports_force_strip_nested_conditionals() -> None:
    """In 'force_strip' mode, imports in nested conditionals should be removed."""
    code = """if condition1:
    if condition2:
        import json
        result = json.loads('{}')
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_strip"
    )
    # No imports should be collected
    assert len(imports) == 0
    # Import should be removed
    assert "import json" not in body
    # Nested conditionals should remain
    assert "if condition1:" in body
    assert "if condition2:" in body


def test_split_imports_force_strip_no_move_comment_respected() -> None:
    """In 'force_strip' mode, no-move comments should still be respected."""
    code = """import sys
import json  # serger: no-move
from pathlib import Path
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_strip"
    )
    # No imports should be collected
    assert len(imports) == 0
    # sys should be removed
    assert "import sys" not in body
    # json should stay (has no-move comment)
    assert "import json  # serger: no-move" in body
    # Path should be removed
    assert "from pathlib import Path" not in body


# ===== strip mode tests =====


def test_split_imports_strip_module_level_removed() -> None:
    """In 'strip' mode, module-level external imports should be removed."""
    code = """import sys
import json
from pathlib import Path

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="strip")
    # No imports should be collected
    assert len(imports) == 0
    # External imports should be removed from body
    assert "import sys" not in body
    assert "import json" not in body
    assert "from pathlib import Path" not in body
    assert "def foo():" in body


def test_split_imports_strip_function_local_in_conditional_kept() -> None:
    """In 'strip' mode, function-local imports in conditionals should be kept."""
    code = """def load_toml():
    try:
        import tomllib
        return tomllib.load
    except ImportError:
        import tomli
        return tomli.load
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="strip")
    # No imports should be collected
    assert len(imports) == 0
    # Function-local imports in try blocks should be kept (try is a conditional)
    assert "import tomllib" in body
    assert "import tomli" in body
    assert "def load_toml():" in body
    assert "try:" in body
    assert "return tomllib.load" in body
    assert "return tomli.load" in body


def test_split_imports_strip_function_local_not_in_conditional_removed() -> None:
    """In 'strip' mode, function-local imports not in conditionals are removed."""
    code = """def load_toml():
    import tomllib
    return tomllib.load
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="strip")
    # No imports should be collected
    assert len(imports) == 0
    # Function-local imports not in conditionals should be removed
    assert "import tomllib" not in body
    assert "def load_toml():" in body
    assert "return tomllib.load" in body


def test_split_imports_strip_try_block_kept() -> None:
    """In 'strip' mode, imports inside try blocks should be kept."""
    code = """try:
    import json
    result = json.loads('{}')
except ImportError:
    pass
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="strip")
    # No imports should be collected
    assert len(imports) == 0
    # Import should be kept in try block
    assert "import json" in body
    assert "try:" in body
    assert "result = json.loads('{}')" in body


def test_split_imports_strip_if_block_kept() -> None:
    """In 'strip' mode, imports inside if blocks should be kept."""
    code = """if some_condition:
    import json
    result = json.loads('{}')
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="strip")
    # No imports should be collected
    assert len(imports) == 0
    # Import should be kept in if block
    assert "import json" in body
    assert "if some_condition:" in body
    assert "result = json.loads('{}')" in body


def test_split_imports_strip_type_checking_removed() -> None:
    """In 'strip' mode, imports inside TYPE_CHECKING blocks should be removed."""
    code = """from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Optional
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="strip")
    # No imports should be collected
    assert len(imports) == 0
    # Imports should be removed
    assert "from pathlib import Path" not in body
    assert "from typing import Optional" not in body
    # Empty TYPE_CHECKING block should be removed entirely
    assert "if TYPE_CHECKING:" not in body


def test_split_imports_strip_type_checking_with_content_kept() -> None:
    """In 'strip' mode, TYPE_CHECKING blocks with non-import content are kept."""
    code = """from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    # Some comment
    SOME_CONSTANT = "value"
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="strip")
    # No imports should be collected
    assert len(imports) == 0
    # Import should be removed
    assert "from pathlib import Path" not in body
    # TYPE_CHECKING block should remain with non-import content
    assert "if TYPE_CHECKING:" in body
    assert 'SOME_CONSTANT = "value"' in body


def test_split_imports_strip_mixed_module_and_conditional() -> None:
    """In 'strip' mode, module-level imports removed, conditional ones kept."""
    code = """import sys
import json

if some_condition:
    import os
    result = os.getenv('TEST')

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="strip")
    # No imports should be collected
    assert len(imports) == 0
    # Module-level imports should be removed
    assert "import sys" not in body
    assert "import json" not in body
    # Conditional import should be kept
    assert "import os" in body
    assert "if some_condition:" in body
    assert "result = os.getenv('TEST')" in body
    assert "def foo():" in body


def test_split_imports_strip_nested_conditionals_kept() -> None:
    """In 'strip' mode, imports in nested conditionals should be kept."""
    code = """if condition1:
    if condition2:
        import json
        result = json.loads('{}')
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="strip")
    # No imports should be collected
    assert len(imports) == 0
    # Import should be kept in nested conditionals
    assert "import json" in body
    assert "if condition1:" in body
    assert "if condition2:" in body
    assert "result = json.loads('{}')" in body


def test_split_imports_strip_no_move_comment_respected() -> None:
    """In 'strip' mode, no-move comments should still be respected."""
    code = """import sys
import json  # serger: no-move
from pathlib import Path
"""
    imports, body = mod_stitch.split_imports(code, ["serger"], external_imports="strip")
    # No imports should be collected
    assert len(imports) == 0
    # sys should be removed
    assert "import sys" not in body
    # json should stay (has no-move comment)
    assert "import json  # serger: no-move" in body
    # Path should be removed
    assert "from pathlib import Path" not in body


# ===== internal_imports keep mode tests =====


def test_split_imports_keep_mode_internal_stays() -> None:
    """In 'keep' mode for internal imports, they should stay in place."""
    code = """import sys
from serger.config import Config

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="keep"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal import should remain in body
    assert "from serger.config import Config" in body
    assert "def foo():" in body


def test_split_imports_keep_mode_internal_function_local_stays() -> None:
    """In 'keep' mode, function-local internal imports should stay."""
    code = """import sys

def compute_order():
    from .utils import derive_module_name
    return derive_module_name(Path("test.py"), Path("."), None)
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="keep"
    )
    # Module-level external import should be hoisted
    assert "import sys" in "".join(imports)
    # Function-local internal import should stay
    assert "from .utils import" in body
    assert "derive_module_name" in body
    assert "def compute_order():" in body


def test_split_imports_keep_mode_internal_relative_import_stays() -> None:
    """In 'keep' mode, relative internal imports should stay."""
    code = """import sys
from .config import Config
from ..parent import Parent

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="keep"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Relative internal imports should remain in body
    assert "from .config import Config" in body
    assert "from ..parent import Parent" in body
    assert "def foo():" in body


def test_split_imports_keep_mode_internal_mixed_with_external() -> None:
    """In 'keep' mode, mixed internal and external imports are handled correctly."""
    code = """import json
from pathlib import Path
from serger.config import Config
from serger.utils import helper

def func1():
    from .internal import helper
    return helper()

def func2():
    try:
        import external_lib
        return external_lib.do_something()
    except ImportError:
        pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="keep"
    )
    # Module-level external imports should be hoisted
    assert "import json" in "".join(imports)
    assert "from pathlib import Path" in "".join(imports)
    # Module-level internal imports should stay in body
    assert "from serger.config import Config" in body
    assert "from serger.utils import helper" in body
    # Function-local internal import should stay
    assert "from .internal import" in body
    # Function-local external import should stay
    assert "import external_lib" in body
    assert "def func1():" in body
    assert "def func2():" in body


def test_split_imports_keep_mode_internal_in_conditional_stays() -> None:
    """In 'keep' mode, internal imports in conditionals should stay."""
    code = """import sys

if some_condition:
    from serger.config import Config
    result = Config()

try:
    from .utils import helper
    result = helper()
except ImportError:
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="keep"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal imports in conditionals should stay
    assert "from serger.config import Config" in body
    assert "from .utils import helper" in body
    assert "if some_condition:" in body
    assert "try:" in body


def test_split_imports_keep_mode_internal_type_checking_stays() -> None:
    """In 'keep' mode, internal imports in TYPE_CHECKING blocks should stay."""
    code = """import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from serger.config import Config
    from .utils import helper
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="keep"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal imports in TYPE_CHECKING should stay
    assert "from serger.config import Config" in body
    assert "from .utils import helper" in body
    assert "if TYPE_CHECKING:" in body


def test_split_imports_keep_mode_internal_multi_package() -> None:
    """In 'keep' mode, internal imports from multiple packages should stay."""
    code = """import sys
from pkg1.module1 import func1
from pkg2.module2 import func2
from external_lib import something
"""
    imports, body = mod_stitch.split_imports(
        code, ["pkg1", "pkg2"], external_imports="force_top", internal_imports="keep"
    )
    # External imports should be hoisted
    assert "import sys" in "".join(imports)
    assert "from external_lib import something" in "".join(imports)
    # Internal imports from both packages should stay
    assert "from pkg1.module1 import func1" in body
    assert "from pkg2.module2 import func2" in body


def test_split_imports_keep_mode_internal_default_behavior() -> None:
    """Default internal_imports mode should still remove internal imports."""
    code = """import sys
from serger.config import Config

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal import should be removed (default is force_strip)
    assert "from serger.config" not in body
    assert "def foo():" in body


def test_split_imports_keep_mode_both_internal_and_external() -> None:
    """In 'keep' mode for both, all imports should stay in place."""
    code = """import sys
import json
from serger.config import Config

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="keep", internal_imports="keep"
    )
    # No imports should be collected
    assert len(imports) == 0
    # All imports should remain in body
    assert "import sys" in body
    assert "import json" in body
    assert "from serger.config import Config" in body
    assert "def foo():" in body


# ===== internal_imports strip mode tests =====


def test_split_imports_strip_internal_module_level_removed() -> None:
    """In 'strip' mode, module-level internal imports should be removed."""
    code = """import sys
from serger.config import Config
from serger.utils import helper

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal imports should be removed from body
    assert "from serger.config" not in body
    assert "from serger.utils" not in body
    assert "def foo():" in body


def test_split_imports_strip_internal_function_local_in_conditional_kept() -> None:
    """In 'strip' mode, function-local internal imports in conditionals kept."""
    code = """import sys

def compute_order():
    try:
        from .utils import derive_module_name
        return derive_module_name(Path("test.py"), Path("."), None)
    except ImportError:
        from serger.utils import derive_module_name
        return derive_module_name(Path("test.py"), Path("."), None)
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="strip"
    )
    # Module-level external import should be hoisted
    assert "import sys" in "".join(imports)
    # Function-local internal imports in try blocks kept (try is a conditional)
    assert "from .utils import" in body
    assert "from serger.utils import" in body
    assert "def compute_order():" in body
    assert "try:" in body
    assert "return derive_module_name" in body


def test_split_imports_strip_internal_function_local_not_conditional_removed() -> None:
    """In 'strip' mode, function-local internal imports not in conditionals removed."""
    code = """import sys

def compute_order():
    from .utils import derive_module_name
    return derive_module_name(Path("test.py"), Path("."), None)
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="strip"
    )
    # Module-level external import should be hoisted
    assert "import sys" in "".join(imports)
    # Function-local internal imports not in conditionals should be removed
    assert "from .utils import" not in body
    assert "def compute_order():" in body
    assert "return derive_module_name" in body  # Usage should remain


def test_split_imports_strip_internal_try_block_kept() -> None:
    """In 'strip' mode, internal imports inside try blocks should be kept."""
    code = """import sys

try:
    from serger.config import Config
    result = Config()
except ImportError:
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal import should be kept in try block
    assert "from serger.config import Config" in body
    assert "try:" in body
    assert "result = Config()" in body


def test_split_imports_strip_internal_if_block_kept() -> None:
    """In 'strip' mode, internal imports inside if blocks should be kept."""
    code = """import sys

if some_condition:
    from serger.config import Config
    result = Config()
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal import should be kept in if block
    assert "from serger.config import Config" in body
    assert "if some_condition:" in body
    assert "result = Config()" in body


def test_split_imports_strip_internal_type_checking_removed() -> None:
    """In 'strip' mode, internal imports inside TYPE_CHECKING blocks removed."""
    code = """import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from serger.config import Config
    from .utils import helper
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="strip"
    )
    # External imports should be hoisted
    assert "import sys" in "".join(imports)
    assert "from typing import TYPE_CHECKING" in "".join(imports)
    # Internal imports should be removed
    assert "from serger.config import Config" not in body
    assert "from .utils import helper" not in body
    # Empty TYPE_CHECKING block should be removed entirely
    assert "if TYPE_CHECKING:" not in body


def test_split_imports_strip_internal_type_checking_with_content_kept() -> None:
    """In 'strip' mode, TYPE_CHECKING blocks with non-import content are kept."""
    code = """import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from serger.config import Config
    # Some comment
    SOME_CONSTANT = "value"
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="strip"
    )
    # External imports should be hoisted
    assert "import sys" in "".join(imports)
    assert "from typing import TYPE_CHECKING" in "".join(imports)
    # Internal import should be removed
    assert "from serger.config import Config" not in body
    # TYPE_CHECKING block should remain with non-import content
    assert "if TYPE_CHECKING:" in body
    assert 'SOME_CONSTANT = "value"' in body


def test_split_imports_strip_internal_mixed_module_and_conditional() -> None:
    """In 'strip' mode, module-level internal imports removed, conditional ones kept."""
    code = """import sys
from serger.config import Config

if some_condition:
    from serger.utils import helper
    result = helper()

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Module-level internal import should be removed
    assert "from serger.config import Config" not in body
    # Conditional internal import should be kept
    assert "from serger.utils import helper" in body
    assert "if some_condition:" in body
    assert "result = helper()" in body
    assert "def foo():" in body


def test_split_imports_strip_internal_nested_conditionals_kept() -> None:
    """In 'strip' mode, internal imports in nested conditionals should be kept."""
    code = """import sys

if condition1:
    if condition2:
        from serger.config import Config
        result = Config()
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal import should be kept in nested conditionals
    assert "from serger.config import Config" in body
    assert "if condition1:" in body
    assert "if condition2:" in body
    assert "result = Config()" in body


def test_split_imports_strip_internal_relative_import_removed() -> None:
    """In 'strip' mode, module-level relative internal imports should be removed."""
    code = """import sys
from .config import Config
from ..parent import Parent

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Relative internal imports should be removed
    assert "from .config import Config" not in body
    assert "from ..parent import Parent" not in body
    assert "def foo():" in body


def test_split_imports_strip_internal_relative_import_in_conditional_kept() -> None:
    """In 'strip' mode, relative internal imports in conditionals should be kept."""
    code = """import sys

if some_condition:
    from .config import Config
    result = Config()
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Relative internal import in conditional should be kept
    assert "from .config import Config" in body
    assert "if some_condition:" in body
    assert "result = Config()" in body


def test_split_imports_strip_internal_multi_package() -> None:
    """In 'strip' mode, internal imports from multiple packages should be handled."""
    code = """import sys
from pkg1.module1 import func1
from pkg2.module2 import func2
from external_lib import something

if condition:
    from pkg1.other import helper
"""
    imports, body = mod_stitch.split_imports(
        code, ["pkg1", "pkg2"], external_imports="force_top", internal_imports="strip"
    )
    # External imports should be hoisted
    assert "import sys" in "".join(imports)
    assert "from external_lib import something" in "".join(imports)
    # Module-level internal imports should be removed
    assert "from pkg1.module1 import func1" not in body
    assert "from pkg2.module2 import func2" not in body
    # Conditional internal import should be kept
    assert "from pkg1.other import helper" in body
    assert "if condition:" in body


def test_split_imports_strip_internal_type_checking_multiple_pass_removed() -> None:
    """In 'strip' mode, TYPE_CHECKING blocks with only pass statements are removed."""
    code = """import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from serger.config import Config
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="strip"
    )
    # External imports should be hoisted
    assert "import sys" in "".join(imports)
    assert "from typing import TYPE_CHECKING" in "".join(imports)
    # Internal import should be removed
    assert "from serger.config import Config" not in body
    # Empty TYPE_CHECKING block should be removed entirely
    assert "if TYPE_CHECKING:" not in body


def test_split_imports_strip_internal_type_checking_with_other_condition_kept() -> None:
    """In 'strip' mode, TYPE_CHECKING with other conditions handled correctly."""
    code = """import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING or DEBUG:
    from serger.config import Config
    SOME_CONSTANT = "value"
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="strip"
    )
    # External imports should be hoisted
    assert "import sys" in "".join(imports)
    assert "from typing import TYPE_CHECKING" in "".join(imports)
    # Internal import should be kept (not a pure TYPE_CHECKING block)
    assert "from serger.config import Config" in body
    # Block should remain with all content
    assert "if TYPE_CHECKING or DEBUG:" in body
    assert 'SOME_CONSTANT = "value"' in body


# ===== internal_imports force_strip mode tests =====


def test_split_imports_force_strip_internal_module_level_removed() -> None:
    """In 'force_strip' mode, module-level internal imports should be removed."""
    code = """import sys
from serger.config import Config
from serger.utils import helper

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="force_strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal imports should be removed from body
    assert "from serger.config" not in body
    assert "from serger.utils" not in body
    assert "def foo():" in body


def test_split_imports_force_strip_internal_function_local_removed() -> None:
    """In 'force_strip' mode, function-local internal imports should be removed."""
    code = """import sys

def compute_order():
    from .utils import derive_module_name
    return derive_module_name(Path("test.py"), Path("."), None)
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="force_strip"
    )
    # Module-level external import should be hoisted
    assert "import sys" in "".join(imports)
    # Function-local internal import should be removed
    assert "from .utils import" not in body
    assert "derive_module_name" in body  # Usage should remain
    assert "def compute_order():" in body


def test_split_imports_force_strip_internal_relative_import_removed() -> None:
    """In 'force_strip' mode, relative internal imports should be removed."""
    code = """import sys
from .config import Config
from ..parent import Parent

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="force_strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Relative internal imports should be removed
    assert "from .config import Config" not in body
    assert "from ..parent import Parent" not in body
    assert "def foo():" in body


def test_split_imports_force_strip_internal_try_block_removed() -> None:
    """In 'force_strip' mode, internal imports inside try blocks should be removed."""
    code = """import sys

try:
    from serger.config import Config
    result = Config()
except ImportError:
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="force_strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal import should be removed
    assert "from serger.config import Config" not in body
    # Try block should remain but with pass added if empty
    assert "try:" in body


def test_split_imports_force_strip_internal_if_block_removed() -> None:
    """In 'force_strip' mode, internal imports inside if blocks should be removed."""
    code = """import sys

if some_condition:
    from serger.config import Config
    result = Config()
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="force_strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal import should be removed
    assert "from serger.config import Config" not in body
    # If block should remain
    assert "if some_condition:" in body


def test_split_imports_force_strip_internal_type_checking_removed() -> None:
    """In 'force_strip' mode, TYPE_CHECKING internal imports should be removed."""
    code = """import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from serger.config import Config
    from .utils import helper
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="force_strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal imports should be removed
    assert "from serger.config import Config" not in body
    assert "from .utils import helper" not in body
    # Empty TYPE_CHECKING block should be removed entirely
    assert "if TYPE_CHECKING:" not in body


def test_split_imports_force_strip_internal_type_checking_multiple_pass_removed() -> (
    None
):
    """Empty TYPE_CHECKING block with multiple pass should be removed."""
    code = """import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from serger.config import Config
    pass
    pass
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="force_strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal import should be removed
    assert "from serger.config import Config" not in body
    # Empty TYPE_CHECKING block (even with multiple pass) should be removed
    assert "if TYPE_CHECKING:" not in body


def test_split_imports_force_strip_internal_empty_try_gets_pass() -> None:
    """Empty try blocks should get 'pass' added."""
    code = """import sys

try:
    from serger.config import Config
except ImportError:
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="force_strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal import should be removed
    assert "from serger.config import Config" not in body
    # Empty try should have 'pass' added
    assert "try:" in body
    assert "pass" in body
    # Check that pass is in the try block
    body_lines = body.splitlines()
    try_line_idx = None
    for i, line in enumerate(body_lines):
        if line.strip() == "try:":
            try_line_idx = i
            break
    assert try_line_idx is not None
    # Next non-empty line should be indented pass
    for i in range(try_line_idx + 1, len(body_lines)):
        line = body_lines[i]
        if line.strip() and not line.strip().startswith("except"):
            assert line.startswith("    ")  # Indented
            assert "pass" in line
            break


def test_split_imports_force_strip_internal_empty_if_gets_pass() -> None:
    """Empty if blocks should get 'pass' added."""
    code = """import sys

if some_condition:
    from serger.config import Config
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="force_strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal import should be removed
    assert "from serger.config import Config" not in body
    # Empty if should have 'pass' added
    assert "if some_condition:" in body
    assert "pass" in body
    # Check that pass is indented inside the if block
    body_lines = body.splitlines()
    if_line_idx = None
    for i, line in enumerate(body_lines):
        if "if some_condition:" in line:
            if_line_idx = i
            break
    assert if_line_idx is not None
    # Next non-empty line should be indented pass
    for i in range(if_line_idx + 1, len(body_lines)):
        line = body_lines[i]
        if line.strip():
            assert line.startswith("    ")  # Indented
            assert "pass" in line
            break


def test_split_imports_force_strip_internal_type_checking_with_content_kept() -> None:
    """TYPE_CHECKING block with non-import content should be kept."""
    code = """import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from serger.config import Config
    SOME_CONSTANT = 42
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="force_strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal import should be removed
    assert "from serger.config import Config" not in body
    # TYPE_CHECKING block should remain with constant
    assert "if TYPE_CHECKING:" in body
    assert "SOME_CONSTANT = 42" in body


def test_split_imports_force_strip_internal_type_checking_with_other_condition_kept() -> (  # noqa: E501
    None
):
    """TYPE_CHECKING block with other conditions should be kept."""
    code = """import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING and some_flag:
    from serger.config import Config
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="force_strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal import should be removed
    assert "from serger.config import Config" not in body
    # Block should remain with pass added
    assert "if TYPE_CHECKING and some_flag:" in body
    assert "pass" in body


def test_split_imports_force_strip_internal_nested_conditionals() -> None:
    """In 'force_strip' mode, nested conditional internal imports should be removed."""
    code = """import sys

if condition1:
    if condition2:
        from serger.config import Config
        result = Config()
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top", internal_imports="force_strip"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal import should be removed
    assert "from serger.config import Config" not in body
    # Nested conditionals should remain
    assert "if condition1:" in body
    assert "if condition2:" in body


def test_split_imports_force_strip_internal_multi_package() -> None:
    """In 'force_strip' mode, multi-package internal imports should be removed."""
    code = """import sys
from pkg1.module1 import func1
from pkg2.module2 import func2
from external_lib import something
"""
    imports, body = mod_stitch.split_imports(
        code,
        ["pkg1", "pkg2"],
        external_imports="force_top",
        internal_imports="force_strip",
    )
    # External imports should be hoisted
    assert "import sys" in "".join(imports)
    assert "from external_lib import something" in "".join(imports)
    # Internal imports from both packages should be removed
    assert "from pkg1.module1 import func1" not in body
    assert "from pkg2.module2 import func2" not in body


def test_split_imports_force_strip_internal_default_behavior() -> None:
    """Default internal_imports mode should be force_strip."""
    code = """import sys
from serger.config import Config

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(
        code, ["serger"], external_imports="force_top"
    )
    # External import should be hoisted
    assert "import sys" in "".join(imports)
    # Internal import should be removed (default is force_strip)
    assert "from serger.config" not in body
    assert "def foo():" in body
