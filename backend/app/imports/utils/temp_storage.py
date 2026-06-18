from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import shutil
import uuid

from app.config import BACKEND_ROOT


TEMP_IMPORT_DIR = BACKEND_ROOT / "output" / "imports" / "temp"
TEMP_IMPORT_TTL = timedelta(hours=24)


def save_temp_import_file(*, job_id: str, filename: str, source_file) -> dict:
    TEMP_IMPORT_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_filename(filename)
    temp_path = TEMP_IMPORT_DIR / f"{job_id}-{uuid.uuid4().hex}-{safe_name}"

    source_file.seek(0)
    with temp_path.open("wb") as destination:
        shutil.copyfileobj(source_file, destination)
    source_file.seek(0)

    now = datetime.now(timezone.utc)

    return {
        "path": str(temp_path),
        "expires_at": now + TEMP_IMPORT_TTL,
    }


def delete_temp_import_file(path: str | None) -> bool:
    normalized_path = str(path or "").strip()

    if not normalized_path:
        return False

    safe_path = Path(normalized_path)

    if not safe_path.exists():
        return False

    safe_path.unlink()
    return True


def _sanitize_filename(filename: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", str(filename or "").strip())
    normalized = normalized.strip(".-") or "import.pdf"

    return normalized
