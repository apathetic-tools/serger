# tests/utils/__init__.py

import apathetic_logging as mod_logging
import apathetic_utils as mod_utils
import apathetic_utils.subprocess as mod_subprocess

from .buildconfig import (
    make_build_cfg,
    make_build_input,
    make_config_content,
    make_include_resolved,
    make_meta,
    make_post_category_config_resolved,
    make_post_processing_config_resolved,
    make_resolved,
    make_tool_config_resolved,
    write_config_file,
)
from .config_validate import make_summary
from .force_mtime_advance import force_mtime_advance
from .package import make_test_package
from .proj_root import PROJ_ROOT
from .runtime_swap import runtime_swap
from .stitch_test import is_serger_build_for_test


# Import from apathetic_utils where identical
is_ci = mod_utils.is_ci
strip_common_prefix = mod_utils.strip_common_prefix
run_with_output = mod_utils.run_with_output
run_with_separated_output = mod_utils.run_with_separated_output
find_all_packages_under_path = mod_utils.find_all_packages_under_path
patch_everywhere = mod_utils.patch_everywhere
SubprocessResult = mod_subprocess.SubprocessResult
SubprocessResultWithBypass = mod_subprocess.SubprocessResultWithBypass

# Import from apathetic_logging (replaces test_trace)
TEST_TRACE = mod_logging.safeTrace
make_test_trace = mod_logging.makeSafeTrace


__all__ = [  # noqa: RUF022
    # buildconfig
    "make_build_cfg",
    "make_build_input",
    "make_config_content",
    "make_include_resolved",
    "make_meta",
    "make_post_category_config_resolved",
    "make_post_processing_config_resolved",
    "make_resolved",
    "make_tool_config_resolved",
    "write_config_file",
    # ci
    "is_ci",
    # config_validate
    "make_summary",
    # force_mtime_advance
    "force_mtime_advance",
    # package
    "make_test_package",
    # patch_everywhere (from apathetic_utils)
    "patch_everywhere",
    # proj_root
    "PROJ_ROOT",
    # runtime_swap
    "runtime_swap",
    # stitch_test
    "is_serger_build_for_test",
    # strip_common_prefix (from apathetic_utils)
    "strip_common_prefix",
    # subprocess_output (from apathetic_utils)
    "SubprocessResult",
    "SubprocessResultWithBypass",
    "run_with_output",
    "run_with_separated_output",
    # find_all_packages_under_path (from apathetic_utils)
    "find_all_packages_under_path",
    # test_trace (from apathetic_logging)
    "TEST_TRACE",
    "make_test_trace",
]
