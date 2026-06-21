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
    get_registered_transaction_fingerprint_statuses,
    register_rejected_transaction_fingerprints,
    register_transaction_fingerprints,
)
from app.imports.repositories.import_repository import (
    count_import_history,
    create_import_draft_transactions,
    create_import_job,
    count_new_import_draft_transactions,
    delete_import_draft_transactions,
    get_import_history_detail,
    get_import_review_filter_counts,
    list_import_history,
    list_import_history_paginated,
    get_import_review_summary,
    increment_import_job_rejected_count,
    list_import_draft_transactions,
    list_import_draft_transactions_paginated,
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
from app.imports.utils.fingerprint import (
    build_canonical_fingerprint,
    build_canonical_fingerprint_date,
    build_transaction_fingerprint,
    normalize_owner_name,
)
from app.imports.utils.merchant_normalizer import MerchantNormalizer
from app.imports.utils.provider_detection import detect_import_provider
from app.imports.utils.temp_storage import delete_temp_import_file, save_temp_import_file
from app.repositories.google_oauth_repository import get_active_google_oauth_connection
from app.repositories.google_sheet_source_repository import (
    ensure_import_google_sheet_source,
    get_google_sheet_source,
)
from app.repositories.transaction_repository import (
    get_existing_transactions_by_canonical_fingerprint,
)
from app.security.encryption import decrypt_text
from app.services.google_sheets_client import GoogleSheetsClientError, read_sheet_values
from app.services.sheet_header_validator import canonicalize_header


logger = logging.getLogger(__name__)

MAX_IMPORT_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
DEFAULT_IMPORT_REVIEW_PAGE_SIZE = 100
DEFAULT_IMPORT_HISTORY_PAGE_SIZE = 20
MAX_IMPORT_PAGE_SIZE = 100
DEFAULT_IMPORT_CATEGORIES = (
    "Bills",
    "Education",
    "Entertainment",
    "Family",
    "Food",
    "Groceries",
    "Health",
    "Household",
    "Income",
    "Other",
    "Saving",
    "Shopping",
    "Subscription",
    "Transport",
)
MISSING_SPREADSHEET_TARGET_MESSAGE = (
    "Target Spreadsheet belum dikonfigurasi. "
    "Transaksi sudah tersimpan di Omon dan dapat dikirim setelah Google Sheet terhubung."
)
ALLOWED_IMPORT_EXTENSIONS = {".pdf"}
ALLOWED_IMPORT_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/acrobat",
    "applications/vnd.pdf",
    "text/pdf",
}
GENERIC_IMPORT_CONTENT_TYPES = {
    "application/octet-stream",
    "binary/octet-stream",
}


class MissingGoogleSheetSourceError(Exception):
    error_code = "missing_google_sheet_source"
    message = "Tujuan Google Spreadsheet belum siap. Hubungkan Google dulu di Settings sebelum approval dilanjutkan."

    def to_response(self) -> dict:
        return {
            "status": "failed",
            "error_code": self.error_code,
            "message": self.message,
        }


class MissingTargetSheetError(Exception):
    error_code = "missing_target_sheet"
    message = "Pilih spreadsheet dan tab tujuan dulu sebelum approval dijalankan."

    def to_response(self) -> dict:
        return {
            "status": "failed",
            "error_code": self.error_code,
            "message": self.message,
        }


class InvalidTargetSheetHeaderError(Exception):
    error_code = "invalid_target_sheet_header"
    message = "Tab tujuan belum siap menerima salinan transaksi karena format kolomnya belum sesuai."

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
            enriched_transactions.append(enriched_transaction)

        return ParsedImportResult(
            provider=parsed_result.provider,
            transactions=enriched_transactions,
        )

    def apply_statement_owner(
        self,
        parsed_result: ParsedImportResult,
        *,
        statement_owner: str,
        source_fund: str = "Blu",
    ) -> ParsedImportResult:
        normalized_statement_owner = normalize_owner_name(statement_owner)
        owner_transactions = []

        for transaction in parsed_result.transactions:
            merchant_name = (
                transaction.get("merchant_display")
                or transaction.get("merchant_normalized")
                or transaction.get("merchant_original")
                or ""
            )
            owner_transaction = {
                **transaction,
                "statement_owner": normalized_statement_owner,
                "source_fund": source_fund,
            }
            owner_transaction["transaction_fingerprint"] = build_transaction_fingerprint(
                owner_name=normalized_statement_owner,
                source_dana=source_fund,
                datetime_value=str(owner_transaction.get("datetime", "")),
                merchant_normalized=str(owner_transaction.get("merchant_normalized", "")),
                amount=owner_transaction.get("amount", 0),
                direction=str(owner_transaction.get("direction", "")),
            )
            owner_transaction["canonical_fingerprint"] = build_canonical_fingerprint(
                owner_name=normalized_statement_owner,
                datetime_value=owner_transaction.get("datetime", ""),
                merchant_name=str(merchant_name),
                amount=owner_transaction.get("amount", 0),
                direction=str(owner_transaction.get("direction", "")),
                source_fund=source_fund,
            )
            owner_transaction["canonical_fingerprint_date"] = build_canonical_fingerprint_date(
                owner_name=normalized_statement_owner,
                datetime_value=owner_transaction.get("datetime", ""),
                merchant_name=str(merchant_name),
                amount=owner_transaction.get("amount", 0),
                direction=str(owner_transaction.get("direction", "")),
                source_fund=source_fund,
            )
            owner_transactions.append(owner_transaction)

        return ParsedImportResult(
            provider=parsed_result.provider,
            transactions=owner_transactions,
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
        canonical_fingerprints = [
            str(transaction.get("canonical_fingerprint", ""))
            for transaction in parsed_result.transactions
            if transaction.get("canonical_fingerprint")
        ]
        canonical_fingerprint_dates = [
            str(transaction.get("canonical_fingerprint_date", ""))
            for transaction in parsed_result.transactions
            if transaction.get("canonical_fingerprint_date")
        ]
        fingerprint_statuses = get_registered_transaction_fingerprint_statuses(
            connection,
            workspace_id=workspace_id,
            transaction_fingerprints=transaction_fingerprints,
        )
        existing_fingerprints = set(fingerprint_statuses.keys())
        canonical_matches = get_existing_transactions_by_canonical_fingerprint(
            connection,
            workspace_id=workspace_id,
            canonical_fingerprints=canonical_fingerprints,
            canonical_fingerprint_dates=canonical_fingerprint_dates,
        )

        return ParsedImportResult(
            provider=parsed_result.provider,
            transactions=self.incremental_engine.apply(
                [
                    {
                        **transaction,
                        "is_existing": bool(
                            str(transaction.get("transaction_fingerprint", "")) in existing_fingerprints
                            or str(transaction.get("canonical_fingerprint", "")) in canonical_matches
                            or str(transaction.get("canonical_fingerprint_date", "")) in canonical_matches
                        ),
                        "registry_status": (
                            fingerprint_statuses.get(str(transaction.get("transaction_fingerprint", "")))
                            or (
                                "already_recorded"
                                if (
                                    str(transaction.get("canonical_fingerprint", "")) in canonical_matches
                                    or str(transaction.get("canonical_fingerprint_date", "")) in canonical_matches
                                )
                                else None
                            )
                        ),
                    }
                    for transaction in parsed_result.transactions
                ],
                existing_fingerprints=existing_fingerprints,
                fingerprint_statuses=fingerprint_statuses,
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
                canonical_fingerprint=str(transaction.get("canonical_fingerprint", "")),
                canonical_fingerprint_date=str(transaction.get("canonical_fingerprint_date", "")),
                statement_owner=str(transaction.get("statement_owner", "")),
                source_fund=str(transaction.get("source_fund", "Blu") or "Blu"),
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

    def receive_upload(self, connection, *, workspace_id: str, file, statement_owner: str) -> ImportUploadResult:
        normalized_statement_owner = normalize_owner_name(statement_owner)

        if not normalized_statement_owner:
            return ImportUploadResult(
                job_id="",
                provider="unknown",
                statement_owner="",
                status=ImportJobStatus.FAILED,
                error_code="invalid_statement_owner",
                message="Pemilik statement wajib dipilih sebelum upload.",
                error="Pemilik statement wajib dipilih sebelum upload.",
            )

        filename = file.filename or "uploaded-file"
        filename_provider = self.detect_provider(filename)
        job = create_import_job(
            connection,
            workspace_id=workspace_id,
            provider=filename_provider,
            filename=filename,
            statement_owner=normalized_statement_owner,
            status=ImportJobStatus.UPLOADED.value,
        )
        job_id = str(job["id"])
        self._log_import_event(
            "smart_import.upload.started",
            job_id=job_id,
            filename=filename,
            file_size=self._get_upload_file_size(file),
        )
        upload_validation_error = self._validate_upload_file(
            connection,
            job_id=job_id,
            provider=filename_provider,
            file=file,
        )
        if upload_validation_error:
            return upload_validation_error

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
                    error_code="temp_file_missing",
                    user_error="File import sementara tidak ditemukan.",
                )

            try:
                with temp_path.open("rb") as temp_pdf:
                    extraction = BluPdfParser().extract_pdf_metadata(temp_pdf)
            except Exception:
                return self._fail_upload(
                    connection,
                    job_id=job_id,
                    provider=filename_provider,
                    detection_source=(
                        "filename"
                        if filename_provider != "unknown"
                        else "unknown"
                    ),
                    page_count=0,
                    extracted_text_length=0,
                    stage="pdf_extraction",
                    reason="PDF extraction raised an error",
                    error_code="invalid_pdf",
                    user_error="PDF tidak valid atau gagal dibaca.",
                )

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
                    error_code="unreadable_pdf",
                    user_error="PDF tidak memiliki text layer atau gagal dibaca.",
                )

            if provider != "blu":
                return self._fail_upload(
                    connection,
                    job_id=job_id,
                    provider=provider,
                    detection_source=detection_source,
                    page_count=extraction["page_count"],
                    extracted_text_length=extraction["extracted_text_length"],
                    stage="provider_detection",
                    reason="Uploaded PDF provider is not supported",
                    error_code="unsupported_provider",
                    user_error=(
                        "File belum didukung. Saat ini Import Transaksi hanya "
                        "mendukung PDF e-Statement Blu."
                    ),
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
            parsed_result = self.apply_statement_owner(
                parsed_result,
                statement_owner=normalized_statement_owner,
                source_fund="Blu",
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
                    error_code="no_parseable_transactions",
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
            rejected_transactions = [
                transaction for transaction in existing_transactions
                if transaction.get("registry_status") == "rejected"
            ]
            no_new_transactions = (
                len(parsed_result.transactions) > 0
                and len(new_transactions) == 0
            )
            terminal_status = (
                ImportJobStatus.COMPLETED
                if no_new_transactions
                else ImportJobStatus.REVIEW
            )
            update_import_job_summary(
                connection,
                job_id=job_id,
                transactions_found=len(parsed_result.transactions),
                new_transactions=len(new_transactions),
                existing_transactions=len(existing_transactions),
                status=terminal_status.value,
            )
            if no_new_transactions:
                update_import_job_status(
                    connection,
                    job_id=job_id,
                    status=ImportJobStatus.COMPLETED.value,
                    completed_at=datetime.now(timezone.utc),
                )
            self._log_import_event(
                "smart_import.incremental.completed",
                job_id=job_id,
                transactions_found=len(parsed_result.transactions),
                new_transactions=len(new_transactions),
                existing_transactions=len(existing_transactions),
                rejected_transactions=len(rejected_transactions),
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
            statement_owner=normalized_statement_owner,
            status=terminal_status,
            transactions_found=len(parsed_result.transactions),
            new_transactions=len(new_transactions),
            existing_transactions=len(existing_transactions),
            rejected_transactions=len(rejected_transactions),
            no_new_transactions=no_new_transactions,
            message=(
                "Semua transaksi dalam PDF ini sudah pernah diproses atau ditolak."
                if len(parsed_result.transactions) > 0 and len(new_transactions) == 0
                else None
            ),
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
        error_code: str,
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
            error_code=error_code,
            message=user_error,
            error=user_error,
            preview=[],
        )

    def _get_upload_file_size(self, file) -> int | None:
        size = getattr(file, "size", None)

        if isinstance(size, int):
            return size

        file_object = getattr(file, "file", None)

        if file_object is None:
            return None

        try:
            current_position = file_object.tell()
            file_object.seek(0, 2)
            size = file_object.tell()
            file_object.seek(current_position)
        except (AttributeError, OSError, ValueError):
            return None

        return size

    def _validate_upload_file(
        self,
        connection,
        *,
        job_id: str,
        provider: str,
        file,
    ) -> ImportUploadResult | None:
        filename = str(getattr(file, "filename", "") or "").strip()
        extension = Path(filename).suffix.lower()
        content_type = str(getattr(file, "content_type", "") or "").strip().lower()
        file_size = self._get_upload_file_size(file)

        if extension not in ALLOWED_IMPORT_EXTENSIONS:
            return self._fail_upload(
                connection,
                job_id=job_id,
                provider=provider,
                detection_source="filename" if provider != "unknown" else "unknown",
                page_count=0,
                extracted_text_length=0,
                stage="upload_validation",
                reason="Uploaded file extension is not supported",
                error_code="invalid_file_extension",
                user_error="File harus berformat PDF (.pdf).",
            )

        if file_size is not None and file_size > MAX_IMPORT_UPLOAD_SIZE_BYTES:
            return self._fail_upload(
                connection,
                job_id=job_id,
                provider=provider,
                detection_source="filename" if provider != "unknown" else "unknown",
                page_count=0,
                extracted_text_length=0,
                stage="upload_validation",
                reason="Uploaded PDF exceeds the maximum allowed size",
                error_code="file_too_large",
                user_error="Ukuran PDF terlalu besar. Maksimal upload adalah 10 MB.",
            )

        if (
            content_type
            and content_type not in ALLOWED_IMPORT_CONTENT_TYPES
            and content_type not in GENERIC_IMPORT_CONTENT_TYPES
        ):
            return self._fail_upload(
                connection,
                job_id=job_id,
                provider=provider,
                detection_source="filename" if provider != "unknown" else "unknown",
                page_count=0,
                extracted_text_length=0,
                stage="upload_validation",
                reason="Uploaded file content-type is not a supported PDF content-type",
                error_code="invalid_content_type",
                user_error="File yang diupload bukan PDF yang valid.",
            )

        if not self._has_pdf_magic_bytes(file):
            return self._fail_upload(
                connection,
                job_id=job_id,
                provider=provider,
                detection_source="filename" if provider != "unknown" else "unknown",
                page_count=0,
                extracted_text_length=0,
                stage="upload_validation",
                reason="Uploaded file does not start with PDF magic bytes",
                error_code="invalid_pdf_signature",
                user_error="File PDF tidak valid atau isinya bukan PDF.",
            )

        return None

    def _has_pdf_magic_bytes(self, file) -> bool:
        file_object = getattr(file, "file", None)

        if file_object is None:
            return False

        try:
            current_position = file_object.tell()
            file_object.seek(0)
            file_header = file_object.read(4)
            file_object.seek(current_position)
        except (AttributeError, OSError, ValueError):
            return False

        return file_header == b"%PDF"

    def _log_import_event(self, event_name: str, **fields):
        logger.info(
            event_name,
            extra={"smart_import": fields},
        )

    def get_review_payload(
        self,
        connection,
        *,
        workspace_id: str,
        job_id: str,
        limit: int = DEFAULT_IMPORT_REVIEW_PAGE_SIZE,
        offset: int = 0,
    ):
        summary = get_import_review_summary(
            connection,
            workspace_id=workspace_id,
            job_id=job_id,
        )

        if not summary:
            return None

        safe_limit = self._normalize_page_limit(
            limit,
            default_limit=DEFAULT_IMPORT_REVIEW_PAGE_SIZE,
        )
        safe_offset = self._normalize_page_offset(offset)
        filter_counts = get_import_review_filter_counts(
            connection,
            import_job_id=job_id,
            status="new",
        ) or {}
        draft_transactions = list_import_draft_transactions_paginated(
            connection,
            import_job_id=job_id,
            status="new",
            limit=safe_limit,
            offset=safe_offset,
        )

        serialized_transactions = [
            self._serialize_review_transaction(transaction, summary=summary)
            for transaction in draft_transactions
        ]
        total_count = int(filter_counts.get("total_count", 0) or 0)

        return {
            "summary": {
                "job_id": str(summary["id"]),
                "filename": summary["filename"],
                "provider": summary["provider"],
                "statement_owner": summary.get("statement_owner", ""),
                "source_fund": "Blu",
                "transactions_found": summary["transactions_found"],
                "new_transactions": summary["new_transactions"],
                "existing_transactions": summary["existing_transactions"],
                "created_at": summary["created_at"],
            },
            "filters": self._build_review_filters(filter_counts),
            "pagination": self._build_pagination_payload(
                total=total_count,
                limit=safe_limit,
                offset=safe_offset,
            ),
            "draft_transactions": serialized_transactions,
        }

    def get_category_options_payload(self, connection, *, workspace_id: str):
        historical_categories = list_workspace_transaction_categories(
            connection,
            workspace_id=workspace_id,
        )
        categories_by_key = {
            category.casefold(): category
            for category in DEFAULT_IMPORT_CATEGORIES
        }

        for category in historical_categories:
            normalized_category = str(category or "").strip()
            if normalized_category:
                categories_by_key.setdefault(
                    normalized_category.casefold(),
                    normalized_category,
                )

        return {
            "categories": sorted(
                categories_by_key.values(),
                key=lambda category: (category.casefold(), category),
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
        approval_plan = self.prepare_review_approval(
            connection,
            workspace=workspace,
            current_user=current_user,
            workspace_id=workspace_id,
            import_job_id=import_job_id,
            draft_ids=draft_ids,
            item_updates=item_updates,
            sheet_source_id=sheet_source_id,
            sheet_name=sheet_name,
        )
        if approval_plan is None:
            return None

        persistence_result = self.persist_review_approval(
            connection,
            workspace_id=workspace_id,
            import_job_id=import_job_id,
            approval_plan=approval_plan,
        )
        sync_result = self.execute_sync_plan(
            connection,
            workspace=workspace,
            current_user=current_user,
            sync_plan=persistence_result["sync_plan"],
        )
        final_sync_result = self.record_review_sync_result(
            connection,
            workspace_id=workspace_id,
            import_job_id=import_job_id,
            transaction_fingerprints=persistence_result["transaction_fingerprints"],
            sync_result=sync_result,
        )

        return {
            "approved_count": persistence_result["approved_count"],
            "skipped_existing_count": persistence_result["skipped_existing_count"],
            "skipped_rejected_count": persistence_result["skipped_rejected_count"],
            "draft_ids": persistence_result["draft_ids"],
            **final_sync_result,
        }

    def prepare_review_approval(
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
                "review_summary": review_summary,
                "merged_drafts": [],
                "target_sheet": None,
                "resolved_source_dana": None,
                "resolved_user_name": None,
                "final_transaction_rows": [],
            }

        fingerprint_statuses = get_registered_transaction_fingerprint_statuses(
            connection,
            workspace_id=workspace_id,
            transaction_fingerprints=[
                str(draft["transaction_fingerprint"])
                for draft in merged_drafts
            ],
        )
        skipped_existing_drafts = [
            draft for draft in merged_drafts
            if fingerprint_statuses.get(str(draft["transaction_fingerprint"])) == "approved"
        ]
        skipped_rejected_drafts = [
            draft for draft in merged_drafts
            if fingerprint_statuses.get(str(draft["transaction_fingerprint"])) == "rejected"
        ]
        approval_drafts = [
            draft for draft in merged_drafts
            if str(draft["transaction_fingerprint"]) not in fingerprint_statuses
        ]

        normalized_source_id = str(sheet_source_id or "").strip()
        normalized_sheet_name = str(sheet_name or "").strip()
        target_sheet_source = None
        if normalized_source_id and normalized_sheet_name:
            target_sheet_source = get_google_sheet_source(
                connection,
                workspace_id=workspace_id,
                source_id=normalized_source_id,
            )
        resolved_source_dana = self.spreadsheet_value_resolver.resolve_source_dana_for_append(
            connection,
            workspace_id=workspace_id,
            provider="Blu",
        )
        resolved_user_name = normalize_owner_name(review_summary.get("statement_owner", "")) or self._resolve_import_user_name(
            connection,
            current_user=current_user,
            workspace_id=workspace_id,
            workspace=workspace,
        )
        final_transaction_rows = [
            serialize_import_transaction_row(
                workspace_id=workspace_id,
                sheet_source_id=(
                    str(target_sheet_source["id"])
                    if target_sheet_source
                    else None
                ),
                import_job_id=import_job_id,
                user_name=resolved_user_name,
                source_fund=resolved_source_dana,
                transaction=draft,
            )
            for draft in approval_drafts
        ]

        return {
            "review_summary": review_summary,
            "selected_drafts": merged_drafts,
            "approval_drafts": approval_drafts,
            "skipped_existing_drafts": skipped_existing_drafts,
            "skipped_rejected_drafts": skipped_rejected_drafts,
            "target_sheet_source": target_sheet_source,
            "target_sheet_source_id": normalized_source_id or None,
            "target_sheet_name": normalized_sheet_name or None,
            "resolved_source_dana": resolved_source_dana,
            "resolved_user_name": resolved_user_name,
            "final_transaction_rows": final_transaction_rows,
        }

    def persist_review_approval(
        self,
        connection,
        *,
        workspace_id: str,
        import_job_id: str,
        approval_plan: dict,
    ):
        selected_drafts = approval_plan.get("selected_drafts", [])
        if not selected_drafts:
            return {
                "approved_count": 0,
                "draft_ids": [],
                "skipped_existing_count": 0,
                "skipped_rejected_count": 0,
                "transaction_fingerprints": [],
                "sync_plan": {
                    "approved_transactions": [],
                    "target_sheet_source": None,
                    "target_sheet_name": None,
                    "user_name": None,
                    "source_dana": None,
                    "job_id": import_job_id,
                },
            }

        fingerprint_statuses = get_registered_transaction_fingerprint_statuses(
            connection,
            workspace_id=workspace_id,
            transaction_fingerprints=[
                str(draft["transaction_fingerprint"])
                for draft in selected_drafts
            ],
        )
        skipped_existing_drafts = [
            draft for draft in selected_drafts
            if fingerprint_statuses.get(str(draft["transaction_fingerprint"])) == "approved"
        ]
        skipped_rejected_drafts = [
            draft for draft in selected_drafts
            if fingerprint_statuses.get(str(draft["transaction_fingerprint"])) == "rejected"
        ]
        approval_drafts = [
            draft for draft in selected_drafts
            if str(draft["transaction_fingerprint"]) not in fingerprint_statuses
        ]
        approval_fingerprints = {
            str(draft["transaction_fingerprint"])
            for draft in approval_drafts
        }
        created_transactions = create_import_transactions(
            connection,
            rows=[
                row for row in approval_plan["final_transaction_rows"]
                if str(row["import_transaction_fingerprint"]) in approval_fingerprints
            ],
        )
        created_fingerprints = {
            str(transaction["import_transaction_fingerprint"])
            for transaction in created_transactions
        }
        created_drafts = [
            draft for draft in approval_drafts
            if str(draft["transaction_fingerprint"]) in created_fingerprints
        ]
        race_skipped_existing_drafts = [
            draft for draft in approval_drafts
            if str(draft["transaction_fingerprint"]) not in created_fingerprints
        ]
        register_transaction_fingerprints(
            connection,
            workspace_id=workspace_id,
            rows=[
                {
                    "transaction_fingerprint": draft["transaction_fingerprint"],
                    "provider": approval_plan["review_summary"]["provider"],
                }
                for draft in created_drafts
            ],
        )
        transaction_fingerprints = [
            draft["transaction_fingerprint"]
            for draft in created_drafts
        ]
        delete_import_draft_transactions(
            connection,
            import_job_id=import_job_id,
            draft_ids=[str(draft["id"]) for draft in selected_drafts],
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
            "draft_ids": [str(draft["id"]) for draft in selected_drafts],
            "skipped_existing_count": (
                len(skipped_existing_drafts)
                + len(race_skipped_existing_drafts)
            ),
            "skipped_rejected_count": len(skipped_rejected_drafts),
            "transaction_fingerprints": transaction_fingerprints,
            "sync_plan": {
                "approved_transactions": created_drafts,
                "target_sheet_source": approval_plan["target_sheet_source"],
                "target_sheet_source_id": approval_plan["target_sheet_source_id"],
                "target_sheet_name": approval_plan["target_sheet_name"],
                "user_name": approval_plan["resolved_user_name"],
                "source_dana": approval_plan["resolved_source_dana"],
                "job_id": import_job_id,
            },
        }

    def execute_sync_plan(
        self,
        connection,
        *,
        workspace: dict,
        current_user: dict,
        sync_plan: dict,
    ):
        approved_transactions = sync_plan.get("approved_transactions") or []
        if not approved_transactions:
            return {
                "status": "skipped",
                "sync_success": 0,
                "sync_failed": 0,
                "source_id": None,
                "error": None,
            }

        target_sheet_source = sync_plan.get("target_sheet_source") or {}
        target_source_id = str(
            sync_plan.get("target_sheet_source_id")
            or target_sheet_source.get("id")
            or ""
        ).strip()
        target_sheet_name = str(sync_plan.get("target_sheet_name") or "").strip()
        if not target_source_id or not target_sheet_name:
            return {
                "status": "skipped",
                "sync_success": 0,
                "sync_failed": len(approved_transactions),
                "source_id": None,
                "error": MISSING_SPREADSHEET_TARGET_MESSAGE,
            }

        try:
            target_sheet = self._resolve_import_target_sheet(
                connection,
                workspace=workspace,
                current_user=current_user,
                workspace_id=str(workspace["id"]),
                sheet_source_id=target_source_id,
                sheet_name=target_sheet_name,
            )
        except MissingGoogleSheetSourceError as exc:
            return {
                "status": "needs_reconnect",
                "sync_success": 0,
                "sync_failed": len(approved_transactions),
                "source_id": target_source_id,
                "error": exc.message,
            }
        except (MissingTargetSheetError, InvalidTargetSheetHeaderError) as exc:
            return {
                "status": "failed",
                "sync_success": 0,
                "sync_failed": len(approved_transactions),
                "source_id": target_source_id or None,
                "error": exc.message,
            }

        self._log_import_event(
            "smart_import.spreadsheet_sync.started",
            job_id=sync_plan.get("job_id"),
            sheet_source_id=str(target_sheet["source"]["id"]),
            sheet_name=target_sheet["sheet_name"],
            row_count=len(approved_transactions),
        )

        try:
            sync_result = self.spreadsheet_sync_service.sync_import_transactions(
                connection,
                workspace=workspace,
                current_user=current_user,
                approved_transactions=approved_transactions,
                target_sheet_source=target_sheet["source"],
                target_sheet_name=target_sheet["sheet_name"],
                user_name=sync_plan["user_name"],
                source_dana=sync_plan["source_dana"],
                job_id=sync_plan.get("job_id"),
            )
        except Exception as exc:  # pragma: no cover - defensive boundary
            logger.exception(
                "smart_import.spreadsheet_sync.unhandled",
                extra={
                    "smart_import": {
                        "job_id": sync_plan.get("job_id"),
                        "sheet_name": sync_plan.get("target_sheet_name"),
                        "row_count": len(approved_transactions),
                    },
                },
            )
            sync_result = {
                "status": "failed",
                "sync_success": 0,
                "sync_failed": len(approved_transactions),
                "source_id": (
                    str(sync_plan["target_sheet_source"]["id"])
                    if sync_plan.get("target_sheet_source")
                    else None
                ),
                "error": str(exc),
            }

        if sync_result["status"] == "success":
            self._log_import_event(
                "smart_import.spreadsheet_sync.completed",
                job_id=sync_plan.get("job_id"),
                success_count=sync_result["sync_success"],
                failed_count=sync_result["sync_failed"],
            )
        else:
            self._log_import_event(
                "smart_import.spreadsheet_sync.failed",
                job_id=sync_plan.get("job_id"),
                sheet_name=sync_plan.get("target_sheet_name"),
                reason=sync_result.get("error") or sync_result["status"],
            )

        return sync_result

    def record_review_sync_result(
        self,
        connection,
        *,
        workspace_id: str,
        import_job_id: str,
        transaction_fingerprints: list[str],
        sync_result: dict,
    ):
        if sync_result["status"] == "success":
            success_status_kwargs = {
                "transaction_fingerprints": transaction_fingerprints,
                "sync_status": "success",
            }
            if sync_result.get("error"):
                success_status_kwargs["sync_error_message"] = sync_result["error"]
            update_import_transaction_sync_status(
                connection,
                workspace_id=workspace_id,
                **success_status_kwargs,
            )
        elif sync_result["status"] == "needs_reconnect":
            update_import_transaction_sync_status(
                connection,
                workspace_id=workspace_id,
                transaction_fingerprints=transaction_fingerprints,
                sync_status="needs_reconnect",
                sync_error_message="needs_reconnect",
            )
        elif sync_result["status"] == "failed":
            update_import_transaction_sync_status(
                connection,
                workspace_id=workspace_id,
                transaction_fingerprints=transaction_fingerprints,
                sync_status="failed",
                sync_error_message=sync_result.get("error"),
            )
        elif sync_result["status"] == "skipped":
            update_import_transaction_sync_status(
                connection,
                workspace_id=workspace_id,
                transaction_fingerprints=transaction_fingerprints,
                sync_status="pending",
                sync_error_message=sync_result.get("error"),
            )

        refresh_import_job_aggregates(
            connection,
            workspace_id=workspace_id,
            job_id=import_job_id,
        )

        return {
            "ledger_saved": bool(transaction_fingerprints),
            "sync_success": sync_result["sync_success"],
            "sync_failed": sync_result["sync_failed"],
            "sync_status": sync_result["status"],
            "sync_error_message": sync_result.get("error"),
            "sheet_delivery": {
                "status": sync_result["status"],
                "success_count": sync_result["sync_success"],
                "pending_or_failed_count": sync_result["sync_failed"],
                "message": sync_result.get("error"),
            },
        }

    def reject_review_transactions(
        self,
        connection,
        *,
        workspace_id: str,
        import_job_id: str,
        draft_ids: list[str],
    ):
        review_summary = get_import_review_summary(
            connection,
            workspace_id=workspace_id,
            job_id=import_job_id,
        )
        if not review_summary:
            return None

        normalized_ids = self._normalize_draft_ids(draft_ids, None)
        selected_drafts = list_import_draft_transactions_by_ids(
            connection,
            import_job_id=import_job_id,
            draft_ids=normalized_ids,
        )
        fingerprint_statuses = get_registered_transaction_fingerprint_statuses(
            connection,
            workspace_id=workspace_id,
            transaction_fingerprints=[
                str(draft["transaction_fingerprint"])
                for draft in selected_drafts
            ],
        )
        rejectable_drafts = [
            draft for draft in selected_drafts
            if str(draft["transaction_fingerprint"]) not in fingerprint_statuses
        ]
        skipped_existing_count = sum(
            fingerprint_statuses.get(str(draft["transaction_fingerprint"])) == "approved"
            for draft in selected_drafts
        )
        skipped_rejected_count = sum(
            fingerprint_statuses.get(str(draft["transaction_fingerprint"])) == "rejected"
            for draft in selected_drafts
        )
        register_rejected_transaction_fingerprints(
            connection,
            workspace_id=workspace_id,
            rows=[
                {
                    "transaction_fingerprint": draft["transaction_fingerprint"],
                    "provider": review_summary["provider"],
                }
                for draft in rejectable_drafts
            ],
        )
        deleted_rows = reject_import_draft_transactions(
            connection,
            import_job_id=import_job_id,
            draft_ids=normalized_ids,
        )
        increment_import_job_rejected_count(
            connection,
            job_id=import_job_id,
            rejected_count=len(rejectable_drafts),
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
            "rejected_count": len(rejectable_drafts),
            "skipped_existing_count": skipped_existing_count,
            "skipped_rejected_count": skipped_rejected_count,
            "draft_ids": [str(row["id"]) for row in deleted_rows],
        }

    def get_history_payload(
        self,
        connection,
        *,
        workspace_id: str,
        limit: int = DEFAULT_IMPORT_HISTORY_PAGE_SIZE,
        offset: int = 0,
    ):
        safe_limit = self._normalize_page_limit(
            limit,
            default_limit=DEFAULT_IMPORT_HISTORY_PAGE_SIZE,
        )
        safe_offset = self._normalize_page_offset(offset)
        total_jobs = count_import_history(
            connection,
            workspace_id=workspace_id,
        )
        jobs = list_import_history_paginated(
            connection,
            workspace_id=workspace_id,
            limit=safe_limit,
            offset=safe_offset,
        )

        return {
            "jobs": [self._serialize_history_job(job) for job in jobs],
            "pagination": self._build_pagination_payload(
                total=total_jobs,
                limit=safe_limit,
                offset=safe_offset,
            ),
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
        retry_plan = self.prepare_retry_sync(
            connection,
            workspace=workspace,
            current_user=current_user,
            workspace_id=workspace_id,
            import_job_id=import_job_id,
            sheet_source_id=sheet_source_id,
            sheet_name=sheet_name,
        )
        if not retry_plan:
            return None
        if retry_plan.get("status") == "skipped":
            return retry_plan

        sync_result = self.execute_sync_plan(
            connection,
            workspace=workspace,
            current_user=current_user,
            sync_plan=retry_plan["sync_plan"],
        )

        return self.record_retry_sync_result(
            connection,
            workspace_id=workspace_id,
            import_job_id=import_job_id,
            retry_plan=retry_plan,
            sync_result=sync_result,
        )

    def prepare_retry_sync(
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
        resolved_retry_user_name = self._resolve_import_user_name(
            connection,
            current_user=current_user,
            workspace_id=workspace_id,
            workspace=workspace,
        )
        transaction_ids = [
            str(transaction["id"])
            for transaction in retryable_transactions
        ]

        return {
            "job_id": import_job_id,
            "retryable_transactions": retryable_transactions,
            "transaction_ids": transaction_ids,
            "skipped_success": skipped_success,
            "sync_plan": {
                "approved_transactions": retryable_transactions,
                "target_sheet_source": target_sheet["source"],
                "target_sheet_name": target_sheet["sheet_name"],
                "user_name": resolved_retry_user_name,
                "source_dana": resolved_retry_source_dana,
                "job_id": import_job_id,
            },
        }

    def record_retry_sync_result(
        self,
        connection,
        *,
        workspace_id: str,
        import_job_id: str,
        retry_plan: dict,
        sync_result: dict,
    ):
        if sync_result["status"] == "success":
            success_status_kwargs = {
                "transaction_ids": retry_plan["transaction_ids"],
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
                transaction_ids=retry_plan["transaction_ids"],
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
                transaction_ids=retry_plan["transaction_ids"],
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
            "retried_count": len(retry_plan["retryable_transactions"]),
            "sync_success": sync_result["sync_success"],
            "sync_failed": sync_result["sync_failed"],
            "skipped_success": retry_plan["skipped_success"],
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
                "canonical_fingerprint": draft.get("canonical_fingerprint", ""),
                "canonical_fingerprint_date": draft.get("canonical_fingerprint_date", ""),
                "statement_owner": draft.get("statement_owner", ""),
                "source_fund": draft.get("source_fund", "") or "Blu",
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

    def _build_review_filters(self, filter_counts: dict):
        filters = [
            {
                "id": "all",
                "label": "Semua",
                "count": int(filter_counts.get("total_count", 0) or 0),
            },
        ]

        for group in filter_counts.get("review_groups", []) or []:
            review_group = str(group.get("review_group", "")).strip()
            if not review_group:
                continue
            filters.append({
                "id": f"group:{review_group}",
                "label": review_group,
                "count": int(group.get("count", 0) or 0),
            })

        filters.append({
            "id": "needs-review",
            "label": "Perlu Review",
            "count": int(filter_counts.get("needs_review_count", 0) or 0),
        })

        return filters

    def _serialize_review_transaction(self, transaction: dict, *, summary: dict):
        return {
            "id": str(transaction["id"]),
            "statement_owner": transaction.get("statement_owner", "") or summary.get("statement_owner", ""),
            "source_fund": transaction.get("source_fund", "") or "Blu",
            "canonical_fingerprint": transaction.get("canonical_fingerprint", ""),
            "canonical_fingerprint_date": transaction.get("canonical_fingerprint_date", ""),
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

    def _normalize_page_limit(self, limit: int | None, *, default_limit: int) -> int:
        if limit is None:
            return default_limit

        return max(1, min(int(limit), MAX_IMPORT_PAGE_SIZE))

    def _normalize_page_offset(self, offset: int | None) -> int:
        if offset is None:
            return 0

        return max(0, int(offset))

    def _build_pagination_payload(self, *, total: int, limit: int, offset: int):
        return {
            "total": int(total),
            "limit": int(limit),
            "offset": int(offset),
            "page": (offset // limit) + 1 if limit else 1,
            "has_next": offset + limit < total,
            "has_previous": offset > 0,
        }

    def _serialize_history_job(self, job: dict):
        return {
            "job_id": str(job["id"]),
            "filename": job["filename"],
            "provider": job["provider"],
            "statement_owner": job.get("statement_owner") or "",
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
            "spreadsheet_unconfigured": bool(job.get("spreadsheet_unconfigured", False)),
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
