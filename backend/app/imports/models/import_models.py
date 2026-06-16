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


class ImportPreviewItem(BaseModel):
    datetime: str = ""
    merchant_original: str = ""
    merchant_normalized: str = ""
    amount: float | int = 0


class ImportDraftTransaction(BaseModel):
    id: str | None = None
    import_job_id: str
    transaction_fingerprint: str
    datetime: str = ""
    merchant_original: str = ""
    merchant_normalized: str = ""
    amount: float | int = 0
    direction: str = ""
    transaction_type: str = ""
    review_group: str = ""
    raw_text: str = ""
    is_existing: bool = False
    status: str = "new"
    category: str = ""
    notes: str = ""


class ImportUploadResult(BaseModel):
    job_id: str
    provider: str = "unknown"
    status: ImportJobStatus = ImportJobStatus.UPLOADED
    transactions_found: int = 0
    new_transactions: int = 0
    existing_transactions: int = 0
    preview: list[ImportPreviewItem] = Field(default_factory=list)
