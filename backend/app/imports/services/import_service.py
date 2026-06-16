from typing import BinaryIO

from app.imports.models.import_models import ImportPreviewItem
from app.imports.models.import_models import (
    ImportJobStatus,
    ImportUploadResult,
    ParsedImportResult,
)
from app.imports.parsers.blu_pdf_parser import BluPdfParser
from app.imports.repositories.import_repository import create_import_job


class ImportService:
    def detect_provider(self, filename: str) -> str:
        normalized_filename = filename.lower()

        if normalized_filename.endswith(".pdf") and "blu" in normalized_filename:
            return "blu"

        return "unknown"

    def parse(self, file: BinaryIO, *, provider: str) -> ParsedImportResult:
        if provider == "blu":
            return BluPdfParser().parse(file)

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
            transactions_found=len(parsed_result.transactions),
            preview=[
                ImportPreviewItem(
                    datetime=str(transaction.get("datetime", "")),
                    merchant=str(transaction.get("merchant", "")),
                    amount=transaction.get("amount", 0),
                )
                for transaction in parsed_result.transactions[:5]
            ],
        )
