from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import shutil
import uuid

from app.config import settings


TEMP_IMPORT_DIR = Path(settings.IMPORT_TEMP_DIR)
TEMP_IMPORT_TTL = timedelta(hours=24)


def save_temp_import_file(*, job_id: str, filename: str, source_file) -> dict:
    TEMP_IMPORT_DIR.mkdir(parents=True, exist_ok=True)

    temp_root = _resolve_temp_import_dir()
    safe_name = _sanitize_filename(filename)
    temp_path = temp_root / f"{job_id}-{uuid.uuid4().hex}-{safe_name}"
    resolved_temp_path = temp_path.resolve(strict=False)

    if not _is_within_temp_import_dir(resolved_temp_path):
        raise OSError("Refusing to write import temp file outside the temp directory")

    source_file.seek(0)
    with resolved_temp_path.open("wb") as destination:
        shutil.copyfileobj(source_file, destination)
    source_file.seek(0)

    now = datetime.now(timezone.utc)

    return {
        "path": str(resolved_temp_path),
        "expires_at": now + TEMP_IMPORT_TTL,
    }


def delete_temp_import_file(path: str | None) -> bool:
    normalized_path = str(path or "").strip()

    if not normalized_path:
        return False

    safe_path = Path(normalized_path).resolve(strict=False)

    if not _is_within_temp_import_dir(safe_path):
        return False

    if not safe_path.exists():
        return False

    if not safe_path.is_file():
        return False

    safe_path.unlink()
    return True


def _sanitize_filename(filename: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", str(filename or "").strip())
    normalized = normalized.strip(".-") or "import.pdf"

    return normalized


def _resolve_temp_import_dir() -> Path:
    return TEMP_IMPORT_DIR.resolve(strict=False)


def _is_within_temp_import_dir(path: Path) -> bool:
    try:
        path.relative_to(_resolve_temp_import_dir())
        return True
    except ValueError:
        return False
