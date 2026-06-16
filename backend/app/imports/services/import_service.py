from typing import BinaryIO

from app.imports.models.import_models import ImportPreviewItem
from app.imports.models.import_models import (
    ImportJobStatus,
    ImportUploadResult,
    ParsedImportResult,
)
from app.imports.parsers.blu_pdf_parser import BluPdfParser
from app.imports.repositories.import_repository import create_import_job
from app.imports.utils.fingerprint import build_transaction_fingerprint
from app.imports.utils.merchant_normalizer import MerchantNormalizer


class ImportService:
    def __init__(self):
        self.merchant_normalizer = MerchantNormalizer()

    def detect_provider(self, filename: str) -> str:
        normalized_filename = filename.lower()

        if normalized_filename.endswith(".pdf") and "blu" in normalized_filename:
            return "blu"

        return "unknown"

    def parse(self, file: BinaryIO, *, provider: str) -> ParsedImportResult:
        if provider == "blu":
            return BluPdfParser().parse(file)

        return ParsedImportResult(provider=provider, transactions=[])

    def enrich_transactions(self, parsed_result: ParsedImportResult) -> ParsedImportResult:
        enriched_transactions = []

        for transaction in parsed_result.transactions:
            merchant_name = transaction.get("merchant_original") or transaction.get("merchant", "")
            merchant_fields = self.merchant_normalizer.normalize(str(merchant_name))

            enriched_transaction = {
                **transaction,
                **merchant_fields,
            }
            enriched_transaction.pop("merchant", None)
            enriched_transaction["transaction_fingerprint"] = build_transaction_fingerprint(
                source_dana=parsed_result.provider.title(),
                datetime_value=str(enriched_transaction.get("datetime", "")),
                merchant_normalized=merchant_fields["merchant_normalized"],
                amount=enriched_transaction.get("amount", 0),
            )
            enriched_transactions.append(enriched_transaction)

        return ParsedImportResult(
            provider=parsed_result.provider,
            transactions=enriched_transactions,
        )

    def receive_upload(self, connection, *, workspace_id: str, file) -> ImportUploadResult:
        provider = self.detect_provider(file.filename or "")
        parsed_result = self.enrich_transactions(
            self.parse(file.file, provider=provider)
        )
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
                    merchant_original=str(transaction.get("merchant_original", "")),
                    merchant_normalized=str(transaction.get("merchant_normalized", "")),
                    amount=transaction.get("amount", 0),
                )
                for transaction in parsed_result.transactions[:5]
            ],
        )
