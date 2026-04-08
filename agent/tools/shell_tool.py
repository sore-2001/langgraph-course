"""
Shell Command Execution Tool

Executes shell commands and captures output.
"""
import subprocess
from typing import Optional


def shell_exec(command: str, timeout: int = 30) -> str:
    """
    Execute a shell command and return its output.

    This tool allows the agent to:
    - Run system commands
    - Execute scripts
    - Manage files and directories
    - Install packages

    Args:
        command: Shell command to execute
        timeout: Command timeout in seconds (default: 30)

    Returns:
        Command output including stdout, stderr, and return code
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        output = f"STDOUT:\n{result.stdout}\n\n"
        output += f"STDERR:\n{result.stderr}\n\n"
        output += f"Return code: {result.returncode}"

        return output

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error: {str(e)}"
