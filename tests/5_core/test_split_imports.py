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
