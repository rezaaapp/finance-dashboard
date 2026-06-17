import io
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DASHBOARD_USERNAME", "test-user")
os.environ.setdefault("DASHBOARD_PASSWORD", "test-password")
os.environ.setdefault("DASHBOARD_AUTH_TOKEN", "test-token")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("TOKEN_ENCRYPTION_SECRET", "test-secret")
os.environ.setdefault(
    "TOKEN_ENCRYPTION_KEY",
    "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
)
fake_psycopg = types.ModuleType("psycopg")
fake_psycopg_rows = types.ModuleType("psycopg.rows")
fake_psycopg_types = types.ModuleType("psycopg.types")
fake_psycopg_types_json = types.ModuleType("psycopg.types.json")
fake_psycopg_pool = types.ModuleType("psycopg_pool")
fake_dotenv = types.ModuleType("dotenv")
fake_httpx = types.ModuleType("httpx")
fake_psycopg_rows.dict_row = object()
fake_psycopg_types_json.Jsonb = lambda value: value
fake_dotenv.dotenv_values = lambda _path: {}
fake_httpx.HTTPError = Exception
fake_httpx.HTTPStatusError = Exception
fake_psycopg_pool.ConnectionPool = object
sys.modules.setdefault("psycopg", fake_psycopg)
sys.modules.setdefault("psycopg.rows", fake_psycopg_rows)
sys.modules.setdefault("psycopg.types", fake_psycopg_types)
sys.modules.setdefault("psycopg.types.json", fake_psycopg_types_json)
sys.modules.setdefault("psycopg_pool", fake_psycopg_pool)
sys.modules.setdefault("dotenv", fake_dotenv)
sys.modules.setdefault("httpx", fake_httpx)

from app.imports.parsers.blu_pdf_parser import BluPdfParser
from app.imports.repositories.final_transaction_repository import create_import_transactions
from app.imports.repositories.fingerprint_registry_repository import (
    register_transaction_fingerprints,
)
from app.imports.services.cleanup_service import ImportCleanupService
from app.imports.services.import_service import (
    ImportService,
    InvalidTargetSheetHeaderError,
    MissingGoogleSheetSourceError,
    MissingTargetSheetError,
)
from app.imports.services.spreadsheet_sync_service import SpreadsheetSyncService
from app.imports.utils.fingerprint import build_transaction_fingerprint
from app.imports.utils.merchant_normalizer import MerchantNormalizer
from app.imports.utils.provider_detection import detect_import_provider
from app.imports.models.import_models import ParsedImportResult


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "blu_statement_sample.pdf"
REAL_JUNE_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "blu_statement_june_real.pdf"


class NamedBytesIO(io.BytesIO):
    def __init__(self, content: bytes, name: str):
        super().__init__(content)
        self.filename = name
        self.file = self


class FakeReturningCursor:
    def __init__(self, returned_rows: list[dict]):
        self.returned_rows = list(returned_rows)
        self.executed = []
        self.fetchone_calls = 0
        self.fetchall_calls = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        self.fetchone_calls += 1
        return self.returned_rows.pop(0)

    def fetchall(self):
        self.fetchall_calls += 1
        raise AssertionError("create_import_transactions should not call fetchall")


class FakeReturningConnection:
    def __init__(self, cursor: FakeReturningCursor):
        self.cursor_instance = cursor
        self.cursor_calls = []

    def cursor(self, **kwargs):
        self.cursor_calls.append(kwargs)
        return self.cursor_instance


class BluPdfParserTestCase(unittest.TestCase):
    def setUp(self):
        self.parser = BluPdfParser()
        self.merchant_normalizer = MerchantNormalizer()
        self.fixture_bytes = FIXTURE_PATH.read_bytes()
        self.real_june_fixture_bytes = REAL_JUNE_FIXTURE_PATH.read_bytes()

    def test_create_import_transactions_returns_inserted_rows(self):
        cursor = FakeReturningCursor([
            {
                "id": "txn-1",
                "import_transaction_fingerprint": "fp-1",
                "sync_status": "pending",
            },
        ])
        connection = FakeReturningConnection(cursor)

        inserted_rows = create_import_transactions(
            connection,
            rows=[{
                "workspace_id": "workspace-1",
                "sheet_source_id": "sheet-source-1",
                "external_row_key": "fp-1",
                "row_number": None,
                "transaction_date": "2026-06-01",
                "transaction_time": "2026-06-01T08:00:00",
                "title": "Fore Coffee",
                "raw_category": "Makan",
                "amount": 28000,
                "source_fund": "Blu",
                "note": None,
                "direction": "expense",
                "raw_payload": {"merchant_original": "Fore Coffee 61715"},
                "normalized_hash": "fp-1",
                "user_name": "Reza",
                "import_job_id": "job-1",
                "import_transaction_fingerprint": "fp-1",
                "sync_status": "pending",
                "sync_error_message": None,
            }],
        )

        self.assertEqual(
            [{
                "id": "txn-1",
                "import_transaction_fingerprint": "fp-1",
                "sync_status": "pending",
            }],
            inserted_rows,
        )
        self.assertEqual(1, len(cursor.executed))
        self.assertIn("returning id, import_transaction_fingerprint, sync_status", cursor.executed[0][0])
        self.assertIn("on conflict (import_transaction_fingerprint)", cursor.executed[0][0])
        self.assertEqual(1, cursor.fetchone_calls)
        self.assertEqual(0, cursor.fetchall_calls)

    def test_create_import_transactions_empty_rows_returns_empty_list(self):
        cursor = FakeReturningCursor([])
        connection = FakeReturningConnection(cursor)

        self.assertEqual([], create_import_transactions(connection, rows=[]))
        self.assertEqual([], connection.cursor_calls)

    def test_register_transaction_fingerprints_empty_rows_returns_empty_list(self):
        cursor = FakeReturningCursor([])
        connection = FakeReturningConnection(cursor)

        self.assertEqual([], register_transaction_fingerprints(connection, rows=[]))
        self.assertEqual([], connection.cursor_calls)

    def test_register_transaction_fingerprints_returns_registered_rows(self):
        cursor = FakeReturningCursor([
            {
                "transaction_fingerprint": "fp-1",
                "provider": "blu",
                "approved_at": "2026-06-17T08:00:00Z",
                "created_at": "2026-06-17T08:00:00Z",
            },
        ])
        connection = FakeReturningConnection(cursor)

        registered_rows = register_transaction_fingerprints(
            connection,
            rows=[{
                "transaction_fingerprint": "fp-1",
                "provider": "blu",
            }],
        )

        self.assertEqual(
            [{
                "transaction_fingerprint": "fp-1",
                "provider": "blu",
                "approved_at": "2026-06-17T08:00:00Z",
                "created_at": "2026-06-17T08:00:00Z",
            }],
            registered_rows,
        )
        self.assertEqual(1, len(cursor.executed))
        self.assertIn("returning transaction_fingerprint, provider, approved_at, created_at", cursor.executed[0][0])
        self.assertIn("on conflict (transaction_fingerprint)", cursor.executed[0][0])
        self.assertEqual(1, cursor.fetchone_calls)
        self.assertEqual(0, cursor.fetchall_calls)

    def test_register_transaction_fingerprints_duplicate_uses_conflict_update(self):
        cursor = FakeReturningCursor([
            {
                "transaction_fingerprint": "fp-1",
                "provider": "blu",
                "approved_at": "2026-06-17T08:05:00Z",
                "created_at": "2026-06-17T08:00:00Z",
            },
        ])
        connection = FakeReturningConnection(cursor)

        register_transaction_fingerprints(
            connection,
            rows=[{
                "transaction_fingerprint": "fp-1",
                "provider": "blu",
            }],
        )

        self.assertIn("do update set", cursor.executed[0][0])
        self.assertIn("provider = excluded.provider", cursor.executed[0][0])
        self.assertIn("approved_at = excluded.approved_at", cursor.executed[0][0])

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

    def test_parser_supports_real_june_statement_text_pattern(self):
        lines = [
            "01 - 16 Jun 2026 21:15",
            "bluAccount - 0000 0000 2555",
            "05 Jun 2026",
            "16:58 SEABANK | 1780653530302275",
            "Transfer ke REZA PUTRA PRATAMA - 250.000,00 1.004,38",
            "06 Jun 2026",
            "08:00 bluSaving",
            "Dana Masuk dari bluSaving 250.000,00 251.004,38",
            "Saldo Awal / Initial Balance 1.004,38",
            "bluSpending - Belanja Bulanan",
            "07 Jun 2026",
            "18:20 SUPERINDO BCY QR 000885002709750 |",
            "02941272241224928998",
            "Pembayaran QRIS - 159.750,00 1.840.757,80",
            "Total Pengeluaran / Total Expense - 159.750,00",
            "bluSpending - Makan Bulanan",
            "10 Jun 2026",
            "18:10 Ayam Gepuk Pak Gembus, Ke M143872 |",
            "J2wouupDBSb6mc513120",
            "Pembayaran QRIS - 52.000,00 301.572,19",
            "bluSpending - Operasional Pacaran",
            "11 Jun 2026",
            "20:30 PARKIR QR 001122 |",
            "ABC123",
            "Pembayaran QRIS - 5.000,00 296.572,19",
            "Disclaimer",
            "BCA Digital",
        ]

        transactions = self.parser._parse_lines(lines)

        by_merchant = {
            transaction["merchant_original"]: transaction
            for transaction in transactions
        }
        superindo = next(
            transaction for transaction in transactions
            if "SUPERINDO" in transaction["merchant_original"]
        )
        ayam_gepuk = next(
            transaction for transaction in transactions
            if "Ayam Gepuk" in transaction["merchant_original"]
        )
        seabank = next(
            transaction for transaction in transactions
            if "SEABANK" in transaction["merchant_original"]
        )
        dana_masuk = next(
            transaction for transaction in transactions
            if "bluSaving" in transaction["merchant_original"]
            and transaction["direction"] == "income"
        )

        self.assertGreater(len(transactions), 0)
        self.assertEqual(
            {"bluAccount", "Belanja Bulanan", "Makan Bulanan", "Operasional Pacaran"},
            {transaction["review_group"] for transaction in transactions},
        )
        self.assertNotIn("Total Pengeluaran", " ".join(by_merchant.keys()))
        self.assertEqual(159750.0, superindo["amount"])
        self.assertEqual("expense", superindo["direction"])
        self.assertEqual("Belanja Bulanan", superindo["review_group"])
        self.assertEqual(52000.0, ayam_gepuk["amount"])
        self.assertEqual("expense", ayam_gepuk["direction"])
        self.assertEqual("Makan Bulanan", ayam_gepuk["review_group"])
        self.assertEqual(250000.0, seabank["amount"])
        self.assertEqual("expense", seabank["direction"])
        self.assertEqual("bluAccount", seabank["review_group"])
        self.assertEqual(250000.0, dana_masuk["amount"])
        self.assertEqual("income", dana_masuk["direction"])
        self.assertEqual("bluAccount", dana_masuk["review_group"])

    def test_provider_detection_supports_filename_and_content_markers(self):
        filename_detection = detect_import_provider(
            filename="bluAccount _ bluSpending_000000002555_01-16Juni2026.pdf",
        )
        content_detection = detect_import_provider(
            filename="statement.pdf",
            extracted_text="Ringkasan bluAccount | bluSpending dari BCA Digital",
        )

        self.assertEqual(
            {"provider": "blu", "detection_source": "filename"},
            filename_detection,
        )
        self.assertEqual(
            {"provider": "blu", "detection_source": "content"},
            content_detection,
        )

    def test_parser_supports_all_required_month_abbreviations(self):
        months = [
            ("Jan", "01"),
            ("Feb", "02"),
            ("Mar", "03"),
            ("Apr", "04"),
            ("Mei", "05"),
            ("May", "05"),
            ("Jun", "06"),
            ("Jul", "07"),
            ("Agu", "08"),
            ("Aug", "08"),
            ("Sep", "09"),
            ("Okt", "10"),
            ("Oct", "10"),
            ("Nov", "11"),
            ("Des", "12"),
            ("Dec", "12"),
        ]

        for month_name, expected_month in months:
            with self.subTest(month=month_name):
                transactions = self.parser._parse_lines([
                    "bluSpending - Makan Bulanan",
                    f"01 {month_name} 2026 Pembayaran QRIS",
                    "- 1.000,00 10.000,00",
                    "08:00",
                    "TEST MERCHANT 001",
                ])

                self.assertEqual(1, len(transactions))
                self.assertEqual(f"01/{expected_month}/2026 08:00", transactions[0]["datetime"])

    def test_parser_real_june_pdf_returns_transactions_and_expected_examples(self):
        result = self.parser.parse(io.BytesIO(self.real_june_fixture_bytes))
        transactions = result.transactions
        superindo = next(
            transaction for transaction in transactions
            if "SUPERINDO" in transaction["merchant_original"]
        )
        ayam_gepuk = next(
            transaction for transaction in transactions
            if "Ayam Gepuk" in transaction["merchant_original"]
        )
        seabank = next(
            transaction for transaction in transactions
            if "SEABANK" in transaction["merchant_original"]
        )
        dana_masuk = next(
            transaction for transaction in transactions
            if transaction["transaction_type"] == "Dana Masuk dari bluSaving"
        )

        self.assertGreater(result.page_count, 0)
        self.assertGreater(result.extracted_text_length, 0)
        self.assertGreater(len(transactions), 0)
        self.assertEqual(
            {"bluAccount", "Belanja Bulanan", "Makan Bulanan", "Operasional Pacaran"},
            {transaction["review_group"] for transaction in transactions},
        )
        self.assertEqual(159750.0, superindo["amount"])
        self.assertEqual("expense", superindo["direction"])
        self.assertEqual(52000.0, ayam_gepuk["amount"])
        self.assertEqual("expense", ayam_gepuk["direction"])
        self.assertEqual(250000.0, seabank["amount"])
        self.assertEqual("expense", seabank["direction"])
        self.assertEqual(250000.0, dana_masuk["amount"])
        self.assertEqual("income", dana_masuk["direction"])

    def test_import_service_calls_blu_parser_and_returns_preview(self):
        fake_upload = NamedBytesIO(self.fixture_bytes, "blu-estatement-june.pdf")
        fake_job = {
            "id": "job-123",
            "provider": "blu",
            "status": "uploaded",
        }

        with patch("app.imports.services.import_service.create_import_job", return_value=fake_job), \
             patch("app.imports.services.import_service.save_temp_import_file", return_value={
                 "path": str(FIXTURE_PATH),
                 "expires_at": "2026-06-17T10:00:00Z",
             }), \
             patch("app.imports.services.import_service.set_import_job_temp_file"), \
             patch("app.imports.services.import_service.update_import_job_provider"), \
             patch("app.imports.services.import_service.update_import_job_status"), \
             patch("app.imports.services.import_service.get_existing_transaction_fingerprints", return_value=set()), \
             patch("app.imports.services.import_service.create_import_draft_transactions"), \
             patch("app.imports.services.import_service.update_import_job_summary"):
            result = ImportService().receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=fake_upload,
            )

        self.assertEqual("blu", result.provider)
        self.assertEqual("review", result.status)
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
                "merchant_display": "Fore Coffee",
            },
            self.merchant_normalizer.normalize("  Fore   Coffee 61715 "),
        )
        self.assertEqual(
            {
                "merchant_original": "SUPERINDO BCY QR",
                "merchant_normalized": "SUPERINDO",
                "merchant_display": "SUPERINDO",
            },
            self.merchant_normalizer.normalize("SUPERINDO BCY QR"),
        )
        self.assertEqual(
            {
                "merchant_original": "jajanan ahmadi 000885",
                "merchant_normalized": "jajanan ahmadi",
                "merchant_display": "jajanan ahmadi",
            },
            self.merchant_normalizer.normalize("jajanan ahmadi 000885"),
        )

    def test_merchant_display_removes_blu_reference_codes(self):
        examples = {
            "SUPERINDO BCY QR 000885002709750 | 02941272241224928998": "SUPERINDO",
            "GUARDIAN BASURA MALL 000123456789 | 998877665544332211": "GUARDIAN BASURA MALL",
            "TDN TEBET SOEPOMO M123456 | abcdef1234567890": "TDN TEBET SOEPOMO",
            "Ayam Gepuk Pak Gembus, Ke M143872 | J2wouupDBSb6mc513120": "Ayam Gepuk Pak Gembus",
            "WARUNG GULE KLATEN TEBET 42526596 | 282525706316erg67774": "Warung Gule Klaten Tebet",
        }

        for merchant_name, expected_display in examples.items():
            with self.subTest(merchant_name=merchant_name):
                self.assertEqual(
                    expected_display,
                    self.merchant_normalizer.normalize(merchant_name)["merchant_display"],
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
             patch("app.imports.services.import_service.save_temp_import_file", return_value={
                 "path": str(FIXTURE_PATH),
                 "expires_at": "2026-06-17T10:00:00Z",
             }), \
             patch("app.imports.services.import_service.set_import_job_temp_file"), \
             patch("app.imports.services.import_service.update_import_job_provider"), \
             patch("app.imports.services.import_service.update_import_job_status"), \
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

        def fake_parse_extracted(_extraction, *, provider):
            self.assertEqual("blu", provider)
            return parse_queue.pop(0)

        def fake_get_existing(_connection, **_kwargs):
            return set(stored_fingerprints)

        def fake_create_drafts(_connection, *, draft_transactions):
            stored_drafts.append(draft_transactions)

        with patch.object(ImportService, "parse_extracted", side_effect=fake_parse_extracted), \
             patch("app.imports.services.import_service.create_import_job", side_effect=fake_create_import_job), \
             patch("app.imports.services.import_service.save_temp_import_file", return_value={
                 "path": str(FIXTURE_PATH),
                 "expires_at": "2026-06-17T10:00:00Z",
             }), \
             patch("app.imports.services.import_service.set_import_job_temp_file"), \
             patch("app.imports.services.import_service.update_import_job_provider"), \
             patch("app.imports.services.import_service.update_import_job_status"), \
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

    def test_import_service_fails_blu_pdf_when_text_layer_is_empty(self):
        fake_upload = NamedBytesIO(b"%PDF-empty", "blu-empty.pdf")
        fake_job = {
            "id": "job-empty",
            "provider": "blu",
            "status": "uploaded",
        }

        with patch("app.imports.services.import_service.create_import_job", return_value=fake_job), \
             patch("app.imports.services.import_service.save_temp_import_file", return_value={
                 "path": str(FIXTURE_PATH),
                 "expires_at": "2026-06-17T10:00:00Z",
             }), \
             patch("app.imports.services.import_service.set_import_job_temp_file"), \
             patch("app.imports.services.import_service.update_import_job_provider"), \
             patch("app.imports.services.import_service.update_import_job_summary"), \
             patch("app.imports.services.import_service.update_import_job_status"), \
             patch.object(BluPdfParser, "extract_pdf_metadata", return_value={
                 "lines": [],
                 "page_count": 1,
                 "extracted_text": "",
                 "extracted_text_length": 0,
                 "extracted_text_hash": "",
             }):
            result = ImportService().receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=fake_upload,
            )

        self.assertEqual("failed", result.status)
        self.assertEqual("PDF tidak memiliki text layer atau gagal dibaca.", result.error)
        self.assertEqual(0, result.transactions_found)

    def test_import_service_fails_blu_pdf_when_text_exists_but_parser_returns_zero(self):
        fake_upload = NamedBytesIO(b"%PDF-no-transactions", "statement.pdf")
        fake_job = {
            "id": "job-zero",
            "provider": "unknown",
            "status": "uploaded",
        }

        with patch("app.imports.services.import_service.create_import_job", return_value=fake_job), \
             patch("app.imports.services.import_service.save_temp_import_file", return_value={
                 "path": str(FIXTURE_PATH),
                 "expires_at": "2026-06-17T10:00:00Z",
             }), \
             patch("app.imports.services.import_service.set_import_job_temp_file"), \
             patch("app.imports.services.import_service.update_import_job_provider"), \
             patch("app.imports.services.import_service.update_import_job_summary"), \
             patch("app.imports.services.import_service.update_import_job_status"), \
             patch.object(BluPdfParser, "extract_pdf_metadata", return_value={
                 "lines": ["bluAccount | bluSpending"],
                 "page_count": 1,
                 "extracted_text": "bluAccount | bluSpending",
                 "extracted_text_length": 24,
                 "extracted_text_hash": "hash",
             }), \
             patch.object(ImportService, "parse_extracted", return_value=ParsedImportResult(
                 provider="blu",
                 transactions=[],
                 page_count=1,
                 extracted_text_length=24,
             )):
            result = ImportService().receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=fake_upload,
            )

        self.assertEqual("failed", result.status)
        self.assertEqual("content", result.detection_source)
        self.assertEqual("PDF Blu terbaca, tapi transaksi tidak berhasil diparse.", result.error)
        self.assertEqual(0, result.transactions_found)

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

    def test_category_options_payload_uses_workspace_transaction_categories(self):
        connection = object()

        with patch(
            "app.imports.services.import_service.list_workspace_transaction_categories",
            return_value=["Groceries", "Makanan", "Parkir", "Pacaran"],
        ) as list_categories_mock:
            payload = ImportService().get_category_options_payload(
                connection,
                workspace_id="workspace-1",
            )

        self.assertEqual(
            {"categories": ["Groceries", "Makanan", "Parkir", "Pacaran"]},
            payload,
        )
        list_categories_mock.assert_called_once_with(
            connection,
            workspace_id="workspace-1",
        )

    def test_approve_review_transactions_creates_final_transactions_and_registers_fingerprint(self):
        service = ImportService()
        selected_drafts = [
            {
                "id": "draft-1",
                "transaction_fingerprint": "fp-1",
                "datetime": "01/06/2026 08:00",
                "merchant_original": "Ayam Gepuk Pak Gembus, Ke M143872 | J2wouupDBSb6mc513120",
                "merchant_normalized": "Ayam Gepuk Pak Gembus, Ke M143872 | J2wouupDBSb6mc513120",
                "amount": 28000,
                "direction": "expense",
                "transaction_type": "DB",
                "review_group": "Makan Bulanan",
                "raw_text": "raw-1",
                "category": "",
                "notes": "",
            },
        ]
        created_transactions = [
            {
                "id": "txn-1",
                "import_transaction_fingerprint": "fp-1",
                "sync_status": "pending",
            },
        ]

        with patch("app.imports.services.import_service.get_import_review_summary", return_value={"id": "job-1", "provider": "blu"}), \
             patch("app.imports.services.import_service.list_import_draft_transactions_by_ids", return_value=selected_drafts), \
             patch("app.imports.services.import_service.get_google_sheet_source", return_value={
                 "id": "sheet-source-1",
                 "sheet_id": "sheet-123",
                 "sheet_name": "Start 1 Juni",
             }), \
             patch("app.imports.services.import_service.get_active_google_oauth_connection", return_value={
                 "id": "oauth-1",
                 "access_token_encrypted": "encrypted-token",
             }), \
             patch("app.imports.services.import_service.decrypt_text", return_value="access-token"), \
             patch("app.imports.services.import_service.read_sheet_values", return_value=[[
                 "Nama",
                 "Waktu Transaksi",
                 "Nama Transaksi",
                 "Kategori",
                 "Harga",
                 "Source Dana",
                 "Keterangan",
             ]]), \
             patch("app.imports.services.import_service.create_import_transactions", return_value=created_transactions) as create_transactions_mock, \
             patch("app.imports.services.import_service.register_transaction_fingerprints") as register_fingerprints_mock, \
             patch.object(SpreadsheetSyncService, "sync_import_transactions", return_value={
                 "status": "success",
                 "sync_success": 1,
                 "sync_failed": 0,
                 "source_id": "sheet-source-1",
                 "error": None,
             }) as sync_mock, \
             patch("app.imports.services.import_service.update_import_transaction_sync_status") as update_sync_mock, \
             patch("app.imports.services.import_service.delete_import_draft_transactions") as delete_drafts_mock, \
             patch.object(ImportCleanupService, "delete_temp_pdf_for_job") as cleanup_pdf_mock, \
             patch("app.imports.services.import_service.count_new_import_draft_transactions", return_value=0), \
             patch("app.imports.services.import_service.update_import_job_status") as update_job_status_mock, \
             patch("app.imports.services.import_service.refresh_import_job_aggregates"):
            approve_result = service.approve_review_transactions(
                connection=object(),
                workspace={"id": "workspace-1", "google_sheet_id": "sheet-123"},
                current_user={"sub": "user-1", "name": "Reza", "email": "reza@example.com"},
                workspace_id="workspace-1",
                import_job_id="job-1",
                draft_ids=["draft-1"],
                sheet_source_id="sheet-source-1",
                sheet_name="Start 1 Juni",
                item_updates=[{
                    "draft_id": "draft-1",
                    "category": "Makan",
                    "notes": "Approved manually",
                }],
            )

        created_row = create_transactions_mock.call_args.kwargs["rows"][0]
        self.assertEqual("sheet-source-1", created_row["sheet_source_id"])
        self.assertEqual("Ayam Gepuk Pak Gembus", created_row["title"])
        self.assertEqual(
            "Ayam Gepuk Pak Gembus, Ke M143872 | J2wouupDBSb6mc513120",
            created_row["raw_payload"]["merchant_original"],
        )
        self.assertEqual(
            "Ayam Gepuk Pak Gembus",
            created_row["raw_payload"]["merchant_display"],
        )
        self.assertEqual("Makan", created_row["raw_category"])
        self.assertEqual("Approved manually", created_row["note"])
        self.assertEqual("Blu", created_row["source_fund"])
        self.assertEqual("Start 1 Juni", sync_mock.call_args.kwargs["target_sheet_name"])
        self.assertEqual(
            "sheet-source-1",
            sync_mock.call_args.kwargs["target_sheet_source"]["id"],
        )
        register_fingerprints_mock.assert_called_once_with(
            unittest.mock.ANY,
            rows=[{
                "transaction_fingerprint": "fp-1",
                "provider": "blu",
            }],
        )
        update_sync_mock.assert_called_once_with(
            unittest.mock.ANY,
            transaction_fingerprints=["fp-1"],
            sync_status="success",
        )
        delete_drafts_mock.assert_called_once_with(
            unittest.mock.ANY,
            import_job_id="job-1",
            draft_ids=["draft-1"],
        )
        cleanup_pdf_mock.assert_called_once_with(
            unittest.mock.ANY,
            workspace_id="workspace-1",
            job_id="job-1",
        )
        update_job_status_mock.assert_called_once()
        self.assertEqual(1, approve_result["approved_count"])
        self.assertEqual(["draft-1"], approve_result["draft_ids"])
        self.assertEqual(1, approve_result["sync_success"])
        self.assertEqual(0, approve_result["sync_failed"])

    def test_approve_review_transactions_missing_target_stops_before_persistence(self):
        service = ImportService()
        selected_drafts = [
            {
                "id": "draft-1",
                "transaction_fingerprint": "fp-1",
                "datetime": "01/06/2026 08:00",
                "merchant_original": "Fore Coffee 61715",
                "merchant_normalized": "Fore Coffee",
                "amount": 28000,
                "direction": "expense",
                "transaction_type": "DB",
                "review_group": "Makan Bulanan",
                "raw_text": "raw-1",
                "category": "Makan",
                "notes": "",
            },
        ]

        with patch("app.imports.services.import_service.get_import_review_summary", return_value={"id": "job-1", "provider": "blu"}), \
             patch("app.imports.services.import_service.list_import_draft_transactions_by_ids", return_value=selected_drafts), \
             patch("app.imports.services.import_service.create_import_transactions") as create_transactions_mock, \
             patch("app.imports.services.import_service.register_transaction_fingerprints") as register_fingerprints_mock, \
             patch("app.imports.services.import_service.delete_import_draft_transactions") as delete_drafts_mock, \
             patch.object(SpreadsheetSyncService, "sync_import_transactions") as sync_mock:
            with self.assertRaises(MissingTargetSheetError) as raised:
                service.approve_review_transactions(
                    connection=object(),
                    workspace={"id": "workspace-1", "google_sheet_id": ""},
                    current_user={"sub": "user-1", "name": "Reza", "email": "reza@example.com"},
                    workspace_id="workspace-1",
                    import_job_id="job-1",
                    draft_ids=["draft-1"],
                    item_updates=[],
                )

        self.assertEqual(
            {
                "status": "failed",
                "error_code": "missing_target_sheet",
                "message": "Pilih target spreadsheet dan tab tujuan sebelum approve.",
            },
            raised.exception.to_response(),
        )
        create_transactions_mock.assert_not_called()
        register_fingerprints_mock.assert_not_called()
        delete_drafts_mock.assert_not_called()
        sync_mock.assert_not_called()

    def test_approve_review_transactions_invalid_target_header_stops_before_persistence(self):
        service = ImportService()
        selected_drafts = [
            {
                "id": "draft-1",
                "transaction_fingerprint": "fp-1",
                "datetime": "01/06/2026 08:00",
                "merchant_original": "Fore Coffee 61715",
                "merchant_normalized": "Fore Coffee",
                "amount": 28000,
                "direction": "expense",
                "transaction_type": "DB",
                "review_group": "Makan Bulanan",
                "raw_text": "raw-1",
                "category": "Makan",
                "notes": "",
            },
        ]

        with patch("app.imports.services.import_service.get_import_review_summary", return_value={"id": "job-1", "provider": "blu"}), \
             patch("app.imports.services.import_service.list_import_draft_transactions_by_ids", return_value=selected_drafts), \
             patch("app.imports.services.import_service.get_google_sheet_source", return_value={
                 "id": "sheet-source-1",
                 "sheet_id": "sheet-123",
                 "sheet_name": "Start 1 Juni",
             }), \
             patch("app.imports.services.import_service.get_active_google_oauth_connection", return_value={
                 "id": "oauth-1",
                 "access_token_encrypted": "encrypted-token",
             }), \
             patch("app.imports.services.import_service.decrypt_text", return_value="access-token"), \
             patch("app.imports.services.import_service.read_sheet_values", return_value=[[
                 "Tanggal",
                 "Deskripsi",
                 "Nominal",
             ]]), \
             patch("app.imports.services.import_service.create_import_transactions") as create_transactions_mock, \
             patch("app.imports.services.import_service.register_transaction_fingerprints") as register_fingerprints_mock, \
             patch("app.imports.services.import_service.delete_import_draft_transactions") as delete_drafts_mock:
            with self.assertRaises(InvalidTargetSheetHeaderError) as raised:
                service.approve_review_transactions(
                    connection=object(),
                    workspace={"id": "workspace-1", "google_sheet_id": "sheet-123"},
                    current_user={"sub": "user-1", "name": "Reza", "email": "reza@example.com"},
                    workspace_id="workspace-1",
                    import_job_id="job-1",
                    draft_ids=["draft-1"],
                    sheet_source_id="sheet-source-1",
                    sheet_name="Start 1 Juni",
                    item_updates=[],
                )

        self.assertEqual(
            {
                "status": "failed",
                "error_code": "invalid_target_sheet_header",
                "message": "Tab tujuan belum memiliki format kolom transaksi yang sesuai.",
            },
            raised.exception.to_response(),
        )
        create_transactions_mock.assert_not_called()
        register_fingerprints_mock.assert_not_called()
        delete_drafts_mock.assert_not_called()

    def test_approve_review_transactions_insert_failure_keeps_draft_and_skips_sync(self):
        service = ImportService()
        selected_drafts = [
            {
                "id": "draft-1",
                "transaction_fingerprint": "fp-1",
                "datetime": "01/06/2026 08:00",
                "merchant_original": "Fore Coffee 61715",
                "merchant_normalized": "Fore Coffee",
                "amount": 28000,
                "direction": "expense",
                "transaction_type": "DB",
                "review_group": "Makan Bulanan",
                "raw_text": "raw-1",
                "category": "Makan",
                "notes": "",
            },
        ]

        with patch("app.imports.services.import_service.get_import_review_summary", return_value={"id": "job-1", "provider": "blu"}), \
             patch("app.imports.services.import_service.list_import_draft_transactions_by_ids", return_value=selected_drafts), \
             patch("app.imports.services.import_service.get_google_sheet_source", return_value={
                 "id": "sheet-source-1",
                 "sheet_id": "sheet-123",
                 "sheet_name": "Start 1 Juni",
             }), \
             patch("app.imports.services.import_service.get_active_google_oauth_connection", return_value={
                 "id": "oauth-1",
                 "access_token_encrypted": "encrypted-token",
             }), \
             patch("app.imports.services.import_service.decrypt_text", return_value="access-token"), \
             patch("app.imports.services.import_service.read_sheet_values", return_value=[[
                 "Nama",
                 "Waktu Transaksi",
                 "Nama Transaksi",
                 "Kategori",
                 "Harga",
                 "Source Dana",
                 "Keterangan",
             ]]), \
             patch("app.imports.services.import_service.create_import_transactions", side_effect=RuntimeError("insert failed")), \
             patch("app.imports.services.import_service.register_transaction_fingerprints") as register_fingerprints_mock, \
             patch("app.imports.services.import_service.delete_import_draft_transactions") as delete_drafts_mock, \
             patch.object(SpreadsheetSyncService, "sync_import_transactions") as sync_mock:
            with self.assertRaises(RuntimeError):
                service.approve_review_transactions(
                    connection=object(),
                    workspace={"id": "workspace-1", "google_sheet_id": "sheet-123"},
                    current_user={"sub": "user-1", "name": "Reza", "email": "reza@example.com"},
                    workspace_id="workspace-1",
                    import_job_id="job-1",
                    draft_ids=["draft-1"],
                    sheet_source_id="sheet-source-1",
                    sheet_name="Start 1 Juni",
                    item_updates=[],
                )

        register_fingerprints_mock.assert_not_called()
        delete_drafts_mock.assert_not_called()
        sync_mock.assert_not_called()

    def test_approve_review_transactions_registry_failure_keeps_draft_and_skips_sync(self):
        service = ImportService()
        selected_drafts = [
            {
                "id": "draft-1",
                "transaction_fingerprint": "fp-1",
                "datetime": "01/06/2026 08:00",
                "merchant_original": "Fore Coffee 61715",
                "merchant_normalized": "Fore Coffee",
                "amount": 28000,
                "direction": "expense",
                "transaction_type": "DB",
                "review_group": "Makan Bulanan",
                "raw_text": "raw-1",
                "category": "Makan",
                "notes": "",
            },
        ]

        with patch("app.imports.services.import_service.get_import_review_summary", return_value={"id": "job-1", "provider": "blu"}), \
             patch("app.imports.services.import_service.list_import_draft_transactions_by_ids", return_value=selected_drafts), \
             patch("app.imports.services.import_service.get_google_sheet_source", return_value={
                 "id": "sheet-source-1",
                 "sheet_id": "sheet-123",
                 "sheet_name": "Start 1 Juni",
             }), \
             patch("app.imports.services.import_service.get_active_google_oauth_connection", return_value={
                 "id": "oauth-1",
                 "access_token_encrypted": "encrypted-token",
             }), \
             patch("app.imports.services.import_service.decrypt_text", return_value="access-token"), \
             patch("app.imports.services.import_service.read_sheet_values", return_value=[[
                 "Nama",
                 "Waktu Transaksi",
                 "Nama Transaksi",
                 "Kategori",
                 "Harga",
                 "Source Dana",
                 "Keterangan",
             ]]), \
             patch("app.imports.services.import_service.create_import_transactions", return_value=[{"id": "txn-1"}]), \
             patch("app.imports.services.import_service.register_transaction_fingerprints", side_effect=RuntimeError("registry failed")), \
             patch("app.imports.services.import_service.delete_import_draft_transactions") as delete_drafts_mock, \
             patch.object(SpreadsheetSyncService, "sync_import_transactions") as sync_mock:
            with self.assertRaises(RuntimeError):
                service.approve_review_transactions(
                    connection=object(),
                    workspace={"id": "workspace-1", "google_sheet_id": "sheet-123"},
                    current_user={"sub": "user-1", "name": "Reza", "email": "reza@example.com"},
                    workspace_id="workspace-1",
                    import_job_id="job-1",
                    draft_ids=["draft-1"],
                    sheet_source_id="sheet-source-1",
                    sheet_name="Start 1 Juni",
                    item_updates=[],
                )

        delete_drafts_mock.assert_not_called()
        sync_mock.assert_not_called()

    def test_approve_review_transactions_keeps_final_transactions_when_sync_fails(self):
        service = ImportService()
        selected_drafts = [
            {
                "id": "draft-1",
                "transaction_fingerprint": "fp-1",
                "datetime": "01/06/2026 08:00",
                "merchant_original": "Fore Coffee 61715",
                "merchant_normalized": "Fore Coffee",
                "amount": 28000,
                "direction": "expense",
                "transaction_type": "DB",
                "review_group": "Makan Bulanan",
                "raw_text": "raw-1",
                "category": "Makan",
                "notes": "",
            },
        ]

        with patch("app.imports.services.import_service.get_import_review_summary", return_value={"id": "job-1", "provider": "blu"}), \
             patch("app.imports.services.import_service.list_import_draft_transactions_by_ids", return_value=selected_drafts), \
             patch("app.imports.services.import_service.get_google_sheet_source", return_value={
                 "id": "sheet-source-1",
                 "sheet_id": "sheet-123",
                 "sheet_name": "Start 1 Juni",
             }), \
             patch("app.imports.services.import_service.get_active_google_oauth_connection", return_value={
                 "id": "oauth-1",
                 "access_token_encrypted": "encrypted-token",
             }), \
             patch("app.imports.services.import_service.decrypt_text", return_value="access-token"), \
             patch("app.imports.services.import_service.read_sheet_values", return_value=[[
                 "Nama",
                 "Waktu Transaksi",
                 "Nama Transaksi",
                 "Kategori",
                 "Harga",
                 "Source Dana",
                 "Keterangan",
             ]]), \
             patch("app.imports.services.import_service.create_import_transactions", return_value=[{"id": "txn-1"}]), \
             patch("app.imports.services.import_service.register_transaction_fingerprints"), \
             patch.object(SpreadsheetSyncService, "sync_import_transactions", return_value={
                 "status": "failed",
                 "sync_success": 0,
                 "sync_failed": 1,
                 "source_id": "sheet-source-1",
                 "error": "append failed",
             }), \
             patch("app.imports.services.import_service.update_import_transaction_sync_status") as update_sync_mock, \
             patch("app.imports.services.import_service.delete_import_draft_transactions") as delete_drafts_mock, \
             patch.object(ImportCleanupService, "delete_temp_pdf_for_job"), \
             patch("app.imports.services.import_service.count_new_import_draft_transactions", return_value=0), \
             patch("app.imports.services.import_service.update_import_job_status"), \
             patch("app.imports.services.import_service.refresh_import_job_aggregates"):
            approve_result = service.approve_review_transactions(
                connection=object(),
                workspace={"id": "workspace-1", "google_sheet_id": "sheet-123"},
                current_user={"sub": "user-1", "name": "Reza", "email": "reza@example.com"},
                workspace_id="workspace-1",
                import_job_id="job-1",
                draft_ids=["draft-1"],
                sheet_source_id="sheet-source-1",
                sheet_name="Start 1 Juni",
                item_updates=[],
            )

        update_sync_mock.assert_called_once_with(
            unittest.mock.ANY,
            transaction_fingerprints=["fp-1"],
            sync_status="failed",
            sync_error_message="append failed",
        )
        delete_drafts_mock.assert_called_once()
        self.assertEqual("failed", approve_result["sync_status"])
        self.assertEqual(0, approve_result["sync_success"])
        self.assertEqual(1, approve_result["sync_failed"])

    def test_spreadsheet_sync_requires_reconnect_for_readonly_scope(self):
        sync_service = SpreadsheetSyncService()

        with patch("app.imports.services.spreadsheet_sync_service.get_active_google_oauth_connection", return_value={
            "id": "oauth-1",
            "access_token_encrypted": "encrypted-token",
            "scopes": ["https://www.googleapis.com/auth/spreadsheets.readonly"],
        }), \
             patch("app.imports.services.spreadsheet_sync_service.ensure_import_google_sheet_source") as ensure_source_mock, \
             patch("app.imports.services.spreadsheet_sync_service.append_sheet_values") as append_values_mock:
            result = sync_service.sync_import_transactions(
                connection=object(),
                workspace={"id": "workspace-1", "google_sheet_id": "sheet-123"},
                current_user={"sub": "user-1", "name": "Reza", "email": "reza@example.com"},
                approved_transactions=[{
                    "datetime": "01/06/2026 08:00",
                    "merchant_normalized": "Fore Coffee",
                    "amount": 28000,
                    "category": "Makan",
                    "notes": "",
                }],
            )

        ensure_source_mock.assert_not_called()
        append_values_mock.assert_not_called()
        self.assertEqual("needs_reconnect", result["status"])
        self.assertEqual(1, result["sync_failed"])

    def test_spreadsheet_row_uses_merchant_display(self):
        row = SpreadsheetSyncService()._build_sheet_row(
            {
                "datetime": "01/06/2026 08:00",
                "merchant_display": "Ayam Gepuk Pak Gembus",
                "merchant_normalized": "Ayam Gepuk Pak Gembus, Ke M143872 | J2wouupDBSb6mc513120",
                "amount": 52000,
                "category": "Makan",
                "notes": "",
            },
            current_user={"name": "Reza"},
        )

        self.assertEqual("Ayam Gepuk Pak Gembus", row[2])

    def test_reject_review_transactions_removes_selected_drafts(self):
        service = ImportService()

        with patch("app.imports.services.import_service.get_import_review_summary", return_value={"id": "job-1"}), \
             patch("app.imports.services.import_service.reject_import_draft_transactions", return_value=[{"id": "draft-2"}]), \
             patch("app.imports.services.import_service.increment_import_job_rejected_count"), \
             patch("app.imports.services.import_service.count_new_import_draft_transactions", return_value=0), \
             patch("app.imports.services.import_service.update_import_job_status"):
            reject_result = service.reject_review_transactions(
                connection=object(),
                workspace_id="workspace-1",
                import_job_id="job-1",
                draft_ids=["draft-2"],
            )

        self.assertEqual(1, reject_result["rejected_count"])
        self.assertEqual(["draft-2"], reject_result["draft_ids"])

    def test_retry_sync_only_retries_failed_or_needs_reconnect_transactions(self):
        service = ImportService()
        retryable_transactions = [
            {
                "transaction_fingerprint": "fp-1",
                "datetime": "01/06/2026 08:00",
                "merchant_normalized": "Fore Coffee",
                "category": "Makan",
                "amount": 28000,
                "notes": "",
            },
            {
                "transaction_fingerprint": "fp-2",
                "datetime": "02/06/2026 08:00",
                "merchant_normalized": "Superindo",
                "category": "Belanja",
                "amount": 150000,
                "notes": "",
            },
        ]

        with patch("app.imports.services.import_service.get_import_history_detail", return_value={"id": "job-1"}), \
             patch("app.imports.services.import_service.list_retryable_import_transactions", return_value=retryable_transactions), \
             patch.object(SpreadsheetSyncService, "sync_import_transactions", return_value={
                 "status": "success",
                 "sync_success": 2,
                 "sync_failed": 0,
                 "source_id": "sheet-source-1",
                 "error": None,
             }), \
             patch("app.imports.services.import_service.update_import_transaction_sync_status") as update_sync_mock, \
             patch("app.imports.services.import_service.refresh_import_job_aggregates"):
            result = service.retry_sync_transactions(
                connection=object(),
                workspace={"id": "workspace-1", "google_sheet_id": "sheet-123"},
                current_user={"sub": "user-1", "name": "Reza", "email": "reza@example.com"},
                workspace_id="workspace-1",
                import_job_id="job-1",
            )

        update_sync_mock.assert_called_once_with(
            unittest.mock.ANY,
            transaction_fingerprints=["fp-1", "fp-2"],
            sync_status="success",
        )
        self.assertEqual(2, result["retried_count"])
        self.assertEqual("success", result["sync_status"])

    def test_cleanup_service_deletes_expired_pdf_and_drafts_but_preserves_history(self):
        service = ImportCleanupService()
        expired_jobs = [
            {
                "id": "job-1",
                "workspace_id": "workspace-1",
                "status": "review",
                "temp_file_path": "temp/job-1.pdf",
                "temp_file_deleted_at": None,
                "expires_at": "2026-06-17T10:00:00Z",
            },
        ]

        with patch("app.imports.services.cleanup_service.list_expired_import_jobs", return_value=expired_jobs), \
             patch("app.imports.services.cleanup_service.mark_import_job_expired") as mark_expired_mock, \
             patch.object(ImportCleanupService, "delete_temp_pdf_for_job", return_value=True) as delete_pdf_mock, \
             patch("app.imports.services.cleanup_service.delete_import_draft_transactions_for_job") as delete_drafts_mock, \
             patch("app.imports.services.cleanup_service.mark_import_job_cleanup_completed") as cleanup_completed_mock:
            result = service.cleanup_expired_jobs(connection=object())

        mark_expired_mock.assert_called_once_with(unittest.mock.ANY, job_id="job-1")
        delete_pdf_mock.assert_called_once_with(
            unittest.mock.ANY,
            workspace_id="workspace-1",
            job_id="job-1",
        )
        delete_drafts_mock.assert_called_once_with(unittest.mock.ANY, import_job_id="job-1")
        cleanup_completed_mock.assert_called_once_with(unittest.mock.ANY, job_id="job-1")
        self.assertEqual({"cleaned_jobs": 1, "job_ids": ["job-1"]}, result)

    def test_history_payload_remains_available_after_cleanup(self):
        service = ImportService()
        history_rows = [
            {
                "id": "job-1",
                "filename": "blu_statement_juni.pdf",
                "provider": "blu",
                "status": "cleanup_completed",
                "created_at": "2026-06-16T10:00:00Z",
                "transactions_found": 300,
                "new_transactions": 150,
                "existing_transactions": 150,
                "approved_transactions": 120,
                "rejected_transactions": 30,
                "sync_success": 110,
                "sync_failed": 10,
                "retryable_sync_count": 10,
                "needs_reconnect": False,
                "temp_file_deleted_at": "2026-06-16T11:00:00Z",
            },
        ]

        with patch("app.imports.services.import_service.list_import_history", return_value=history_rows):
            payload = service.get_history_payload(
                connection=object(),
                workspace_id="workspace-1",
            )

        self.assertEqual(1, len(payload["jobs"]))
        self.assertEqual("cleanup_completed", payload["jobs"][0]["status"])
        self.assertEqual("already_deleted", payload["jobs"][0]["pdf_status"])


if __name__ == "__main__":
    unittest.main()
