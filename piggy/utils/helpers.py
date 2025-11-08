from pathlib import Path


def get_project_root() -> Path:
    """
    Returns the root directory containing the Python project.
    :return: An absolute path to the root of the project.
    """
    file_path = Path(__file__).resolve()
    return file_path.parent.parent.parent


def ensure_directory(file_path: str | Path) -> Path:
    """
    Ensure parent directory exists for a file path.

    Creates parent directories if they don't exist. Validates that the path
    itself is not an existing directory.

    :param file_path: File path as string or Path object
    :return: Validated Path object
    :raises ValueError: If path is an existing directory
    :raises OSError: If parent directory creation fails
    """
    path = Path(file_path)

    if path.exists() and path.is_dir():
        raise ValueError(f"Path is a directory, not a file: {file_path}")

    if path.parent != Path('.'):
        path.parent.mkdir(parents=True, exist_ok=True)

    return path
