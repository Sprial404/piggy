import traceback
from io import StringIO


def format_error_message(exception: Exception, include_traceback: bool = False) -> str:
    """
    Format an exception as a user-friendly error message.

    :param exception: The exception to format
    :param include_traceback: Whether to include full traceback
    :return: Formatted error message string
    """
    if include_traceback:
        # Capture traceback to string
        tb_output = StringIO()
        traceback.print_exc(file=tb_output)
        tb_string = tb_output.getvalue()

        # Format with prominent header
        lines = [
            "",
            "=" * 50,
            "UNEXPECTED ERROR - Please report this issue",
            "=" * 50,
            tb_string.rstrip(),
            "=" * 50,
            "",
        ]
        return "\n".join(lines)
    else:
        # Simple error message for expected errors
        return f"Error: {exception}"


def get_error_category(exception: Exception) -> str:
    """
    Categorize an exception to determine handling strategy.

    :param exception: The exception to categorize
    :return: Category string: 'expected', 'io', 'interrupt', or 'unexpected'
    """
    if isinstance(exception, ValueError | KeyError | FileNotFoundError):
        return "expected"
    elif isinstance(exception, OSError | IOError):
        return "io"
    elif isinstance(exception, KeyboardInterrupt):
        return "interrupt"
    else:
        return "unexpected"


def format_error_for_category(exception: Exception, category: str) -> str:
    """
    Format error message based on category.

    :param exception: The exception to format
    :param category: Error category from get_error_category()
    :return: Formatted error message
    """
    if category == "expected":
        return f"Error: {exception}"
    elif category == "io":
        return f"File operation failed: {exception}"
    elif category == "unexpected":
        return format_error_message(exception, include_traceback=True)
    else:
        return str(exception)
