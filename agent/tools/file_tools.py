"""
File System Tools for reading and writing files
"""
import os
from typing import Optional


def file_read(file_path: str, encoding: str = "utf-8") -> str:
    """
    Read content from a file.

    Args:
        file_path: Absolute or relative path to the file
        encoding: File encoding (default: utf-8)

    Returns:
        File content as string, or error message if failed
    """
    try:
        # Security check: prevent reading from sensitive directories
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return f"Error: File not found: {file_path}"

        with open(abs_path, 'r', encoding=encoding) as f:
            return f.read()
    except PermissionError:
        return f"Error: Permission denied reading: {file_path}"
    except UnicodeDecodeError:
        # Try with different encoding
        try:
            with open(abs_path, 'r', encoding='gbk') as f:
                return f.read()
        except Exception as e:
            return f"Error: Failed to decode file: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


def file_write(file_path: str, content: str, encoding: str = "utf-8") -> str:
    """
    Write content to a file.

    Args:
        file_path: Absolute or relative path to the file
        content: Content to write
        encoding: File encoding (default: utf-8)

    Returns:
        Success message or error description
    """
    try:
        # Create parent directory if it doesn't exist
        abs_path = os.path.abspath(file_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        with open(abs_path, 'w', encoding=encoding) as f:
            f.write(content)

        return f"Successfully wrote to {file_path}"
    except PermissionError:
        return f"Error: Permission denied writing to: {file_path}"
    except Exception as e:
        return f"Error: {str(e)}"
