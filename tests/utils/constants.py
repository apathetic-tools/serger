# tests/utils/proj_root.py

from pathlib import Path


PROJ_ROOT = Path(__file__).resolve().parent.parent.parent.resolve()


DEFAULT_TEST_LOG_LEVEL = "test"
