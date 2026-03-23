from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_for_bytes(content: bytes) -> str:
    hasher = hashlib.sha256()
    hasher.update(content)
    return hasher.hexdigest()


def sha256_for_file(path: str | Path) -> str:
    file_path = Path(path)
    hasher = hashlib.sha256()

    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def ensure_directory(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory