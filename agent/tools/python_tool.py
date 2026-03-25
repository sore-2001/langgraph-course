"""
Python Code Execution Tool

Safely executes Python code and captures output.
"""
import sys
from io import StringIO
from typing import Dict, Any


def python_exec(code: str) -> str:
    """
    Execute Python code and capture its output.

    This tool allows the agent to run Python code for:
    - Data analysis and calculations
    - Processing geological data
    - Generating plots and visualizations
    - Automating repetitive tasks

    Args:
        code: Python code to execute

    Returns:
        Captured stdout output and list of defined variables, or error message
    """
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()

    try:
        # Create a local scope for execution
        local_vars: Dict[str, Any] = {}
        exec(code, {"__builtins__": __builtins__}, local_vars)

        sys.stdout = old_stdout
        captured_output = redirected_output.getvalue()

        # Filter out private/magic variables
        public_vars = {k: v for k, v in local_vars.items()
                       if not k.startswith('_')}

        result = f"Output:\n{captured_output}"
        if public_vars:
            result += f"\n\nDefined variables: {list(public_vars.keys())}"

        return result

    except Exception as e:
        sys.stdout = old_stdout
        return f"Error: {str(e)}"
