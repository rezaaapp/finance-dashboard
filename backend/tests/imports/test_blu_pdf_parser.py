import io
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
fake_psycopg = types.ModuleType("psycopg")
fake_psycopg_rows = types.ModuleType("psycopg.rows")
fake_psycopg_rows.dict_row = object()
sys.modules.setdefault("psycopg", fake_psycopg)
sys.modules.setdefault("psycopg.rows", fake_psycopg_rows)

from app.imports.parsers.blu_pdf_parser import BluPdfParser
from app.imports.services.import_service import ImportService
from app.imports.utils.fingerprint import build_transaction_fingerprint
from app.imports.utils.merchant_normalizer import MerchantNormalizer
from app.imports.models.import_models import ParsedImportResult


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "blu_statement_sample.pdf"


class NamedBytesIO(io.BytesIO):
    def __init__(self, content: bytes, name: str):
        super().__init__(content)
        self.filename = name
        self.file = self


class BluPdfParserTestCase(unittest.TestCase):
    def setUp(self):
        self.parser = BluPdfParser()
        self.merchant_normalizer = MerchantNormalizer()
        self.fixture_bytes = FIXTURE_PATH.read_bytes()

    def test_parser_detects_sections_and_review_groups(self):
        transactions = self.parser.parse(io.BytesIO(self.fixture_bytes)).transactions

        self.assertEqual("blu", self.parser.provider)
        self.assertEqual("bluAccount", transactions[0]["review_group"])
        self.assertEqual("Makan Bulanan", transactions[1]["review_group"])
        self.assertEqual("Makan Bulanan", transactions[2]["review_group"])
        self.assertEqual("Operasional Pacaran", transactions[3]["review_group"])

    def test_parser_extracts_standardized_transaction_fields(self):
        transactions = self.parser.parse(io.BytesIO(self.fixture_bytes)).transactions

        self.assertEqual(4, len(transactions))
        self.assertEqual("14/06/2026 09:15", transactions[0]["datetime"])
        self.assertEqual("Top Up dari Bank Lain", transactions[0]["merchant_original"])
        self.assertEqual(1500000.0, transactions[0]["amount"])
        self.assertEqual("income", transactions[0]["direction"])
        self.assertEqual("CR", transactions[0]["transaction_type"])
        self.assertIn("Fore Coffee", transactions[1]["merchant_original"])
        self.assertEqual(28000.0, transactions[1]["amount"])

    def test_import_service_calls_blu_parser_and_returns_preview(self):
        fake_upload = NamedBytesIO(self.fixture_bytes, "blu-estatement-june.pdf")
        fake_job = {
            "id": "job-123",
            "provider": "blu",
            "status": "uploaded",
        }

        with patch("app.imports.services.import_service.create_import_job", return_value=fake_job), \
             patch("app.imports.services.import_service.get_existing_transaction_fingerprints", return_value=set()), \
             patch("app.imports.services.import_service.create_import_draft_transactions"), \
             patch("app.imports.services.import_service.update_import_job_summary"):
            result = ImportService().receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=fake_upload,
            )

        self.assertEqual("blu", result.provider)
        self.assertEqual("uploaded", result.status)
        self.assertEqual(4, result.transactions_found)
        self.assertEqual(4, result.new_transactions)
        self.assertEqual(0, result.existing_transactions)
        self.assertEqual(4, len(result.preview))
        self.assertEqual("14/06/2026 09:15", result.preview[0].datetime)
        self.assertEqual("Top Up dari Bank Lain", result.preview[0].merchant_original)
        self.assertEqual("Top Up dari Bank Lain", result.preview[0].merchant_normalized)

    def test_merchant_normalizer_produces_stable_output(self):
        self.assertEqual(
            {
                "merchant_original": "Fore Coffee 61715",
                "merchant_normalized": "Fore Coffee",
            },
            self.merchant_normalizer.normalize("  Fore   Coffee 61715 "),
        )
        self.assertEqual(
            {
                "merchant_original": "SUPERINDO BCY QR",
                "merchant_normalized": "SUPERINDO",
            },
            self.merchant_normalizer.normalize("SUPERINDO BCY QR"),
        )
        self.assertEqual(
            {
                "merchant_original": "jajanan ahmadi 000885",
                "merchant_normalized": "jajanan ahmadi",
            },
            self.merchant_normalizer.normalize("jajanan ahmadi 000885"),
        )

    def test_fingerprint_is_deterministic_for_same_transaction(self):
        fingerprint_a = build_transaction_fingerprint(
            source_dana="Blu",
            datetime_value="21/05/2026 17:54",
            merchant_normalized="Fore Coffee",
            amount=67200,
        )
        fingerprint_b = build_transaction_fingerprint(
            source_dana="Blu",
            datetime_value="21/05/2026 17:54",
            merchant_normalized="Fore Coffee",
            amount=67200,
        )

        self.assertEqual(fingerprint_a, fingerprint_b)

    def test_fingerprint_changes_when_datetime_amount_or_merchant_changes(self):
        baseline = build_transaction_fingerprint(
            source_dana="Blu",
            datetime_value="21/05/2026 17:54",
            merchant_normalized="Fore Coffee",
            amount=67200,
        )
        different_datetime = build_transaction_fingerprint(
            source_dana="Blu",
            datetime_value="21/05/2026 17:55",
            merchant_normalized="Fore Coffee",
            amount=67200,
        )
        different_amount = build_transaction_fingerprint(
            source_dana="Blu",
            datetime_value="21/05/2026 17:54",
            merchant_normalized="Fore Coffee",
            amount=67201,
        )
        different_merchant = build_transaction_fingerprint(
            source_dana="Blu",
            datetime_value="21/05/2026 17:54",
            merchant_normalized="Family Mart",
            amount=67200,
        )

        self.assertNotEqual(baseline, different_datetime)
        self.assertNotEqual(baseline, different_amount)
        self.assertNotEqual(baseline, different_merchant)

    def test_incremental_engine_marks_second_upload_as_existing(self):
        service = ImportService()
        fake_upload = NamedBytesIO(self.fixture_bytes, "blu-estatement-june.pdf")
        stored_fingerprints = set()
        stored_drafts = []
        job_counter = {"value": 0}

        def fake_create_import_job(_connection, **kwargs):
            job_counter["value"] += 1
            return {
                "id": f"job-{job_counter['value']}",
                "provider": kwargs["provider"],
                "status": kwargs["status"],
            }

        def fake_get_existing(_connection, **_kwargs):
            return set(stored_fingerprints)

        def fake_create_drafts(_connection, *, draft_transactions):
            stored_drafts.append(draft_transactions)

        with patch("app.imports.services.import_service.create_import_job", side_effect=fake_create_import_job), \
             patch("app.imports.services.import_service.get_existing_transaction_fingerprints", side_effect=fake_get_existing), \
             patch("app.imports.services.import_service.create_import_draft_transactions", side_effect=fake_create_drafts), \
             patch("app.imports.services.import_service.update_import_job_summary"):
            first_result = service.receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=NamedBytesIO(self.fixture_bytes, "blu-estatement-june.pdf"),
            )
            stored_fingerprints.update(
                draft["transaction_fingerprint"] for draft in stored_drafts[-1]
            )
            second_result = service.receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=NamedBytesIO(self.fixture_bytes, "blu-estatement-june.pdf"),
            )

        self.assertEqual(4, first_result.new_transactions)
        self.assertEqual(0, first_result.existing_transactions)
        self.assertEqual(4, second_result.existing_transactions)
        self.assertEqual(0, second_result.new_transactions)
        self.assertEqual([], second_result.preview)
        self.assertEqual([], stored_drafts[-1])

    def test_incremental_engine_supports_overlap_upload_previewing_only_new_rows(self):
        service = ImportService()
        first_half_transactions = ParsedImportResult(
            provider="blu",
            transactions=[
                {
                    "datetime": "01/06/2026 08:00",
                    "merchant_original": "Fore Coffee 61715",
                    "amount": 28000,
                    "direction": "expense",
                    "transaction_type": "DB",
                    "review_group": "Makan Bulanan",
                    "raw_text": "first-half-1",
                },
                {
                    "datetime": "15/06/2026 12:00",
                    "merchant_original": "SUPERINDO BCY QR",
                    "amount": 150000,
                    "direction": "expense",
                    "transaction_type": "DB",
                    "review_group": "Belanja Bulanan",
                    "raw_text": "first-half-2",
                },
            ],
        )
        full_month_transactions = ParsedImportResult(
            provider="blu",
            transactions=[
                *first_half_transactions.transactions,
                {
                    "datetime": "20/06/2026 19:00",
                    "merchant_original": "Family Mart 000885",
                    "amount": 45000,
                    "direction": "expense",
                    "transaction_type": "DB",
                    "review_group": "Makan Bulanan",
                    "raw_text": "full-month-3",
                },
                {
                    "datetime": "30/06/2026 09:30",
                    "merchant_original": "Top Up dari Bank Lain",
                    "amount": 500000,
                    "direction": "income",
                    "transaction_type": "CR",
                    "review_group": "bluAccount",
                    "raw_text": "full-month-4",
                },
            ],
        )
        parse_queue = [first_half_transactions, full_month_transactions]
        stored_fingerprints = set()
        stored_drafts = []
        job_counter = {"value": 0}

        def fake_create_import_job(_connection, **kwargs):
            job_counter["value"] += 1
            return {
                "id": f"job-{job_counter['value']}",
                "provider": kwargs["provider"],
                "status": kwargs["status"],
            }

        def fake_parse(_file, *, provider):
            self.assertEqual("blu", provider)
            return parse_queue.pop(0)

        def fake_get_existing(_connection, **_kwargs):
            return set(stored_fingerprints)

        def fake_create_drafts(_connection, *, draft_transactions):
            stored_drafts.append(draft_transactions)

        with patch.object(ImportService, "parse", side_effect=fake_parse), \
             patch("app.imports.services.import_service.create_import_job", side_effect=fake_create_import_job), \
             patch("app.imports.services.import_service.get_existing_transaction_fingerprints", side_effect=fake_get_existing), \
             patch("app.imports.services.import_service.create_import_draft_transactions", side_effect=fake_create_drafts), \
             patch("app.imports.services.import_service.update_import_job_summary"):
            first_result = service.receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=NamedBytesIO(b"first-half", "blu-first-half.pdf"),
            )
            stored_fingerprints.update(
                draft["transaction_fingerprint"] for draft in stored_drafts[-1]
            )
            second_result = service.receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=NamedBytesIO(b"full-month", "blu-full-month.pdf"),
            )

        self.assertEqual(2, first_result.new_transactions)
        self.assertEqual(0, first_result.existing_transactions)
        self.assertEqual(2, second_result.new_transactions)
        self.assertEqual(2, second_result.existing_transactions)
        self.assertEqual(2, len(second_result.preview))
        self.assertEqual("Family Mart 000885", second_result.preview[0].merchant_original)
        self.assertEqual("Family Mart", second_result.preview[0].merchant_normalized)
        self.assertEqual("Top Up dari Bank Lain", second_result.preview[1].merchant_original)
        self.assertEqual(2, len(stored_drafts[-1]))
        self.assertFalse(stored_drafts[-1][0]["is_existing"])
        self.assertFalse(stored_drafts[-1][1]["is_existing"])

    def test_review_payload_contains_only_new_transactions_and_filters(self):
        service = ImportService()
        review_summary = {
            "id": "job-1",
            "filename": "blu_statement_juni.pdf",
            "provider": "blu",
            "status": "uploaded",
            "transactions_found": 4,
            "new_transactions": 2,
            "existing_transactions": 2,
            "created_at": "2026-06-16T10:00:00Z",
        }
        draft_transactions = [
            {
                "id": "draft-1",
                "datetime": "01/06/2026 08:00",
                "merchant_original": "Fore Coffee 61715",
                "merchant_normalized": "Fore Coffee",
                "amount": 28000,
                "direction": "expense",
                "transaction_type": "DB",
                "review_group": "Makan Bulanan",
                "raw_text": "raw-1",
                "status": "new",
                "category": "",
                "notes": "",
            },
            {
                "id": "draft-2",
                "datetime": "02/06/2026 09:00",
                "merchant_original": "Top Up dari Bank Lain",
                "merchant_normalized": "Top Up dari Bank Lain",
                "amount": 500000,
                "direction": "income",
                "transaction_type": "CR",
                "review_group": "bluAccount",
                "raw_text": "raw-2",
                "status": "new",
                "category": "",
                "notes": "",
            },
        ]

        with patch("app.imports.services.import_service.get_import_review_summary", return_value=review_summary), \
             patch("app.imports.services.import_service.list_import_draft_transactions", return_value=draft_transactions):
            payload = service.get_review_payload(
                connection=object(),
                workspace_id="workspace-1",
                job_id="job-1",
            )

        self.assertEqual("blu_statement_juni.pdf", payload["summary"]["filename"])
        self.assertEqual(2, len(payload["draft_transactions"]))
        self.assertEqual(
            ["Semua", "Makan Bulanan", "bluAccount", "Perlu Review"],
            [filter_item["label"] for filter_item in payload["filters"]],
        )

    def test_approve_and_reject_review_transactions(self):
        service = ImportService()

        with patch("app.imports.services.import_service.get_import_review_summary", return_value={"id": "job-1"}), \
             patch("app.imports.services.import_service.approve_import_draft_transactions", return_value=[{"id": "draft-1"}]), \
             patch("app.imports.services.import_service.reject_import_draft_transactions", return_value=[{"id": "draft-2"}]):
            approve_result = service.approve_review_transactions(
                connection=object(),
                workspace_id="workspace-1",
                import_job_id="job-1",
                draft_ids=["draft-1"],
                item_updates=[{
                    "draft_id": "draft-1",
                    "category": "Makan",
                    "notes": "Approved manually",
                }],
            )
            reject_result = service.reject_review_transactions(
                connection=object(),
                workspace_id="workspace-1",
                import_job_id="job-1",
                draft_ids=["draft-2"],
            )

        self.assertEqual(1, approve_result["approved_count"])
        self.assertEqual(["draft-1"], approve_result["draft_ids"])
        self.assertEqual(1, reject_result["rejected_count"])
        self.assertEqual(["draft-2"], reject_result["draft_ids"])


if __name__ == "__main__":
    unittest.main()
