"""CSV writing utilities for clean and consistent CSV export."""

import csv
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any


def format_value(value: Any) -> str:
    """
    Format a value for CSV output.

    Handles datetime, date, Decimal, bool, and None types with appropriate formatting.

    :param value: Value to format
    :return: Formatted string representation
    """
    if isinstance(value, datetime | date):
        return value.isoformat()
    elif isinstance(value, Decimal | bool):
        return str(value)
    elif value is None:
        return ""
    return str(value)


def write_csv_from_dicts(headers: list[str], rows: list[dict[str, Any]], file_path: str | None = None) -> str:
    """
    Write CSV from list of dictionaries.

    :param headers: List of column headers
    :param rows: List of dictionaries containing row data
    :param file_path: Optional file path to save CSV
    :return: CSV content as string
    """
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)

    csv_content = output.getvalue()

    if file_path:
        Path(file_path).write_text(csv_content, encoding="utf-8")

    return csv_content
