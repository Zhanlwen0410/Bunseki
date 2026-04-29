from pathlib import Path
from typing import Any, Dict

from src.utils.file_io import read_json_file, write_json


def save_project_file(output_path: Path, payload: Dict[str, Any]) -> None:
    write_json(payload, output_path)


def open_project_file(file_path: Path) -> Dict[str, Any]:
    payload = read_json_file(str(file_path))
    if not isinstance(payload, dict):
        raise ValueError("Project file must contain a JSON object.")
    return payload
