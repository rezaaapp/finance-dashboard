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
    CLEANUP_COMPLETED = "cleanup_completed"


class ImportJob(BaseModel):
    id: str
    workspace_id: str
    provider: str = "unknown"
    filename: str
    statement_owner: str = ""
    status: ImportJobStatus = ImportJobStatus.UPLOADED
    created_at: datetime
    completed_at: datetime | None = None
    transactions_found: int = 0
    new_transactions: int = 0
    existing_transactions: int = 0
    rejected_transactions: int = 0
    temp_file_deleted_at: datetime | None = None
    expires_at: datetime | None = None


class ParsedImportResult(BaseModel):
    provider: str = ""
    transactions: list[dict[str, Any]] = Field(default_factory=list)
    page_count: int = 0
    extracted_text_length: int = 0


class ImportPreviewItem(BaseModel):
    datetime: str = ""
    merchant_original: str = ""
    merchant_normalized: str = ""
    amount: float | int = 0


class ImportDraftTransaction(BaseModel):
    id: str | None = None
    import_job_id: str
    transaction_fingerprint: str
    canonical_fingerprint: str = ""
    canonical_fingerprint_date: str = ""
    statement_owner: str = ""
    source_fund: str
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
    detection_source: str = "unknown"
    statement_owner: str = ""
    status: ImportJobStatus = ImportJobStatus.UPLOADED
    transactions_found: int = 0
    new_transactions: int = 0
    existing_transactions: int = 0
    rejected_transactions: int = 0
    no_new_transactions: bool = False
    page_count: int = 0
    extracted_text_length: int = 0
    error_code: str | None = None
    message: str | None = None
    error: str | None = None
    preview: list[ImportPreviewItem] = Field(default_factory=list)
