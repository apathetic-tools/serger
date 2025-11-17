# tests/5_core/test_post_stitch_processing.py
"""Tests for post_stitch_processing function."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import serger.config.config_types as mod_types
import serger.verify_script as mod_verify
from tests.utils import (
    make_post_category_config_resolved,
    make_post_processing_config_resolved,
    make_tool_config_resolved,
)


def test_post_stitch_processing_with_valid_file() -> None:
    """Should process valid file successfully."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("def main():\n    return 0\n")
        f.flush()
        path = Path(f.name)
        path.chmod(0o755)

    try:
        config = make_post_processing_config_resolved(
            enabled=False,  # Disabled to avoid needing tools
            categories={
                "formatter": make_post_category_config_resolved(
                    enabled=False, priority=[], tools={}
                ),
            },
        )
        # Should not raise
        mod_verify.post_stitch_processing(path, post_processing=config)
    finally:
        path.unlink(missing_ok=True)


def test_post_stitch_processing_with_none_config() -> None:
    """Should skip post-processing when config is None."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("def main():\n    return 0\n")
        f.flush()
        path = Path(f.name)
        path.chmod(0o755)

    try:
        # Should not raise
        mod_verify.post_stitch_processing(path, post_processing=None)
    finally:
        path.unlink(missing_ok=True)


def test_post_stitch_processing_skips_when_not_compiling_before(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should skip post-processing when file doesn't compile before."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("def main(\n    return 0\n")  # Invalid syntax
        f.flush()
        path = Path(f.name)

    try:
        verify_executes_called = False

        def mock_verify_executes(_file_path: Path) -> bool:
            nonlocal verify_executes_called
            verify_executes_called = True
            return False

        monkeypatch.setattr(mod_verify, "verify_executes", mock_verify_executes)

        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["formatter"],
            categories={
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["format"], command="ruff"
                        ),
                    },
                ),
            },
        )
        # Should not raise, should skip post-processing
        mod_verify.post_stitch_processing(path, post_processing=config)
        # Should still try to verify execution
        assert verify_executes_called
    finally:
        path.unlink(missing_ok=True)


def test_post_stitch_processing_reverts_on_compilation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should revert changes when file doesn't compile after processing."""
    original_content = "def main():\n    return 0\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(original_content)
        f.flush()
        path = Path(f.name)
        path.chmod(0o755)

    try:
        # Mock execute_post_processing to corrupt the file
        def mock_execute_post_processing(
            file_path: Path,
            _config: mod_types.PostProcessingConfigResolved,
        ) -> None:
            # Corrupt the file
            file_path.write_text("def main(\n    return 0\n")  # Invalid syntax

        monkeypatch.setattr(
            mod_verify, "execute_post_processing", mock_execute_post_processing
        )

        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["formatter"],
            categories={
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["format"], command="ruff"
                        ),
                    },
                ),
            },
        )
        # Should revert and not raise
        mod_verify.post_stitch_processing(path, post_processing=config)
        # File should be reverted to original
        assert path.read_text() == original_content
    finally:
        path.unlink(missing_ok=True)


def test_post_stitch_processing_logs_error_on_revert_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should log error (not raise) when revert fails to compile."""
    original_content = "def main():\n    return 0\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(original_content)
        f.flush()
        path = Path(f.name)
        path.chmod(0o755)

    try:
        # Track calls to verify_compiles
        call_count = 0

        # Mock execute_post_processing to corrupt the file
        def mock_execute_post_processing(
            file_path: Path,
            _config: mod_types.PostProcessingConfigResolved,
        ) -> None:
            # Corrupt the file
            file_path.write_text("def main(\n    return 0\n")  # Invalid syntax

        # Mock verify_compiles: return True before processing, False after
        def mock_verify_compiles(_file_path: Path) -> bool:
            nonlocal call_count
            call_count += 1
            # First call: before processing (should return True)
            # Second call: after processing (should return False)
            # Third call: after revert (should return False to trigger error)
            return call_count == 1

        monkeypatch.setattr(
            mod_verify, "execute_post_processing", mock_execute_post_processing
        )
        monkeypatch.setattr(mod_verify, "verify_compiles", mock_verify_compiles)

        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["formatter"],
            categories={
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["format"], command="ruff"
                        ),
                    },
                ),
            },
        )
        # Should not raise, should log error and continue
        mod_verify.post_stitch_processing(path, post_processing=config)
        # Verify it was called 3 times (before, after, after revert)
        expected_calls = 3
        assert call_count == expected_calls
    finally:
        path.unlink(missing_ok=True)


def test_post_stitch_processing_logs_warning_when_not_compiling_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should log warning (not raise) when file doesn't compile after processing."""
    # Start with a valid file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("def main():\n    return 0\n")
        f.flush()
        path = Path(f.name)
        path.chmod(0o755)

    try:
        # Track calls to verify_compiles
        call_count = 0

        # Mock verify_compiles: return True before, False after (processing corrupts it)
        def mock_verify_compiles(_file_path: Path) -> bool:
            nonlocal call_count
            call_count += 1
            # First call: before processing (should return True so processing runs)
            # Second call: after processing (should return False - file is corrupted)
            # Third call: after revert (should return False - revert fails to fix it)
            return call_count == 1

        # Mock execute_post_processing to corrupt the file
        def mock_execute_post_processing(
            file_path: Path,
            _config: mod_types.PostProcessingConfigResolved,
        ) -> None:
            # Corrupt the file
            file_path.write_text("def main(\n    return 0\n")  # Invalid syntax

        monkeypatch.setattr(mod_verify, "verify_compiles", mock_verify_compiles)
        monkeypatch.setattr(
            mod_verify, "execute_post_processing", mock_execute_post_processing
        )

        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["formatter"],
            categories={
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["format"], command="ruff"
                        ),
                    },
                ),
            },
        )
        # Should not raise, should log error and continue
        mod_verify.post_stitch_processing(path, post_processing=config)
        # Verify it was called 3 times (before, after, after revert)
        expected_calls = 3
        assert call_count == expected_calls
    finally:
        path.unlink(missing_ok=True)


def test_post_stitch_processing_runs_execution_check() -> None:
    """Should run execution check after successful processing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("def main():\n    return 0\n")
        f.flush()
        path = Path(f.name)
        path.chmod(0o755)

    try:
        verify_executes_called = False

        def mock_verify_executes(_file_path: Path) -> bool:
            nonlocal verify_executes_called
            verify_executes_called = True
            return True

        with patch.object(mod_verify, "verify_executes", mock_verify_executes):
            config = make_post_processing_config_resolved(
                enabled=False,  # Disabled to avoid needing tools
                categories={
                    "formatter": make_post_category_config_resolved(
                        enabled=False, priority=[], tools={}
                    ),
                },
            )
            mod_verify.post_stitch_processing(path, post_processing=config)
            assert verify_executes_called
    finally:
        path.unlink(missing_ok=True)


def test_post_stitch_processing_preserves_file_permissions() -> None:
    """Should preserve file permissions after processing."""
    original_content = "def main():\n    return 0\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(original_content)
        f.flush()
        path = Path(f.name)
        path.chmod(0o755)

    try:
        config: mod_types.PostProcessingConfigResolved = {
            "enabled": False,  # Disabled to avoid needing tools
            "category_order": [],
            "categories": {},
        }
        mod_verify.post_stitch_processing(path, post_processing=config)
        # Permissions should be preserved (or at least executable)
        assert path.stat().st_mode & 0o111  # Executable bit
    finally:
        path.unlink(missing_ok=True)


def test_post_stitch_processing_with_actual_post_processing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should execute post-processing when enabled and tools are available."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x=1+2\n")  # Code that can be formatted
        f.flush()
        path = Path(f.name)
        path.chmod(0o755)

    try:
        execute_called = False

        def mock_execute_post_processing(
            _file_path: Path,
            _config: mod_types.PostProcessingConfigResolved,
        ) -> None:
            nonlocal execute_called
            execute_called = True

        monkeypatch.setattr(
            mod_verify, "execute_post_processing", mock_execute_post_processing
        )

        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["formatter"],
            categories={
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["format"], command="ruff"
                        ),
                    },
                ),
            },
        )
        mod_verify.post_stitch_processing(path, post_processing=config)
        assert execute_called
    finally:
        path.unlink(missing_ok=True)
