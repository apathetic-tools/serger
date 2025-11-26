# tests/utils/check.py
import sys

import serger as pkg
import serger.logs as mod_logs
from tests.utils import TEST_TRACE


TEST_TRACE(
    "logger_origin",
    f"pkg_getAppLogger_id={id(pkg.getAppLogger)}",
    f"logs_getAppLogger_id={id(mod_logs.getAppLogger)}",
    f"pkg_getAppLogger is logs_getAppLogger? "
    f"{pkg.getAppLogger is mod_logs.getAppLogger}",
)

TEST_TRACE(
    "module_ids",
    f"pkg_logs_module={id(mod_logs)} path={getattr(mod_logs, '__file__', None)}",
    f"sys_modules[serger.logs]={id(sys.modules.get('serger.logs'))}",
)
