import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


os.environ.setdefault("JWT_SECRET", "test-secret")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.repositories.transaction_repository import batch_upsert_transactions


def _row(row_number: int, fingerprint: str, normalized_hash: str) -> dict:
    return {
        "workspace_id": "workspace-1",
        "sheet_source_id": "source-1",
        "external_row_key": f"row-{row_number}",
        "row_number": row_number,
        "payload": {
            "canonical_fingerprint": fingerprint,
            "canonical_fingerprint_date": f"date-{fingerprint}",
            "normalized_hash": normalized_hash,
        },
    }


class BatchUpsertTransactionsTestCase(unittest.TestCase):
    @patch("app.repositories.transaction_repository.get_transaction_ids_by_external_row_keys", return_value=[])
    @patch("app.repositories.transaction_repository.bulk_update_transactions_by_id", return_value=0)
    @patch("app.repositories.transaction_repository.bulk_update_transactions", return_value=0)
    @patch("app.repositories.transaction_repository.bulk_insert_transactions")
    @patch("app.repositories.transaction_repository.get_existing_transactions_by_canonical_fingerprint", return_value={})
    @patch("app.repositories.transaction_repository.get_existing_transaction_hashes", return_value={})
    def test_duplicate_canonical_fingerprint_in_payload_is_skipped(
        self,
        _existing_hashes,
        _canonical_matches,
        bulk_insert,
        _bulk_update,
        _bulk_rekey,
        _transaction_ids,
    ):
        payloads = [
            _row(2, "duplicate-fingerprint", "hash-1"),
            _row(3, "duplicate-fingerprint", "hash-2"),
            _row(4, "unique-fingerprint", "hash-3"),
        ]
        bulk_insert.side_effect = lambda _connection, rows, chunk_size: len(rows)

        result = batch_upsert_transactions(
            object(),
            workspace_id="workspace-1",
            sheet_source_id="source-1",
            payloads=payloads,
        )

        inserted_rows = bulk_insert.call_args.args[1]
        self.assertEqual([payloads[0], payloads[2]], inserted_rows)
        self.assertEqual(2, result["inserted"])
        self.assertEqual(1, result["skipped"])
        self.assertEqual(1, result["skipped_duplicates"])
        self.assertEqual(0, result["failed"])
        self.assertEqual("DUPLICATE_BATCH", result["details"]["skipped"][0]["reason"])

    @patch("app.repositories.transaction_repository.get_transaction_ids_by_external_row_keys", return_value=[])
    @patch("app.repositories.transaction_repository.bulk_update_transactions_by_id", return_value=1)
    @patch("app.repositories.transaction_repository.bulk_update_transactions", return_value=0)
    @patch("app.repositories.transaction_repository.bulk_insert_transactions")
    @patch("app.repositories.transaction_repository.get_existing_transactions_by_canonical_fingerprint")
    @patch("app.repositories.transaction_repository.get_existing_transaction_hashes", return_value={})
    def test_existing_database_fingerprint_is_not_inserted_twice(
        self,
        _existing_hashes,
        canonical_matches,
        bulk_insert,
        _bulk_update,
        bulk_rekey,
        _transaction_ids,
    ):
        existing_row = _row(2, "existing-fingerprint", "hash-existing")
        unique_row = _row(3, "unique-fingerprint", "hash-unique")
        canonical_matches.return_value = {
            "existing-fingerprint": {
                "id": "transaction-1",
                "source_origin": "google_sheet",
                "sheet_source_id": "source-1",
            },
        }
        bulk_insert.side_effect = lambda _connection, rows, chunk_size: len(rows)

        result = batch_upsert_transactions(
            object(),
            workspace_id="workspace-1",
            sheet_source_id="source-1",
            payloads=[existing_row, unique_row],
        )

        self.assertEqual([unique_row], bulk_insert.call_args.args[1])
        rekey_rows = bulk_rekey.call_args.args[1]
        self.assertEqual("transaction-1", rekey_rows[0]["existing_transaction_id"])
        self.assertEqual(1, result["inserted"])
        self.assertEqual(1, result["updated"])
        self.assertEqual(0, result["failed"])


if __name__ == "__main__":
    unittest.main()
