"""File security validation: never trust extension alone."""
import os
import re
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode

settings = get_settings()

_MAGIC_BYTES = {
    b"%PDF": "pdf",
    b"PK\x03\x04": "zip",  # xlsx is a zip container
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
}

_EXT_TO_FORMAT = {
    ".pdf": "pdf", ".csv": "csv", ".xls": "xlsx", ".xlsx": "xlsx",
    ".txt": "txt", ".html": "html", ".htm": "html", ".png": "image", ".jpg": "image", ".jpeg": "image",
}

_SAFE_FILENAME_RE = re.compile(r"^[\w\-. ]+$")


def detect_format_from_bytes(head: bytes, filename: str) -> str:
    for magic, kind in _MAGIC_BYTES.items():
        if head.startswith(magic):
            if kind == "zip":
                return "xlsx"
            if kind in ("jpg", "png"):
                return "image"
            return kind
    ext = Path(filename).suffix.lower()
    return _EXT_TO_FORMAT.get(ext, "unknown")


def validate_upload(filename: str, size_bytes: int, head: bytes) -> str:
    if not filename or not _SAFE_FILENAME_RE.match(Path(filename).name):
        raise AppError(ErrorCode.INVALID_FILE, "Filename contains unsafe characters.")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise AppError(ErrorCode.INVALID_FILE, f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB limit.")
    if size_bytes == 0:
        raise AppError(ErrorCode.INVALID_FILE, "File is empty.")

    ext = Path(filename).suffix.lower()
    if ext not in _EXT_TO_FORMAT:
        raise AppError(ErrorCode.UNSUPPORTED_FORMAT, f"Unsupported file extension: {ext}")

    detected = detect_format_from_bytes(head, filename)
    if detected == "unknown":
        # Fall back to extension for plain-text formats (csv/txt/html have no magic bytes).
        detected = _EXT_TO_FORMAT[ext]

    return detected


def safe_temp_path(original_filename: str) -> Path:
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}{Path(original_filename).suffix.lower()}"
    return upload_dir / safe_name


def delete_temp_file(path: Path) -> None:
    try:
        if path.exists():
            os.remove(path)
    except OSError:
        pass
