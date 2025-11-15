# tests/utils/subprocess_output.py
"""Helper for running subprocesses with flexible output handling.

This module provides utilities for running subprocesses with various output
capture and forwarding options. It supports forwarding captured output to
different destinations (bypass streams, normal streams, or not at all) and
can separate stdout from __stdout__ when needed.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any


class SubprocessResult:
    """Result from run_with_output() that includes all output in error messages."""

    def __init__(
        self,
        result: subprocess.CompletedProcess[str],
    ) -> None:
        self.result = result

    @property
    def stdout(self) -> str:
        """Captured stdout (includes trace/debug when LOG_LEVEL=test)."""
        return self.result.stdout

    @property
    def stderr(self) -> str:
        """Captured stderr."""
        return self.result.stderr

    @property
    def returncode(self) -> int:
        """Return code from subprocess."""
        return self.result.returncode

    @property
    def all_output(self) -> str:
        """All output combined: stdout + stderr."""
        parts: list[str] = []
        if self.stdout:
            parts.append(f"=== STDOUT ===\n{self.stdout}")
        if self.stderr:
            parts.append(f"=== STDERR ===\n{self.stderr}")
        return "\n\n".join(parts) if parts else ""


class SubprocessResultWithBypass:
    """Result from run_with_separated_output() with separate bypass output."""

    def __init__(
        self,
        result: subprocess.CompletedProcess[str],
        bypass_output: str,
    ) -> None:
        self.result = result
        self._bypass_output = bypass_output

    @property
    def stdout(self) -> str:
        """Captured stdout (normal output, excluding bypass)."""
        return self.result.stdout

    @property
    def stderr(self) -> str:
        """Captured stderr."""
        return self.result.stderr

    @property
    def bypass_output(self) -> str:
        """Bypass output (written to sys.__stdout__)."""
        return self._bypass_output

    @property
    def returncode(self) -> int:
        """Return code from subprocess."""
        return self.result.returncode

    @property
    def all_output(self) -> str:
        """All output combined: stdout + stderr + bypass."""
        parts: list[str] = []
        if self.stdout:
            parts.append(f"=== STDOUT ===\n{self.stdout}")
        if self.stderr:
            parts.append(f"=== STDERR ===\n{self.stderr}")
        if self.bypass_output:
            parts.append(f"=== BYPASS (__stdout__) ===\n{self.bypass_output}")
        return "\n\n".join(parts) if parts else ""


def run_with_output(
    args: list[str],
    *,
    cwd: Path | str | None = None,
    initial_env: dict[str, str] | None = None,
    env: dict[str, str] | None = None,
    forward_to: str | None = "normal",
    check: bool = False,
    **kwargs: Any,
) -> SubprocessResult:
    """Run subprocess and capture all output with optional forwarding.

    This helper captures subprocess output and can optionally forward it to
    different destinations. It ensures captured output is available for error
    messages and can be displayed in real-time if desired.

    Args:
        args: Command and arguments to run
        cwd: Working directory
        initial_env: Initial environment state. If None, uses os.environ.copy().
            If provided, starts with this environment (can be empty dict for
            blank environment).
        env: Additional environment variables to add/override
        forward_to: Where to forward captured output. Options:
            - "bypass": Forward to sys.__stdout__/sys.__stderr__
              (bypasses capsys) (default)
            - "normal": Forward to sys.stdout/sys.stderr (normal streams)
            - None: Don't forward
        check: If True, raise CalledProcessError on non-zero exit
        **kwargs: Additional arguments passed to subprocess.run()

    Returns:
        SubprocessResult with all captured output

    Example:
        # Use current environment with additional vars
        result = run_with_output(
            [sys.executable, "-m", "serger", "--config", "config.json"],
            cwd=tmp_path,
            env={"LOG_LEVEL": "test"},
        )

        # Forward output to bypass (visible in real-time, bypasses capsys)
        result = run_with_output(
            [sys.executable, "-m", "serger", "--config", "config.json"],
            cwd=tmp_path,
            env={"LOG_LEVEL": "test"},
            forward_to="bypass",
        )

        # Forward output to normal streams
        result = run_with_output(
            [sys.executable, "-m", "serger", "--config", "config.json"],
            cwd=tmp_path,
            env={"LOG_LEVEL": "test"},
            forward_to="normal",
        )

        # Don't forward output
        result = run_with_output(
            [sys.executable, "-m", "serger"],
            cwd=tmp_path,
            env={"LOG_LEVEL": "test"},
            forward_to=None,
        )

        # On test failure, output will be included
        assert result.returncode == 0, f"Failed: {result.all_output}"
    """
    # Set up environment
    proc_env = os.environ.copy() if initial_env is None else initial_env.copy()

    if env:
        proc_env.update(env)

    # Run subprocess with normal capture
    result = subprocess.run(  # noqa: S603
        args,
        cwd=cwd,
        env=proc_env,
        capture_output=True,
        text=True,
        check=check,
        **kwargs,
    )

    # Forward captured output to specified destination
    if forward_to == "bypass":
        if result.stdout and sys.__stdout__ is not None:
            print(result.stdout, file=sys.__stdout__, end="")
            sys.__stdout__.flush()
        if result.stderr and sys.__stderr__ is not None:
            print(result.stderr, file=sys.__stderr__, end="")
            sys.__stderr__.flush()
    elif forward_to == "normal":
        if result.stdout:
            print(result.stdout, end="")
            sys.stdout.flush()
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
            sys.stderr.flush()

    return SubprocessResult(result=result)


def run_with_separated_output(
    args: list[str],
    *,
    cwd: Path | str | None = None,
    initial_env: dict[str, str] | None = None,
    env: dict[str, str] | None = None,
    check: bool = False,
    **kwargs: Any,
) -> SubprocessResultWithBypass:
    """Run subprocess with stdout and __stdout__ captured separately.

    This uses a Python wrapper to modify sys.__stdout__ before the command runs,
    allowing code to write to stdout and __stdout__ normally without any
    changes. Normal output (stdout) is captured, while bypass output
    (__stdout__) goes to the parent's stdout.

    Args:
        args: Command and arguments to run (must be a Python command)
        cwd: Working directory
        initial_env: Initial environment state. If None, uses os.environ.copy().
            If provided, starts with this environment (can be empty dict for
            blank environment).
        env: Additional environment variables to add/override
        check: If True, raise CalledProcessError on non-zero exit
        **kwargs: Additional arguments passed to subprocess.run()

    Returns:
        SubprocessResultWithBypass with separate stdout and bypass_output

    Example:
        result = run_with_separated_output(
            [sys.executable, "-m", "serger", "--config", "config.json"],
            cwd=tmp_path,
            env={"LOG_LEVEL": "test"},
        )
        # stdout contains normal output (captured)
        # bypass_output contains output written to __stdout__
        assert result.returncode == 0, f"Failed: {result.all_output}"
    """
    # Set up environment
    proc_env = os.environ.copy() if initial_env is None else initial_env.copy()

    if env:
        proc_env.update(env)

    # Create Python wrapper script that modifies sys.__stdout__
    # This wrapper runs before the actual command and sets __stdout__ to fd 3
    wrapper_script = """import sys
import os

# Modify __stdout__ to point to fd 3 (preserved original stdout)
try:
    original_stdout = os.fdopen(3, 'w')
    sys.__stdout__ = original_stdout
except (OSError, ValueError):
    # FD 3 not available, __stdout__ remains unchanged
    pass

# Execute the actual command
import subprocess
import sys as sys_module

# Reconstruct the original command from environment
cmd = os.environ.get('_WRAPPED_CMD').split(chr(0))
sys_module.exit(subprocess.run(cmd).returncode)
"""

    # Create temporary wrapper script
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(wrapper_script)
        wrapper_path = f.name

    # Initialize read_pipe before try block
    read_pipe = None
    try:
        # Create pipes for stdout capture
        read_pipe, write_pipe = os.pipe()

        # Set up command in environment (use null separator for safety)
        proc_env["_WRAPPED_CMD"] = "\0".join(args)

        # Create shell command that:
        # 1. Preserves original stdout to fd 3: exec 3>&1
        # 2. Redirects stdout to pipe: exec 1>&{write_pipe}
        # 3. Runs Python wrapper: exec python wrapper.py
        shell_cmd = f"""
exec 3>&1  # Preserve original stdout to fd 3
exec 1>&{write_pipe}  # Redirect stdout to pipe
exec {shutil.which("python3") or sys.executable} {wrapper_path}
"""

        # Run the shell command
        # Note: We can't use capture_output=True because we need pass_fds
        # which is incompatible with capture_output. We need manual PIPE setup.
        result = subprocess.run(  # noqa: S603, UP022
            ["/bin/bash", "-c", shell_cmd],
            cwd=cwd,
            env=proc_env,
            stdout=subprocess.PIPE,  # This captures fd 3 output (bypass)
            stderr=subprocess.PIPE,  # This captures stderr
            text=True,
            check=check,
            pass_fds=(write_pipe,),
            **kwargs,
        )

        # Close write end
        os.close(write_pipe)

        # Read captured stdout from pipe
        captured_stdout = ""
        try:
            with os.fdopen(read_pipe, "r") as f:
                captured_stdout = f.read()
        except (OSError, ValueError):
            pass

        # Result structure:
        # - result.stdout contains bypass output (from fd 3)
        # - captured_stdout contains normal output (from pipe)
        # - result.stderr contains stderr

        # Create a modified CompletedProcess with swapped stdout
        modified_result = subprocess.CompletedProcess(
            args=args,
            returncode=result.returncode,
            stdout=captured_stdout,  # Normal output from pipe
            stderr=result.stderr,
        )

        return SubprocessResultWithBypass(
            result=modified_result,
            bypass_output=result.stdout,  # Bypass output from fd 3
        )

    finally:
        # Clean up wrapper script
        with suppress(OSError):
            Path(wrapper_path).unlink()
        if read_pipe is not None:
            with suppress(OSError):
                os.close(read_pipe)
