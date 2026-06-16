from typing import BinaryIO

from app.imports.models.import_models import ImportPreviewItem
from app.imports.models.import_models import (
    ImportDraftTransaction,
    ImportJobStatus,
    ImportUploadResult,
    ParsedImportResult,
)
from app.imports.parsers.blu_pdf_parser import BluPdfParser
from app.imports.repositories.import_repository import (
    approve_import_draft_transactions,
    create_import_draft_transactions,
    create_import_job,
    get_existing_transaction_fingerprints,
    get_import_review_summary,
    list_import_draft_transactions,
    reject_import_draft_transactions,
    update_import_job_summary,
)
from app.imports.services.incremental_import_engine import IncrementalImportEngine
from app.imports.utils.fingerprint import build_transaction_fingerprint
from app.imports.utils.merchant_normalizer import MerchantNormalizer


class ImportService:
    def __init__(self):
        self.incremental_engine = IncrementalImportEngine()
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
        )

        return ImportUploadResult(
            job_id=str(job["id"]),
            provider=job["provider"],
            status=job["status"],
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
        workspace_id: str,
        import_job_id: str,
        draft_ids: list[str],
        item_updates: list[dict] | None = None,
    ):
        if not get_import_review_summary(
            connection,
            workspace_id=workspace_id,
            job_id=import_job_id,
        ):
            return None

        normalized_ids = self._normalize_draft_ids(draft_ids, item_updates)
        updates_by_id = {
            str(item["draft_id"]): {
                "category": str(item.get("category", "")),
                "notes": str(item.get("notes", "")),
            }
            for item in (item_updates or [])
            if item.get("draft_id")
        }

        updated_rows = approve_import_draft_transactions(
            connection,
            import_job_id=import_job_id,
            draft_ids=normalized_ids,
            updates_by_id=updates_by_id,
        )

        return {
            "approved_count": len(updated_rows),
            "draft_ids": [str(row["id"]) for row in updated_rows],
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

        return {
            "rejected_count": len(deleted_rows),
            "draft_ids": [str(row["id"]) for row in deleted_rows],
        }

    def _normalize_draft_ids(self, draft_ids: list[str], item_updates: list[dict] | None):
        normalized_ids = [str(draft_id) for draft_id in draft_ids if str(draft_id).strip()]

        for item in item_updates or []:
            draft_id = str(item.get("draft_id", "")).strip()
            if draft_id and draft_id not in normalized_ids:
                normalized_ids.append(draft_id)

        return normalized_ids

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
