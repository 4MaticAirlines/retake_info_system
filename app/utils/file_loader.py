import re
from hashlib import md5
from pathlib import Path
from uuid import uuid4


def calculate_file_hash(file_bytes: bytes) -> str:
    return md5(file_bytes).hexdigest()


def calculate_file_hash_from_path(file_path: Path) -> str:
    return calculate_file_hash(file_path.read_bytes())


def _sanitize_name(file_name: str) -> str:
    file_name = file_name.strip()
    file_name = re.sub(r"\s+", "_", file_name)
    file_name = re.sub(r"[^A-Za-zА-Яа-яЁё0-9._-]", "", file_name)
    return file_name or "file"


def build_stored_file_name(original_name: str) -> str:
    path = Path(original_name)
    stem = _sanitize_name(path.stem)
    suffix = path.suffix.lower()
    return f"{stem}_{uuid4().hex[:8]}{suffix}"


def save_binary_file(directory: Path, original_name: str, file_bytes: bytes) -> tuple[str, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = build_stored_file_name(original_name)
    file_path = directory / stored_name
    file_path.write_bytes(file_bytes)
    return stored_name, file_path


def find_existing_file_by_hash(directory: Path, file_hash: str) -> Path | None:
    if not directory.exists():
        return None

    for file_path in directory.iterdir():
        if not file_path.is_file():
            continue
        if file_path.name.startswith("."):
            continue
        if calculate_file_hash_from_path(file_path) == file_hash:
            return file_path

    return None