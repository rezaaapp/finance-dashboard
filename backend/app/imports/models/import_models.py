from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ImportJobStatus(StrEnum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    REVIEW = "review"
    APPROVED = "approved"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class ImportJob(BaseModel):
    id: str
    workspace_id: str
    provider: str = "unknown"
    filename: str
    status: ImportJobStatus = ImportJobStatus.UPLOADED
    created_at: datetime
    completed_at: datetime | None = None


class ParsedImportResult(BaseModel):
    provider: str = ""
    transactions: list[dict[str, Any]] = Field(default_factory=list)


class ImportUploadResult(BaseModel):
    job_id: str
    provider: str = "unknown"
    status: ImportJobStatus = ImportJobStatus.UPLOADED
