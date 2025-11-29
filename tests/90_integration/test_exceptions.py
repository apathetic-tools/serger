# tests/90_integration/test_exceptions.py
"""Tests for package.cli (package and standalone versions)."""

import logging

import apathetic_logging as mod_alogs
import apathetic_utils as mod_utils
import pytest

import serger.cli as mod_cli
import serger.logs as mod_logs
import serger.meta as mod_meta


def test_main_handles_controlled_exception(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Simulate a controlled exception (e.g. ValueError) and verify clean handling."""

    # --- stubs ---
    def fake_parser() -> object:
        xmsg = "mocked config failure"
        raise ValueError(xmsg)

    # --- patch and execute ---
    mod_utils.patch_everywhere(
        monkeypatch,
        mod_cli,
        "_setup_parser",
        fake_parser,
        package_prefix=mod_meta.PROGRAM_PACKAGE,
        stitch_hints={"/dist/", "standalone", f"{mod_meta.PROGRAM_SCRIPT}.py", ".pyz"},
    )
    code = mod_cli.main([])

    # --- verify ---
    assert code == 1
    # ensure log() was called for controlled exception
    out = capsys.readouterr().err.lower()
    assert "mocked config failure".lower() in out


def test_main_handles_unexpected_exception(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Simulate an unexpected internal error and ensure it logs as critical."""

    # --- stubs ---
    def fake_parser() -> object:
        xmsg = "boom!"
        raise OSError(xmsg)  # not one of the controlled types

    # --- patch and execute ---
    mod_utils.patch_everywhere(
        monkeypatch,
        mod_cli,
        "_setup_parser",
        fake_parser,
        package_prefix=mod_meta.PROGRAM_PACKAGE,
        stitch_hints={"/dist/", "standalone", f"{mod_meta.PROGRAM_SCRIPT}.py", ".pyz"},
    )
    code = mod_cli.main([])

    # --- verify ---
    assert code == 1
    out = capsys.readouterr().err.lower()
    assert "Unexpected internal error".lower() in out


def test_main_fallbacks_to_safe_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If log() itself fails, safe_log() should be called instead of recursion."""
    # --- setup ---
    called: dict[str, str] = {}

    # --- stubs ---
    def fake_parser() -> object:
        xmsg = "simulated fail"
        raise ValueError(xmsg)

    def fake_safe_log(msg: str) -> None:
        called["msg"] = msg

    # --- force the internal logger to explode ---
    class BoomHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:  # noqa: ARG002
            xmsg = "handler exploded"
            raise RuntimeError(xmsg)

    # --- patch and execute ---
    mod_utils.patch_everywhere(
        monkeypatch,
        mod_cli,
        "_setup_parser",
        fake_parser,
        package_prefix=mod_meta.PROGRAM_PACKAGE,
        stitch_hints={"/dist/", "standalone", f"{mod_meta.PROGRAM_SCRIPT}.py", ".pyz"},
    )
    mod_utils.patch_everywhere(
        monkeypatch,
        mod_alogs,
        "safeLog",
        fake_safe_log,
        package_prefix=mod_meta.PROGRAM_PACKAGE,
        stitch_hints={"/dist/", "standalone", f"{mod_meta.PROGRAM_SCRIPT}.py", ".pyz"},
    )

    # Backup logger state
    logger = mod_logs.getAppLogger()
    old_handlers = list(logger.handlers)
    old_level = logger.level

    try:
        # initialize hanlders so we have something to replace
        logger.ensureHandlers()

        # Replace handlers with the exploding one
        logger.handlers = [BoomHandler()]
        logger.setLevel(logging.DEBUG)
        code = mod_cli.main([])
    finally:
        # Always restore to avoid affecting other tests
        logger.handlers = old_handlers
        logger.ensureHandlers()
        logger.setLevel(old_level)

    # --- verify ---
    assert code == 1
    assert "Logging failed while reporting" in called["msg"]
