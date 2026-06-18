from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO
import logging

from app.imports.models.import_models import ImportPreviewItem
from app.imports.models.import_models import (
    ImportDraftTransaction,
    ImportJobStatus,
    ImportUploadResult,
    ParsedImportResult,
)
from app.imports.parsers.blu_pdf_parser import BluPdfParser
from app.imports.repositories.final_transaction_repository import (
    count_successful_import_transactions,
    create_import_transactions,
    list_retryable_import_transactions,
    serialize_import_transaction_row,
    update_import_transaction_sync_status,
    update_import_transaction_sync_status_by_ids,
)
from app.imports.repositories.fingerprint_registry_repository import (
    register_transaction_fingerprints,
)
from app.imports.repositories.import_repository import (
    create_import_draft_transactions,
    create_import_job,
    count_new_import_draft_transactions,
    delete_import_draft_transactions,
    get_import_history_detail,
    list_import_history,
    get_existing_transaction_fingerprints,
    get_import_review_summary,
    increment_import_job_rejected_count,
    list_import_draft_transactions,
    list_import_draft_transactions_by_ids,
    reject_import_draft_transactions,
    refresh_import_job_aggregates,
    set_import_job_temp_file,
    list_workspace_transaction_categories,
    update_import_job_provider,
    update_import_job_status,
    update_import_job_summary,
)
from app.imports.services.cleanup_service import ImportCleanupService
from app.imports.services.incremental_import_engine import IncrementalImportEngine
from app.imports.services.spreadsheet_sync_service import SpreadsheetSyncService
from app.imports.services.spreadsheet_value_resolver import SpreadsheetValueResolver
from app.imports.utils.fingerprint import build_transaction_fingerprint
from app.imports.utils.merchant_normalizer import MerchantNormalizer
from app.imports.utils.provider_detection import detect_import_provider
from app.imports.utils.temp_storage import delete_temp_import_file, save_temp_import_file
from app.repositories.google_oauth_repository import get_active_google_oauth_connection
from app.repositories.google_sheet_source_repository import (
    ensure_import_google_sheet_source,
    get_google_sheet_source,
)
from app.security.encryption import decrypt_text
from app.services.google_sheets_client import GoogleSheetsClientError, read_sheet_values
from app.services.sheet_header_validator import canonicalize_header


logger = logging.getLogger(__name__)


class MissingGoogleSheetSourceError(Exception):
    error_code = "missing_google_sheet_source"
    message = "Google Sheet aktif belum dikonfigurasi. Hubungkan Google Sheets dulu di Settings."

    def to_response(self) -> dict:
        return {
            "status": "failed",
            "error_code": self.error_code,
            "message": self.message,
        }


class MissingTargetSheetError(Exception):
    error_code = "missing_target_sheet"
    message = "Pilih target spreadsheet dan tab tujuan sebelum approve."

    def to_response(self) -> dict:
        return {
            "status": "failed",
            "error_code": self.error_code,
            "message": self.message,
        }


class InvalidTargetSheetHeaderError(Exception):
    error_code = "invalid_target_sheet_header"
    message = "Tab tujuan belum memiliki format kolom transaksi yang sesuai."

    def to_response(self) -> dict:
        return {
            "status": "failed",
            "error_code": self.error_code,
            "message": self.message,
        }


REQUIRED_IMPORT_TARGET_COLUMNS = [
    "Nama",
    "Waktu Transaksi",
    "Nama Transaksi",
    "Kategori",
    "Harga",
    "Source Dana",
    "Keterangan",
]


class ImportService:
    def __init__(self):
        self.cleanup_service = ImportCleanupService()
        self.incremental_engine = IncrementalImportEngine()
        self.merchant_normalizer = MerchantNormalizer()
        self.spreadsheet_sync_service = SpreadsheetSyncService()
        self.spreadsheet_value_resolver = SpreadsheetValueResolver()

    def detect_provider(self, filename: str) -> str:
        return self.detect_provider_details(filename=filename)["provider"]

    def detect_provider_details(self, *, filename: str, extracted_text: str = "") -> dict:
        return detect_import_provider(
            filename=filename,
            extracted_text=extracted_text,
        )

    def parse(self, file: BinaryIO, *, provider: str) -> ParsedImportResult:
        if provider == "blu":
            return BluPdfParser().parse(file)

        return ParsedImportResult(provider=provider, transactions=[])

    def parse_extracted(self, extraction: dict, *, provider: str) -> ParsedImportResult:
        if provider == "blu":
            return BluPdfParser().parse_extracted_lines(
                extraction.get("lines", []),
                page_count=extraction.get("page_count", 0),
                extracted_text_length=extraction.get("extracted_text_length", 0),
            )

        return ParsedImportResult(
            provider=provider,
            transactions=[],
            page_count=extraction.get("page_count", 0),
            extracted_text_length=extraction.get("extracted_text_length", 0),
        )

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

    def mark_existing_transactions(
        self,
        connection,
        *,
        workspace_id: str,
        parsed_result: ParsedImportResult,
    ) -> ParsedImportResult:
        transaction_fingerprints = [
            str(transaction.get("transaction_fingerprint", ""))
            for transaction in parsed_result.transactions
            if transaction.get("transaction_fingerprint")
        ]
        existing_fingerprints = get_existing_transaction_fingerprints(
            connection,
            workspace_id=workspace_id,
            transaction_fingerprints=transaction_fingerprints,
        )

        return ParsedImportResult(
            provider=parsed_result.provider,
            transactions=self.incremental_engine.apply(
                parsed_result.transactions,
                existing_fingerprints=existing_fingerprints,
            ),
        )

    def persist_draft_transactions(self, connection, *, import_job_id: str, transactions: list[dict]):
        new_transactions = [
            transaction for transaction in transactions
            if not transaction.get("is_existing", False)
        ]
        draft_transactions = [
            ImportDraftTransaction(
                import_job_id=import_job_id,
                transaction_fingerprint=str(transaction.get("transaction_fingerprint", "")),
                datetime=str(transaction.get("datetime", "")),
                merchant_original=str(transaction.get("merchant_original", "")),
                merchant_normalized=str(transaction.get("merchant_normalized", "")),
                amount=transaction.get("amount", 0),
                direction=str(transaction.get("direction", "")),
                transaction_type=str(transaction.get("transaction_type", "")),
                review_group=str(transaction.get("review_group", "")),
                raw_text=str(transaction.get("raw_text", "")),
                is_existing=bool(transaction.get("is_existing", False)),
                status="new",
                category="",
                notes="",
            ).model_dump()
            for transaction in new_transactions
        ]
        create_import_draft_transactions(
            connection,
            draft_transactions=draft_transactions,
        )

    def receive_upload(self, connection, *, workspace_id: str, file) -> ImportUploadResult:
        filename = file.filename or "uploaded-file"
        filename_provider = self.detect_provider(filename)
        job = create_import_job(
            connection,
            workspace_id=workspace_id,
            provider=filename_provider,
            filename=filename,
            status=ImportJobStatus.UPLOADED.value,
        )
        job_id = str(job["id"])
        self._log_import_event(
            "smart_import.upload.started",
            job_id=job_id,
            filename=filename,
            file_size=self._get_upload_file_size(file),
        )
        temp_file = save_temp_import_file(
            job_id=job_id,
            filename=filename,
            source_file=file.file,
        )
        set_import_job_temp_file(
            connection,
            job_id=job_id,
            temp_file_path=temp_file["path"],
            expires_at=temp_file["expires_at"],
        )
        extraction = {
            "lines": [],
            "page_count": 0,
            "extracted_text": "",
            "extracted_text_length": 0,
            "extracted_text_hash": "",
        }
        try:
            temp_path = Path(temp_file["path"])

            if not temp_path.is_file():
                return self._fail_upload(
                    connection,
                    job_id=job_id,
                    provider=filename_provider,
                    detection_source="filename" if filename_provider != "unknown" else "unknown",
                    page_count=0,
                    extracted_text_length=0,
                    stage="temp_storage",
                    reason="Temporary PDF file was not found before parsing",
                    user_error="File import sementara tidak ditemukan.",
                )

            with temp_path.open("rb") as temp_pdf:
                extraction = BluPdfParser().extract_pdf_metadata(temp_pdf)

            provider_detection = self.detect_provider_details(
                filename=filename,
                extracted_text=extraction.get("extracted_text", ""),
            )
            provider = provider_detection["provider"]
            detection_source = provider_detection["detection_source"]
            update_import_job_provider(
                connection,
                job_id=job_id,
                provider=provider,
            )
            self._log_import_event(
                "smart_import.provider.detected",
                job_id=job_id,
                provider=provider,
                detection_source=detection_source,
            )
            self._log_import_event(
                "smart_import.pdf.extracted",
                job_id=job_id,
                provider=provider,
                page_count=extraction["page_count"],
                extracted_text_length=extraction["extracted_text_length"],
                extracted_text_hash=extraction.get("extracted_text_hash", "")[:16],
            )

            if extraction["extracted_text_length"] == 0:
                return self._fail_upload(
                    connection,
                    job_id=job_id,
                    provider=provider,
                    detection_source=detection_source,
                    page_count=extraction["page_count"],
                    extracted_text_length=extraction["extracted_text_length"],
                    stage="pdf_extraction",
                    reason="PDF text layer is empty",
                    user_error="PDF tidak memiliki text layer atau gagal dibaca.",
                )

            update_import_job_status(
                connection,
                job_id=job_id,
                status=ImportJobStatus.PARSING.value,
            )
            self._log_import_event(
                "smart_import.parser.started",
                job_id=job_id,
                provider=provider,
            )
            parsed_result = self.enrich_transactions(
                self.parse_extracted(extraction, provider=provider)
            )

            self._log_import_event(
                "smart_import.parser.completed",
                job_id=job_id,
                provider=provider,
                transactions_found=len(parsed_result.transactions),
                review_groups_found=sorted({
                    str(transaction.get("review_group", ""))
                    for transaction in parsed_result.transactions
                    if str(transaction.get("review_group", "")).strip()
                }),
            )

            if provider == "blu" and not parsed_result.transactions:
                return self._fail_upload(
                    connection,
                    job_id=job_id,
                    provider=provider,
                    detection_source=detection_source,
                    page_count=extraction["page_count"],
                    extracted_text_length=extraction["extracted_text_length"],
                    stage="parser",
                    reason="Blu PDF text was extracted but no transactions were parsed",
                    user_error="PDF Blu terbaca, tapi transaksi tidak berhasil diparse.",
                )

            parsed_result = self.mark_existing_transactions(
                connection,
                workspace_id=workspace_id,
                parsed_result=parsed_result,
            )
            self.persist_draft_transactions(
                connection,
                import_job_id=str(job["id"]),
                transactions=parsed_result.transactions,
            )
            new_transactions = [
                transaction for transaction in parsed_result.transactions
                if not transaction.get("is_existing", False)
            ]
            existing_transactions = [
                transaction for transaction in parsed_result.transactions
                if transaction.get("is_existing", False)
            ]
            update_import_job_summary(
                connection,
                job_id=job_id,
                transactions_found=len(parsed_result.transactions),
                new_transactions=len(new_transactions),
                existing_transactions=len(existing_transactions),
                status=ImportJobStatus.REVIEW.value,
            )
            self._log_import_event(
                "smart_import.incremental.completed",
                job_id=job_id,
                transactions_found=len(parsed_result.transactions),
                new_transactions=len(new_transactions),
                existing_transactions=len(existing_transactions),
            )
        except Exception:
            delete_temp_import_file(temp_file["path"])
            update_import_job_status(
                connection,
                job_id=job_id,
                status=ImportJobStatus.FAILED.value,
                completed_at=datetime.now(timezone.utc),
            )
            self._log_import_event(
                "smart_import.failed",
                job_id=job_id,
                stage="runtime_exception",
                reason="Import upload failed unexpectedly",
            )
            raise

        return ImportUploadResult(
            job_id=job_id,
            provider=parsed_result.provider or job["provider"],
            detection_source=detection_source,
            status=ImportJobStatus.REVIEW,
            transactions_found=len(parsed_result.transactions),
            new_transactions=len(new_transactions),
            existing_transactions=len(existing_transactions),
            page_count=parsed_result.page_count,
            extracted_text_length=parsed_result.extracted_text_length,
            preview=[
                ImportPreviewItem(
                    datetime=str(transaction.get("datetime", "")),
                    merchant_original=str(transaction.get("merchant_original", "")),
                    merchant_normalized=str(transaction.get("merchant_normalized", "")),
                    amount=transaction.get("amount", 0),
                )
                for transaction in new_transactions[:5]
            ],
        )

    def _fail_upload(
        self,
        connection,
        *,
        job_id: str,
        provider: str,
        detection_source: str,
        page_count: int,
        extracted_text_length: int,
        stage: str,
        reason: str,
        user_error: str,
    ) -> ImportUploadResult:
        update_import_job_summary(
            connection,
            job_id=job_id,
            transactions_found=0,
            new_transactions=0,
            existing_transactions=0,
            status=ImportJobStatus.FAILED.value,
        )
        update_import_job_status(
            connection,
            job_id=job_id,
            status=ImportJobStatus.FAILED.value,
            completed_at=datetime.now(timezone.utc),
        )
        self._log_import_event(
            "smart_import.failed",
            job_id=job_id,
            stage=stage,
            reason=reason,
        )

        return ImportUploadResult(
            job_id=job_id,
            provider=provider,
            detection_source=detection_source,
            status=ImportJobStatus.FAILED,
            transactions_found=0,
            new_transactions=0,
            existing_transactions=0,
            page_count=page_count,
            extracted_text_length=extracted_text_length,
            error=user_error,
            preview=[],
        )

    def _get_upload_file_size(self, file) -> int | None:
        size = getattr(file, "size", None)

        if isinstance(size, int):
            return size

        return None

    def _log_import_event(self, event_name: str, **fields):
        logger.info(
            event_name,
            extra={"smart_import": fields},
        )

    def get_review_payload(self, connection, *, workspace_id: str, job_id: str):
        summary = get_import_review_summary(
            connection,
            workspace_id=workspace_id,
            job_id=job_id,
        )

        if not summary:
            return None

        draft_transactions = list_import_draft_transactions(
            connection,
            import_job_id=job_id,
            status="new",
        )

        serialized_transactions = [
            {
                "id": str(transaction["id"]),
                "datetime": transaction["datetime"],
                "merchant_original": transaction["merchant_original"],
                "merchant_normalized": transaction["merchant_normalized"],
                "merchant_display": self.merchant_normalizer.normalize(
                    transaction["merchant_original"]
                )["merchant_display"],
                "amount": float(transaction["amount"]),
                "direction": transaction["direction"],
                "transaction_type": transaction["transaction_type"],
                "review_group": transaction["review_group"],
                "raw_text": transaction["raw_text"],
                "status": transaction["status"],
                "category": transaction["category"],
                "notes": transaction["notes"],
            }
            for transaction in draft_transactions
        ]

        return {
            "summary": {
                "job_id": str(summary["id"]),
                "filename": summary["filename"],
                "provider": summary["provider"],
                "transactions_found": summary["transactions_found"],
                "new_transactions": summary["new_transactions"],
                "existing_transactions": summary["existing_transactions"],
                "created_at": summary["created_at"],
            },
            "filters": self._build_review_filters(serialized_transactions),
            "draft_transactions": serialized_transactions,
        }

    def get_category_options_payload(self, connection, *, workspace_id: str):
        return {
            "categories": list_workspace_transaction_categories(
                connection,
                workspace_id=workspace_id,
            ),
        }

    def approve_review_transactions(
        self,
        connection,
        *,
        workspace: dict,
        current_user: dict,
        workspace_id: str,
        import_job_id: str,
        draft_ids: list[str],
        item_updates: list[dict] | None = None,
        sheet_source_id: str | None = None,
        sheet_name: str | None = None,
    ):
        review_summary = get_import_review_summary(
            connection,
            workspace_id=workspace_id,
            job_id=import_job_id,
        )
        if not review_summary:
            return None

        normalized_ids = self._normalize_draft_ids(draft_ids, item_updates)
        selected_drafts = list_import_draft_transactions_by_ids(
            connection,
            import_job_id=import_job_id,
            draft_ids=normalized_ids,
        )
        merged_drafts = self._merge_review_item_updates(
            selected_drafts,
            item_updates=item_updates or [],
        )
        if not merged_drafts:
            return {
                "approved_count": 0,
                "sync_success": 0,
                "sync_failed": 0,
                "sync_status": "skipped",
                "draft_ids": [],
            }

        target_sheet = self._resolve_import_target_sheet(
            connection,
            workspace=workspace,
            current_user=current_user,
            workspace_id=workspace_id,
            sheet_source_id=sheet_source_id,
            sheet_name=sheet_name,
        )
        resolved_source_dana = self.spreadsheet_value_resolver.resolve_source_dana_for_append(
            connection,
            workspace_id=workspace_id,
            provider="Blu",
        )
        resolved_user_name = self._resolve_import_user_name(
            connection,
            current_user=current_user,
            workspace_id=workspace_id,
            workspace=workspace,
        )
        final_transaction_rows = [
            serialize_import_transaction_row(
                workspace_id=workspace_id,
                sheet_source_id=str(target_sheet["source"]["id"]),
                import_job_id=import_job_id,
                user_name=resolved_user_name,
                source_fund=resolved_source_dana,
                transaction=draft,
            )
            for draft in merged_drafts
        ]
        created_transactions = create_import_transactions(
            connection,
            rows=final_transaction_rows,
        )
        register_transaction_fingerprints(
            connection,
            rows=[
                {
                    "transaction_fingerprint": draft["transaction_fingerprint"],
                    "provider": review_summary["provider"],
                }
                for draft in merged_drafts
            ],
        )
        self._log_import_event(
            "smart_import.spreadsheet_sync.started",
            job_id=import_job_id,
            sheet_source_id=str(target_sheet["source"]["id"]),
            sheet_name=target_sheet["sheet_name"],
            row_count=len(merged_drafts),
        )
        sync_result = self.spreadsheet_sync_service.sync_import_transactions(
            connection,
            workspace=workspace,
            current_user=current_user,
            approved_transactions=merged_drafts,
            target_sheet_source=target_sheet["source"],
            target_sheet_name=target_sheet["sheet_name"],
            user_name=resolved_user_name,
            source_dana=resolved_source_dana,
            job_id=import_job_id,
        )
        if sync_result["status"] == "success":
            self._log_import_event(
                "smart_import.spreadsheet_sync.completed",
                job_id=import_job_id,
                success_count=sync_result["sync_success"],
                failed_count=sync_result["sync_failed"],
            )
        else:
            self._log_import_event(
                "smart_import.spreadsheet_sync.failed",
                job_id=import_job_id,
                sheet_name=target_sheet["sheet_name"],
                reason=sync_result.get("error") or sync_result["status"],
            )
        transaction_fingerprints = [
            draft["transaction_fingerprint"]
            for draft in merged_drafts
        ]
        if sync_result["status"] == "success":
            success_status_kwargs = {
                "transaction_fingerprints": transaction_fingerprints,
                "sync_status": "success",
            }
            if sync_result.get("error"):
                success_status_kwargs["sync_error_message"] = sync_result["error"]
            update_import_transaction_sync_status(
                connection,
                **success_status_kwargs,
            )
        elif sync_result["status"] == "needs_reconnect":
            update_import_transaction_sync_status(
                connection,
                transaction_fingerprints=transaction_fingerprints,
                sync_status="needs_reconnect",
                sync_error_message="needs_reconnect",
            )
        else:
            update_import_transaction_sync_status(
                connection,
                transaction_fingerprints=transaction_fingerprints,
                sync_status="failed",
                sync_error_message=sync_result.get("error"),
            )
        delete_import_draft_transactions(
            connection,
            import_job_id=import_job_id,
            draft_ids=[str(draft["id"]) for draft in merged_drafts],
        )
        self.cleanup_service.delete_temp_pdf_for_job(
            connection,
            workspace_id=workspace_id,
            job_id=import_job_id,
        )
        remaining_draft_count = count_new_import_draft_transactions(
            connection,
            import_job_id=import_job_id,
        )
        update_import_job_status(
            connection,
            job_id=import_job_id,
            status=(
                ImportJobStatus.COMPLETED.value
                if remaining_draft_count == 0
                else ImportJobStatus.REVIEW.value
            ),
            completed_at=(
                datetime.now(timezone.utc)
                if remaining_draft_count == 0
                else None
            ),
        )
        refresh_import_job_aggregates(
            connection,
            workspace_id=workspace_id,
            job_id=import_job_id,
        )

        return {
            "approved_count": len(created_transactions),
            "sync_success": sync_result["sync_success"],
            "sync_failed": sync_result["sync_failed"],
            "sync_status": sync_result["status"],
            "sync_error_message": sync_result.get("error"),
            "draft_ids": [str(draft["id"]) for draft in merged_drafts],
        }

    def reject_review_transactions(
        self,
        connection,
        *,
        workspace_id: str,
        import_job_id: str,
        draft_ids: list[str],
    ):
        if not get_import_review_summary(
            connection,
            workspace_id=workspace_id,
            job_id=import_job_id,
        ):
            return None

        normalized_ids = self._normalize_draft_ids(draft_ids, None)
        deleted_rows = reject_import_draft_transactions(
            connection,
            import_job_id=import_job_id,
            draft_ids=normalized_ids,
        )
        increment_import_job_rejected_count(
            connection,
            job_id=import_job_id,
            rejected_count=len(deleted_rows),
        )
        remaining_draft_count = count_new_import_draft_transactions(
            connection,
            import_job_id=import_job_id,
        )
        update_import_job_status(
            connection,
            job_id=import_job_id,
            status=(
                ImportJobStatus.COMPLETED.value
                if remaining_draft_count == 0
                else ImportJobStatus.REVIEW.value
            ),
            completed_at=(
                datetime.now(timezone.utc)
                if remaining_draft_count == 0
                else None
            ),
        )

        return {
            "rejected_count": len(deleted_rows),
            "draft_ids": [str(row["id"]) for row in deleted_rows],
        }

    def get_history_payload(self, connection, *, workspace_id: str):
        jobs = list_import_history(
            connection,
            workspace_id=workspace_id,
        )

        return {
            "jobs": [self._serialize_history_job(job) for job in jobs],
        }

    def get_history_detail_payload(self, connection, *, workspace_id: str, job_id: str):
        job = get_import_history_detail(
            connection,
            workspace_id=workspace_id,
            job_id=job_id,
        )

        if not job:
            return None

        unsynced_transactions = list_retryable_import_transactions(
            connection,
            workspace_id=workspace_id,
            import_job_id=job_id,
        )
        payload = self._serialize_history_job(job)
        payload["sync_success_count"] = payload["sync_success"]
        payload["sync_failed_count"] = payload["sync_failed"]
        payload["unsynced_count"] = len(unsynced_transactions)
        payload["unsynced_transactions"] = [
            self._serialize_unsynced_transaction(transaction)
            for transaction in unsynced_transactions[:50]
        ]

        return payload

    def retry_sync_transactions(
        self,
        connection,
        *,
        workspace: dict,
        current_user: dict,
        workspace_id: str,
        import_job_id: str,
        sheet_source_id: str | None = None,
        sheet_name: str | None = None,
    ):
        job = get_import_history_detail(
            connection,
            workspace_id=workspace_id,
            job_id=import_job_id,
        )

        if not job:
            return None

        retryable_transactions = list_retryable_import_transactions(
            connection,
            workspace_id=workspace_id,
            import_job_id=import_job_id,
        )
        skipped_success = count_successful_import_transactions(
            connection,
            workspace_id=workspace_id,
            import_job_id=import_job_id,
        )

        if not retryable_transactions:
            return {
                "job_id": import_job_id,
                "retried_count": 0,
                "sync_success": 0,
                "sync_failed": 0,
                "skipped_success": skipped_success,
                "status": "skipped",
                "sync_status": "skipped",
                "message": "Tidak ada transaksi yang perlu disinkronkan ulang.",
            }

        target_sheet = self._resolve_import_target_sheet(
            connection,
            workspace=workspace,
            current_user=current_user,
            workspace_id=workspace_id,
            sheet_source_id=sheet_source_id,
            sheet_name=sheet_name,
        )
        self._log_import_event(
            "smart_import.retry_sync.started",
            job_id=import_job_id,
            sheet_source_id=str(target_sheet["source"]["id"]),
            sheet_name=target_sheet["sheet_name"],
            unsynced_count=len(retryable_transactions),
        )
        resolved_retry_source_dana = self.spreadsheet_value_resolver.resolve_source_dana_for_append(
            connection,
            workspace_id=workspace_id,
            provider="Blu",
        )
        sync_result = self.spreadsheet_sync_service.sync_import_transactions(
            connection,
            workspace=workspace,
            current_user=current_user,
            approved_transactions=retryable_transactions,
            target_sheet_source=target_sheet["source"],
            target_sheet_name=target_sheet["sheet_name"],
            user_name=self._resolve_import_user_name(
                connection,
                current_user=current_user,
                workspace_id=workspace_id,
                workspace=workspace,
            ),
            source_dana=resolved_retry_source_dana,
            job_id=import_job_id,
        )
        transaction_ids = [
            str(transaction["id"])
            for transaction in retryable_transactions
        ]

        if sync_result["status"] == "success":
            success_status_kwargs = {
                "transaction_ids": transaction_ids,
                "sync_status": "success",
            }
            if sync_result.get("error"):
                success_status_kwargs["sync_error_message"] = sync_result["error"]
            update_import_transaction_sync_status_by_ids(
                connection,
                **success_status_kwargs,
            )
            self._log_import_event(
                "smart_import.retry_sync.completed",
                job_id=import_job_id,
                sync_success=sync_result["sync_success"],
                sync_failed=sync_result["sync_failed"],
            )
        elif sync_result["status"] == "needs_reconnect":
            update_import_transaction_sync_status_by_ids(
                connection,
                transaction_ids=transaction_ids,
                sync_status="needs_reconnect",
                sync_error_message="needs_reconnect",
            )
            self._log_import_event(
                "smart_import.retry_sync.failed",
                job_id=import_job_id,
                reason="needs_reconnect",
            )
        else:
            update_import_transaction_sync_status_by_ids(
                connection,
                transaction_ids=transaction_ids,
                sync_status="failed",
                sync_error_message=sync_result.get("error"),
            )
            self._log_import_event(
                "smart_import.retry_sync.failed",
                job_id=import_job_id,
                reason=sync_result.get("error") or sync_result["status"],
            )

        refresh_import_job_aggregates(
            connection,
            workspace_id=workspace_id,
            job_id=import_job_id,
        )

        return {
            "job_id": import_job_id,
            "retried_count": len(retryable_transactions),
            "sync_success": sync_result["sync_success"],
            "sync_failed": sync_result["sync_failed"],
            "skipped_success": skipped_success,
            "status": (
                "completed"
                if sync_result["status"] == "success"
                else sync_result["status"]
            ),
            "sync_status": sync_result["status"],
            "sync_error_message": sync_result.get("error"),
        }

    def _normalize_draft_ids(self, draft_ids: list[str], item_updates: list[dict] | None):
        normalized_ids = [str(draft_id) for draft_id in draft_ids if str(draft_id).strip()]

        for item in item_updates or []:
            draft_id = str(item.get("draft_id", "")).strip()
            if draft_id and draft_id not in normalized_ids:
                normalized_ids.append(draft_id)

        return normalized_ids

    def _resolve_import_user_name(
        self,
        connection,
        *,
        current_user: dict,
        workspace_id: str,
        workspace: dict,
    ) -> str:
        resolved_name = self.spreadsheet_value_resolver.resolve_user_name_for_append(
            connection,
            workspace_id=workspace_id,
            current_user=current_user,
        )

        if resolved_name != "User":
            return resolved_name

        for candidate in (workspace.get("owner_name"), workspace.get("name")):
            normalized_candidate = str(candidate or "").strip()
            if normalized_candidate:
                return normalized_candidate

        return resolved_name

    def _merge_review_item_updates(self, draft_transactions: list[dict], *, item_updates: list[dict]):
        updates_by_id = {
            str(item["draft_id"]): item
            for item in item_updates
            if item.get("draft_id")
        }

        merged_drafts = []

        for draft in draft_transactions:
            draft_id = str(draft["id"])
            update = updates_by_id.get(draft_id, {})
            merged_drafts.append({
                "id": draft_id,
                "transaction_fingerprint": draft["transaction_fingerprint"],
                "datetime": draft["datetime"],
                "merchant_original": draft["merchant_original"],
                "merchant_normalized": draft["merchant_normalized"],
                "merchant_display": self.merchant_normalizer.normalize(
                    draft["merchant_original"]
                )["merchant_display"],
                "amount": float(draft["amount"]),
                "direction": draft["direction"],
                "transaction_type": draft["transaction_type"],
                "review_group": draft["review_group"],
                "raw_text": draft["raw_text"],
                "category": str(update.get("category", draft.get("category", ""))),
                "notes": str(update.get("notes", draft.get("notes", ""))),
            })

        return merged_drafts

    def _resolve_final_sheet_source_id(
        self,
        connection,
        *,
        workspace: dict,
        current_user: dict,
    ) -> str:
        fallback_sheet_id = str(workspace.get("google_sheet_id") or "").strip()

        if not fallback_sheet_id:
            raise MissingGoogleSheetSourceError()

        oauth_connection = get_active_google_oauth_connection(
            connection,
            workspace_id=str(workspace["id"]),
            user_id=current_user["sub"],
        )
        sheet_source = ensure_import_google_sheet_source(
            connection,
            workspace_id=str(workspace["id"]),
            oauth_connection_id=(str(oauth_connection["id"]) if oauth_connection else None),
            sheet_id=fallback_sheet_id,
        )

        if not sheet_source:
            raise MissingGoogleSheetSourceError()

        return str(sheet_source["id"])

    def _resolve_import_target_sheet(
        self,
        connection,
        *,
        workspace: dict,
        current_user: dict,
        workspace_id: str,
        sheet_source_id: str | None,
        sheet_name: str | None,
    ) -> dict:
        normalized_source_id = str(sheet_source_id or "").strip()
        normalized_sheet_name = str(sheet_name or "").strip()

        if not normalized_source_id or not normalized_sheet_name:
            raise MissingTargetSheetError()

        sheet_source = get_google_sheet_source(
            connection,
            workspace_id=workspace_id,
            source_id=normalized_source_id,
        )

        if not sheet_source:
            raise MissingTargetSheetError()

        oauth_connection = get_active_google_oauth_connection(
            connection,
            workspace_id=str(workspace["id"]),
            user_id=current_user["sub"],
        )

        if not oauth_connection or not oauth_connection.get("access_token_encrypted"):
            raise MissingGoogleSheetSourceError()

        try:
            access_token = decrypt_text(oauth_connection["access_token_encrypted"])
            header_rows = read_sheet_values(
                access_token=access_token,
                spreadsheet_id=sheet_source["sheet_id"],
                range_name=self._build_header_range(normalized_sheet_name),
            )
        except (GoogleSheetsClientError, ValueError) as exc:
            raise InvalidTargetSheetHeaderError() from exc

        self._validate_import_target_header(header_rows[0] if header_rows else [])

        return {
            "source": sheet_source,
            "sheet_name": normalized_sheet_name,
        }

    def _validate_import_target_header(self, header: list[str]):
        canonical_header = {
            canonicalize_header(column)
            for column in header
            if str(column or "").strip()
        }
        missing_columns = [
            column
            for column in REQUIRED_IMPORT_TARGET_COLUMNS
            if column not in canonical_header
        ]

        if missing_columns:
            raise InvalidTargetSheetHeaderError()

    def _build_header_range(self, sheet_name: str) -> str:
        escaped_sheet_name = str(sheet_name or "").strip().replace("'", "''")
        return f"'{escaped_sheet_name}'!1:1"

    def _build_review_filters(self, draft_transactions: list[dict]):
        review_group_counts: dict[str, int] = {}

        for transaction in draft_transactions:
            review_group = str(transaction.get("review_group", "")).strip()
            if review_group:
                review_group_counts[review_group] = review_group_counts.get(review_group, 0) + 1

        filters = [
            {
                "id": "all",
                "label": "Semua",
                "count": len(draft_transactions),
            },
        ]

        for review_group in sorted(review_group_counts.keys()):
            filters.append({
                "id": f"group:{review_group}",
                "label": review_group,
                "count": review_group_counts[review_group],
            })

        filters.append({
            "id": "needs-review",
            "label": "Perlu Review",
            "count": sum(
                1 for transaction in draft_transactions
                if not str(transaction.get("category", "")).strip()
            ),
        })

        return filters

    def _serialize_history_job(self, job: dict):
        return {
            "job_id": str(job["id"]),
            "filename": job["filename"],
            "provider": job["provider"],
            "status": job["status"],
            "import_time": job["created_at"],
            "transactions_found": int(job.get("transactions_found", 0) or 0),
            "new_transactions": int(job.get("new_transactions", 0) or 0),
            "existing_transactions": int(job.get("existing_transactions", 0) or 0),
            "approved_transactions": int(job.get("approved_transactions", 0) or 0),
            "rejected_transactions": int(job.get("rejected_transactions", 0) or 0),
            "sync_success": int(job.get("sync_success", 0) or 0),
            "sync_failed": int(job.get("sync_failed", 0) or 0),
            "sync_success_count": int(job.get("sync_success", 0) or 0),
            "sync_failed_count": int(job.get("sync_failed", 0) or 0),
            "unsynced_count": int(job.get("retryable_sync_count", 0) or 0),
            "retryable_sync_count": int(job.get("retryable_sync_count", 0) or 0),
            "needs_reconnect": bool(job.get("needs_reconnect", False)),
            "pdf_status": (
                "already_deleted"
                if job.get("temp_file_deleted_at")
                else "available"
            ),
        }

    def _serialize_unsynced_transaction(self, transaction: dict):
        return {
            "id": str(transaction["id"]),
            "date": transaction.get("date") or "",
            "transaction_name": (
                transaction.get("merchant_display")
                or transaction.get("merchant_normalized")
                or ""
            ),
            "category": transaction.get("category") or "",
            "amount": float(transaction.get("amount", 0) or 0),
            "source_dana": transaction.get("source_dana") or "Blu",
            "sync_status": transaction.get("sync_status") or "pending",
            "sync_error_message": transaction.get("sync_error_message"),
        }
