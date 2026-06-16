from typing import BinaryIO
from datetime import datetime, timezone

from app.imports.models.import_models import ImportPreviewItem
from app.imports.models.import_models import (
    ImportDraftTransaction,
    ImportJobStatus,
    ImportUploadResult,
    ParsedImportResult,
)
from app.imports.parsers.blu_pdf_parser import BluPdfParser
from app.imports.repositories.final_transaction_repository import (
    create_import_transactions,
    list_retryable_import_transactions,
    serialize_import_transaction_row,
    update_import_transaction_sync_status,
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
    update_import_job_status,
    update_import_job_summary,
)
from app.imports.services.cleanup_service import ImportCleanupService
from app.imports.services.incremental_import_engine import IncrementalImportEngine
from app.imports.services.spreadsheet_sync_service import SpreadsheetSyncService
from app.imports.utils.fingerprint import build_transaction_fingerprint
from app.imports.utils.merchant_normalizer import MerchantNormalizer
from app.imports.utils.temp_storage import delete_temp_import_file, save_temp_import_file
from app.repositories.google_oauth_repository import get_active_google_oauth_connection
from app.repositories.google_sheet_source_repository import ensure_import_google_sheet_source


class ImportService:
    def __init__(self):
        self.cleanup_service = ImportCleanupService()
        self.incremental_engine = IncrementalImportEngine()
        self.merchant_normalizer = MerchantNormalizer()
        self.spreadsheet_sync_service = SpreadsheetSyncService()

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
        provider = self.detect_provider(file.filename or "")
        job = create_import_job(
            connection,
            workspace_id=workspace_id,
            provider=provider,
            filename=file.filename or "uploaded-file",
            status=ImportJobStatus.UPLOADED.value,
        )
        temp_file = save_temp_import_file(
            job_id=str(job["id"]),
            filename=file.filename or "uploaded-file.pdf",
            source_file=file.file,
        )
        set_import_job_temp_file(
            connection,
            job_id=str(job["id"]),
            temp_file_path=temp_file["path"],
            expires_at=temp_file["expires_at"],
        )
        try:
            update_import_job_status(
                connection,
                job_id=str(job["id"]),
                status=ImportJobStatus.PARSING.value,
            )
            parsed_result = self.enrich_transactions(
                self.parse(file.file, provider=provider)
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
                job_id=str(job["id"]),
                transactions_found=len(parsed_result.transactions),
                new_transactions=len(new_transactions),
                existing_transactions=len(existing_transactions),
                status=ImportJobStatus.REVIEW.value,
            )
        except Exception:
            delete_temp_import_file(temp_file["path"])
            raise

        return ImportUploadResult(
            job_id=str(job["id"]),
            provider=parsed_result.provider or job["provider"],
            status=ImportJobStatus.REVIEW,
            transactions_found=len(parsed_result.transactions),
            new_transactions=len(new_transactions),
            existing_transactions=len(existing_transactions),
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

        final_sheet_source_id = self._resolve_final_sheet_source_id(
            connection,
            workspace=workspace,
            current_user=current_user,
        )
        final_transaction_rows = [
            serialize_import_transaction_row(
                workspace_id=workspace_id,
                sheet_source_id=final_sheet_source_id,
                import_job_id=import_job_id,
                user_name=current_user.get("name") or current_user.get("email") or "User",
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
        sync_result = self.spreadsheet_sync_service.sync_import_transactions(
            connection,
            workspace=workspace,
            current_user=current_user,
            approved_transactions=merged_drafts,
        )
        transaction_fingerprints = [
            draft["transaction_fingerprint"]
            for draft in merged_drafts
        ]
        if sync_result["status"] == "success":
            update_import_transaction_sync_status(
                connection,
                transaction_fingerprints=transaction_fingerprints,
                sync_status="success",
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

        return self._serialize_history_job(job)

    def retry_sync_transactions(
        self,
        connection,
        *,
        workspace: dict,
        current_user: dict,
        workspace_id: str,
        import_job_id: str,
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
            sync_statuses=["failed", "needs_reconnect"],
        )

        if not retryable_transactions:
            return {
                "job_id": import_job_id,
                "retried_count": 0,
                "sync_success": 0,
                "sync_failed": 0,
                "sync_status": "skipped",
            }

        sync_result = self.spreadsheet_sync_service.sync_import_transactions(
            connection,
            workspace=workspace,
            current_user=current_user,
            approved_transactions=retryable_transactions,
        )
        transaction_fingerprints = [
            str(transaction["transaction_fingerprint"])
            for transaction in retryable_transactions
        ]

        if sync_result["status"] == "success":
            update_import_transaction_sync_status(
                connection,
                transaction_fingerprints=transaction_fingerprints,
                sync_status="success",
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
            "sync_status": sync_result["status"],
        }

    def _normalize_draft_ids(self, draft_ids: list[str], item_updates: list[dict] | None):
        normalized_ids = [str(draft_id) for draft_id in draft_ids if str(draft_id).strip()]

        for item in item_updates or []:
            draft_id = str(item.get("draft_id", "")).strip()
            if draft_id and draft_id not in normalized_ids:
                normalized_ids.append(draft_id)

        return normalized_ids

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
            raise ValueError("Workspace does not have an active Google Sheet source")

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
            raise ValueError("Workspace does not have an active Google Sheet source")

        return str(sheet_source["id"])

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
            "retryable_sync_count": int(job.get("retryable_sync_count", 0) or 0),
            "needs_reconnect": bool(job.get("needs_reconnect", False)),
            "pdf_status": (
                "already_deleted"
                if job.get("temp_file_deleted_at")
                else "available"
            ),
        }
