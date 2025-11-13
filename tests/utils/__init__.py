# tests/utils/__init__.py

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
from .ci import is_ci
from .config_validate import make_summary
from .force_mtime_advance import force_mtime_advance
from .package import make_test_package
from .patch_everywhere import patch_everywhere
from .proj_root import PROJ_ROOT
from .runtime_swap import runtime_swap
from .strip_common_prefix import strip_common_prefix
from .test_trace import TEST_TRACE, make_test_trace


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
    # patch_everywhere
    "patch_everywhere",
    # proj_root
    "PROJ_ROOT",
    # runtime_swap
    "runtime_swap",
    # strip_common_prefix
    "strip_common_prefix",
    # test_trace
    "TEST_TRACE",
    "make_test_trace",
]
