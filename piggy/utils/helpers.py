from pathlib import Path


def get_project_root() -> Path:
    """
    Returns the root directory containing the Python project.
    :return: An absolute path to the root of the project.
    """
    file_path = Path(__file__).resolve()
    return file_path.parent.parent.parent
