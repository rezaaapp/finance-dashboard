from typing import BinaryIO

from app.imports.models.import_models import (
    ImportJobStatus,
    ImportUploadResult,
    ParsedImportResult,
)
from app.imports.repositories.import_repository import create_import_job


class ImportService:
    def detect_provider(self, filename: str) -> str:
        return "unknown"

    def parse(self, file: BinaryIO, *, provider: str) -> ParsedImportResult:
        return ParsedImportResult(provider=provider, transactions=[])

    def receive_upload(self, connection, *, workspace_id: str, file) -> ImportUploadResult:
        provider = self.detect_provider(file.filename or "")
        parsed_result = self.parse(file.file, provider=provider)
        job = create_import_job(
            connection,
            workspace_id=workspace_id,
            provider=parsed_result.provider or provider,
            filename=file.filename or "uploaded-file",
            status=ImportJobStatus.UPLOADED.value,
        )

        return ImportUploadResult(
            job_id=str(job["id"]),
            provider=job["provider"],
            status=job["status"],
        )
