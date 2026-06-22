import io
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

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
from app.imports.repositories.final_transaction_repository import (
    create_import_transactions,
    update_import_transaction_sync_status,
)
from app.imports.repositories.fingerprint_registry_repository import (
    get_registered_transaction_fingerprint_statuses,
    register_rejected_transaction_fingerprints,
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
from app.imports.services.spreadsheet_value_resolver import SpreadsheetValueResolver
from app.services.google_sheets_client import (
    GoogleSheetsClientError,
    copy_sheet_row_format_and_validation,
    get_data_validation_values,
)
from app.services.transaction_normalizer import normalize_transaction_row
from app.imports.utils.fingerprint import build_transaction_fingerprint
from app.imports.utils.merchant_normalizer import MerchantNormalizer
from app.imports.utils.provider_detection import detect_import_provider
from app.imports.models.import_models import ParsedImportResult


REAL_JUNE_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "blu_statement_june_real.pdf"
FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "blu_statement_sample.pdf"
if not FIXTURE_PATH.exists():
    FIXTURE_PATH = REAL_JUNE_FIXTURE_PATH


class NamedBytesIO(io.BytesIO):
    def __init__(
        self,
        content: bytes,
        name: str,
        *,
        content_type: str | None = None,
        size: int | None = None,
    ):
        super().__init__(content)
        self.filename = name
        self.file = self
        self.content_type = content_type
        self.size = len(content) if size is None else size


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


class FakeFetchAllCursor(FakeReturningCursor):
    def fetchall(self):
        self.fetchall_calls += 1
        rows = list(self.returned_rows)
        self.returned_rows.clear()
        return rows


class FakeReturningConnection:
    def __init__(self, cursor: FakeReturningCursor):
        self.cursor_instance = cursor
        self.cursor_calls = []

    def cursor(self, **kwargs):
        self.cursor_calls.append(kwargs)
        return self.cursor_instance


class FakeSpreadsheetValueResolver:
    def __init__(self, user_name: str = "Reza", source_dana: str = "Blu"):
        self.user_name = user_name
        self.source_dana = source_dana

    def resolve_user_name_for_append(self, connection, *, workspace_id: str, current_user: dict):
        return self.user_name

    def resolve_source_dana_for_append(self, connection, *, workspace_id: str, provider: str = "Blu"):
        return self.source_dana


class BluPdfParserTestCase(unittest.TestCase):
    def setUp(self):
        self.parser = BluPdfParser()
        self.merchant_normalizer = MerchantNormalizer()
        self.registry_status_patcher = patch(
            "app.imports.services.import_service.get_registered_transaction_fingerprint_statuses",
            return_value={},
        )
        self.registry_status_patcher.start()
        self.addCleanup(self.registry_status_patcher.stop)
        fixture_path = FIXTURE_PATH if FIXTURE_PATH.exists() else REAL_JUNE_FIXTURE_PATH
        self.fixture_bytes = fixture_path.read_bytes()
        self.real_june_fixture_bytes = REAL_JUNE_FIXTURE_PATH.read_bytes()
        self.fixture_transaction_count = len(self.parser.parse(io.BytesIO(self.fixture_bytes)).transactions)

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
                "sheet_source_id": None,
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
        self.assertIn(
            "on conflict (workspace_id, import_transaction_fingerprint)",
            cursor.executed[0][0],
        )
        self.assertIsNone(cursor.executed[0][1]["sheet_source_id"])
        self.assertEqual(
            "fore coffee makan blu",
            cursor.executed[0][1]["search_text_normalized"],
        )
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

        self.assertEqual(
            [],
            register_transaction_fingerprints(
                connection,
                workspace_id="workspace-1",
                rows=[],
            ),
        )
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
            workspace_id="workspace-1",
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
        self.assertIn(
            "returning workspace_id, transaction_fingerprint, provider, status, approved_at, rejected_at, last_seen_at, created_at",
            cursor.executed[0][0],
        )
        self.assertIn(
            "on conflict (workspace_id, transaction_fingerprint)",
            cursor.executed[0][0],
        )
        self.assertEqual("workspace-1", cursor.executed[0][1]["workspace_id"])
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
            workspace_id="workspace-1",
            rows=[{
                "transaction_fingerprint": "fp-1",
                "provider": "blu",
            }],
        )

        self.assertIn("do update set", cursor.executed[0][0])
        self.assertIn("provider = excluded.provider", cursor.executed[0][0])
        self.assertIn("approved_at = excluded.approved_at", cursor.executed[0][0])

    def test_same_fingerprint_can_be_registered_for_different_workspaces(self):
        cursor = FakeReturningCursor([
            {"transaction_fingerprint": "shared-fp", "workspace_id": "workspace-1"},
            {"transaction_fingerprint": "shared-fp", "workspace_id": "workspace-2"},
        ])
        connection = FakeReturningConnection(cursor)
        row = {
            "transaction_fingerprint": "shared-fp",
            "provider": "blu",
        }

        register_transaction_fingerprints(
            connection,
            workspace_id="workspace-1",
            rows=[row],
        )
        register_transaction_fingerprints(
            connection,
            workspace_id="workspace-2",
            rows=[row],
        )

        self.assertEqual(2, len(cursor.executed))
        self.assertIn(
            "on conflict (workspace_id, transaction_fingerprint)",
            cursor.executed[0][0],
        )
        self.assertEqual("workspace-1", cursor.executed[0][1]["workspace_id"])
        self.assertEqual("workspace-2", cursor.executed[1][1]["workspace_id"])

    def test_get_registered_transaction_fingerprint_statuses_returns_mapping(self):
        cursor = FakeFetchAllCursor([
            {
                "transaction_fingerprint": "fp-approved",
                "status": "approved",
            },
            {
                "transaction_fingerprint": "fp-rejected",
                "status": "rejected",
            },
        ])
        connection = FakeReturningConnection(cursor)

        statuses = get_registered_transaction_fingerprint_statuses(
            connection,
            workspace_id="workspace-1",
            transaction_fingerprints=["fp-approved", "fp-rejected"],
        )

        self.assertEqual(
            {
                "fp-approved": "approved",
                "fp-rejected": "rejected",
            },
            statuses,
        )
        self.assertIn("returning transaction_fingerprint, status", cursor.executed[0][0])
        self.assertIn("where workspace_id = %s", cursor.executed[0][0])
        self.assertEqual(
            ("workspace-1", ["fp-approved", "fp-rejected"]),
            cursor.executed[0][1],
        )

    def test_register_rejected_transaction_fingerprint_returns_rejected_status(self):
        cursor = FakeReturningCursor([{
            "transaction_fingerprint": "fp-rejected",
            "provider": "blu",
            "status": "rejected",
            "approved_at": None,
            "rejected_at": "2026-06-18T08:00:00Z",
            "last_seen_at": "2026-06-18T08:00:00Z",
            "created_at": "2026-06-18T08:00:00Z",
        }])
        connection = FakeReturningConnection(cursor)

        rows = register_rejected_transaction_fingerprints(
            connection,
            workspace_id="workspace-1",
            rows=[{
                "transaction_fingerprint": "fp-rejected",
                "provider": "blu",
            }],
        )

        self.assertEqual("rejected", rows[0]["status"])
        self.assertIn("'rejected'", cursor.executed[0][0])
        self.assertIn("rejected_at = excluded.rejected_at", cursor.executed[0][0])
        self.assertIn(
            "on conflict (workspace_id, transaction_fingerprint)",
            cursor.executed[0][0],
        )

    def test_sync_status_update_is_scoped_by_workspace(self):
        cursor = FakeFetchAllCursor([])
        connection = FakeReturningConnection(cursor)

        update_import_transaction_sync_status(
            connection,
            workspace_id="workspace-2",
            transaction_fingerprints=["shared-fingerprint"],
            sync_status="success",
        )

        query, params = cursor.executed[0]
        self.assertIn("where workspace_id = %s", query)
        self.assertIn("import_transaction_fingerprint = any(%s)", query)
        self.assertEqual(
            ("success", None, "workspace-2", ["shared-fingerprint"]),
            params,
        )

    def test_parser_detects_sections_and_review_groups(self):
        transactions = self.parser._parse_lines([
            "bluAccount - 0000 0000 2555",
            "05 Jun 2026",
            "16:58 SEABANK | 1780653530302275",
            "Transfer ke REZA PUTRA PRATAMA - 250.000,00 1.004,38",
            "bluSpending - Makan Bulanan",
            "10 Jun 2026",
            "18:10 Ayam Gepuk Pak Gembus, Ke M143872 |",
            "J2wouupDBSb6mc513120",
            "Pembayaran QRIS - 52.000,00 301.572,19",
            "11 Jun 2026",
            "18:11 Fore Coffee 61715 |",
            "ABC123456789",
            "Pembayaran QRIS - 28.000,00 273.572,19",
            "bluSpending - Operasional Pacaran",
            "12 Jun 2026",
            "20:30 PARKIR QR 001122 |",
            "ABC123",
            "Pembayaran QRIS - 5.000,00 268.572,19",
        ])

        self.assertEqual("bluAccount", transactions[0]["review_group"])
        self.assertEqual("Makan Bulanan", transactions[1]["review_group"])
        self.assertEqual("Makan Bulanan", transactions[2]["review_group"])
        self.assertEqual("Operasional Pacaran", transactions[3]["review_group"])

    def test_parser_extracts_standardized_transaction_fields(self):
        transactions = self.parser._parse_lines([
            "bluAccount - 0000 0000 2555",
            "14 Jun 2026",
            "09:15 Top Up dari Bank Lain",
            "CR 1.500.000,00 1.500.000,00",
            "bluSpending - Makan Bulanan",
            "14 Jun 2026",
            "12:00 Fore Coffee 61715 |",
            "ABC123456789",
            "Pembayaran QRIS - 28.000,00 1.472.000,00",
            "14 Jun 2026",
            "13:00 Family Mart 001",
            "Pembayaran QRIS - 15.000,00 1.457.000,00",
            "bluSpending - Operasional Pacaran",
            "14 Jun 2026",
            "20:00 XXI Mall",
            "Pembayaran QRIS - 50.000,00 1.407.000,00",
        ])

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
             patch("app.imports.services.import_service.get_registered_transaction_fingerprint_statuses", return_value={}), \
             patch("app.imports.services.import_service.create_import_draft_transactions"), \
             patch("app.imports.services.import_service.update_import_job_summary"):
            result = ImportService().receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=fake_upload,
                statement_owner="Reza",
            )

        self.assertEqual("blu", result.provider)
        self.assertEqual("review", result.status)
        self.assertEqual(self.fixture_transaction_count, result.transactions_found)
        self.assertEqual(self.fixture_transaction_count, result.new_transactions)
        self.assertEqual(0, result.existing_transactions)
        self.assertEqual(min(5, self.fixture_transaction_count), len(result.preview))

    def test_import_service_returns_no_new_state_for_previously_approved_pdf(self):
        fake_upload = NamedBytesIO(self.fixture_bytes, "blu-estatement-june.pdf")
        fake_job = {
            "id": "job-124",
            "provider": "blu",
            "status": "uploaded",
        }

        def fake_get_statuses(_connection, *, workspace_id, transaction_fingerprints):
            self.assertEqual("workspace-1", workspace_id)
            return {
                fingerprint: "approved"
                for fingerprint in transaction_fingerprints
            }

        with patch("app.imports.services.import_service.create_import_job", return_value=fake_job), \
             patch("app.imports.services.import_service.save_temp_import_file", return_value={
                 "path": str(FIXTURE_PATH),
                 "expires_at": "2026-06-17T10:00:00Z",
             }), \
             patch("app.imports.services.import_service.set_import_job_temp_file"), \
             patch("app.imports.services.import_service.update_import_job_provider"), \
             patch("app.imports.services.import_service.update_import_job_status"), \
             patch(
                 "app.imports.services.import_service.get_registered_transaction_fingerprint_statuses",
                 side_effect=fake_get_statuses,
             ), \
             patch("app.imports.services.import_service.create_import_draft_transactions") as create_draft_mock, \
             patch("app.imports.services.import_service.update_import_job_summary"):
            result = ImportService().receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=fake_upload,
                statement_owner="Reza",
            )

        self.assertEqual("completed", result.status)
        self.assertTrue(result.no_new_transactions)
        self.assertEqual(self.fixture_transaction_count, result.transactions_found)
        self.assertEqual(0, result.new_transactions)
        self.assertEqual(self.fixture_transaction_count, result.existing_transactions)
        self.assertEqual(0, result.rejected_transactions)
        self.assertEqual([], result.preview)
        self.assertEqual(
            "Semua transaksi dalam PDF ini sudah pernah diproses atau ditolak.",
            result.message,
        )
        create_draft_mock.assert_called_once_with(unittest.mock.ANY, draft_transactions=[])

    def test_import_service_returns_no_new_state_for_previously_rejected_pdf(self):
        fake_upload = NamedBytesIO(self.fixture_bytes, "blu-estatement-june.pdf")
        fake_job = {
            "id": "job-125",
            "provider": "blu",
            "status": "uploaded",
        }
        def fake_get_statuses(_connection, *, workspace_id, transaction_fingerprints):
            self.assertEqual("workspace-1", workspace_id)
            return {
                fingerprint: "rejected"
                for fingerprint in transaction_fingerprints
            }

        with patch("app.imports.services.import_service.create_import_job", return_value=fake_job), \
             patch("app.imports.services.import_service.save_temp_import_file", return_value={
                 "path": str(FIXTURE_PATH),
                 "expires_at": "2026-06-17T10:00:00Z",
             }), \
             patch("app.imports.services.import_service.set_import_job_temp_file"), \
             patch("app.imports.services.import_service.update_import_job_provider"), \
             patch("app.imports.services.import_service.update_import_job_status"), \
             patch(
                 "app.imports.services.import_service.get_registered_transaction_fingerprint_statuses",
                 side_effect=fake_get_statuses,
             ), \
             patch("app.imports.services.import_service.create_import_draft_transactions") as create_draft_mock, \
             patch("app.imports.services.import_service.update_import_job_summary"):
            result = ImportService().receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=fake_upload,
                statement_owner="Reza",
            )

        self.assertEqual("completed", result.status)
        self.assertTrue(result.no_new_transactions)
        self.assertEqual(self.fixture_transaction_count, result.transactions_found)
        self.assertEqual(0, result.new_transactions)
        self.assertEqual(self.fixture_transaction_count, result.existing_transactions)
        self.assertEqual(self.fixture_transaction_count, result.rejected_transactions)
        self.assertEqual([], result.preview)
        self.assertEqual(
            "Semua transaksi dalam PDF ini sudah pernah diproses atau ditolak.",
            result.message,
        )
        create_draft_mock.assert_called_once_with(unittest.mock.ANY, draft_transactions=[])

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

    def test_normalize_transaction_row_keeps_owner_and_canonical_fingerprint(self):
        payload = normalize_transaction_row(
            {
                "Nama": " Reza ",
                "Waktu Transaksi": "18/06/2026 17:50",
                "Nama Transaksi": "SUPERINDO BCY QR 000885002709750",
                "Kategori": "Belanja",
                "Harga": "159.750",
                "Source Dana": "Blu",
                "Keterangan": "Belanja mingguan",
            },
            raw_metadata={
                "_sheet_name": "Start 1 Juni",
                "_row_number": 2,
            },
        )

        self.assertEqual("Reza", payload["user_name"])
        self.assertEqual("google_sheet", payload["source_origin"])
        self.assertEqual("sheet:Start 1 Juni|row:2", payload["source_reference"])
        self.assertTrue(payload["canonical_fingerprint"])
        self.assertTrue(payload["canonical_fingerprint_date"])

    def test_normalize_transaction_row_maps_reza_putra_pratama_to_reza(self):
        payload = normalize_transaction_row(
            {
                "Nama": "  reza putra pratama ",
                "Waktu Transaksi": "18/06/2026 17:50",
                "Nama Transaksi": "SUPERINDO BCY QR 000885002709750",
                "Kategori": "Belanja",
                "Harga": "159.750",
                "Source Dana": "Blu",
                "Keterangan": "Belanja mingguan",
            },
            raw_metadata={
                "_sheet_name": "Start 1 Juni",
                "_row_number": 3,
            },
        )

        self.assertEqual("Reza", payload["user_name"])

    def test_fingerprint_is_deterministic_for_same_transaction(self):
        fingerprint_a = build_transaction_fingerprint(
            owner_name="Reza",
            source_dana="Blu",
            datetime_value="21/05/2026 17:54",
            merchant_normalized="Fore Coffee",
            amount=67200,
            direction="expense",
        )
        fingerprint_b = build_transaction_fingerprint(
            owner_name="Reza",
            source_dana="Blu",
            datetime_value="21/05/2026 17:54",
            merchant_normalized="Fore Coffee",
            amount=67200,
            direction="expense",
        )

        self.assertEqual(fingerprint_a, fingerprint_b)

    def test_fingerprint_changes_when_datetime_amount_or_merchant_changes(self):
        baseline = build_transaction_fingerprint(
            owner_name="Reza",
            source_dana="Blu",
            datetime_value="21/05/2026 17:54",
            merchant_normalized="Fore Coffee",
            amount=67200,
            direction="expense",
        )
        different_datetime = build_transaction_fingerprint(
            owner_name="Reza",
            source_dana="Blu",
            datetime_value="21/05/2026 17:55",
            merchant_normalized="Fore Coffee",
            amount=67200,
            direction="expense",
        )
        different_amount = build_transaction_fingerprint(
            owner_name="Reza",
            source_dana="Blu",
            datetime_value="21/05/2026 17:54",
            merchant_normalized="Fore Coffee",
            amount=67201,
            direction="expense",
        )
        different_merchant = build_transaction_fingerprint(
            owner_name="Reza",
            source_dana="Blu",
            datetime_value="21/05/2026 17:54",
            merchant_normalized="Family Mart",
            amount=67200,
            direction="expense",
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

        def fake_get_statuses(_connection, **_kwargs):
            return {
                fingerprint: "approved"
                for fingerprint in stored_fingerprints
            }

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
             patch("app.imports.services.import_service.get_registered_transaction_fingerprint_statuses", side_effect=fake_get_statuses), \
             patch("app.imports.services.import_service.create_import_draft_transactions", side_effect=fake_create_drafts), \
             patch("app.imports.services.import_service.update_import_job_summary"):
            first_result = service.receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=NamedBytesIO(self.fixture_bytes, "blu-estatement-june.pdf"),
                statement_owner="Reza",
            )
            stored_fingerprints.update(
                draft["transaction_fingerprint"] for draft in stored_drafts[-1]
            )
            second_result = service.receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=NamedBytesIO(self.fixture_bytes, "blu-estatement-june.pdf"),
                statement_owner="Reza",
            )

        self.assertEqual(self.fixture_transaction_count, first_result.new_transactions)
        self.assertEqual(0, first_result.existing_transactions)
        self.assertEqual(self.fixture_transaction_count, second_result.existing_transactions)
        self.assertEqual(0, second_result.new_transactions)
        self.assertEqual([], second_result.preview)
        self.assertEqual([], stored_drafts[-1])

    def test_incremental_engine_supports_overlap_upload_previewing_only_new_rows(self):
        service = ImportService()
        first_half_transactions = ParsedImportResult(
            provider="blu",
            transactions=[
                {
                    "datetime": "2026-06-13 13:26",
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

        def fake_get_statuses(_connection, **_kwargs):
            return {
                fingerprint: "approved"
                for fingerprint in stored_fingerprints
            }

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
             patch("app.imports.services.import_service.get_registered_transaction_fingerprint_statuses", side_effect=fake_get_statuses), \
             patch("app.imports.services.import_service.create_import_draft_transactions", side_effect=fake_create_drafts), \
             patch("app.imports.services.import_service.update_import_job_summary"):
            first_result = service.receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=NamedBytesIO(b"%PDF-first-half", "blu-first-half.pdf"),
                statement_owner="Reza",
            )
            stored_fingerprints.update(
                draft["transaction_fingerprint"] for draft in stored_drafts[-1]
            )
            second_result = service.receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=NamedBytesIO(b"%PDF-full-month", "blu-full-month.pdf"),
                statement_owner="Reza",
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
                statement_owner="Reza",
            )

        self.assertEqual("failed", result.status)
        self.assertEqual("PDF tidak memiliki text layer atau gagal dibaca.", result.error)
        self.assertEqual(0, result.transactions_found)

    def test_import_service_returns_controlled_failure_for_invalid_pdf(self):
        fake_upload = NamedBytesIO(b"not-a-pdf", "blu-invalid.pdf")
        fake_job = {
            "id": "job-invalid",
            "provider": "blu",
            "status": "uploaded",
        }

        with patch("app.imports.services.import_service.create_import_job", return_value=fake_job), \
             patch("app.imports.services.import_service.save_temp_import_file", return_value={
                 "path": str(FIXTURE_PATH),
                 "expires_at": "2026-06-18T10:00:00Z",
             }), \
             patch("app.imports.services.import_service.set_import_job_temp_file"), \
             patch("app.imports.services.import_service.update_import_job_summary"), \
             patch("app.imports.services.import_service.update_import_job_status"), \
             patch.object(
                 BluPdfParser,
                 "extract_pdf_metadata",
                 side_effect=ValueError("broken pdf"),
             ):
            result = ImportService().receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=fake_upload,
                statement_owner="Reza",
            )

        self.assertEqual("failed", result.status)
        self.assertEqual("invalid_pdf_signature", result.error_code)
        self.assertEqual("File PDF tidak valid atau isinya bukan PDF.", result.message)

    def test_import_service_rejects_non_pdf_extension_before_temp_save(self):
        fake_upload = NamedBytesIO(
            b"%PDF-fake",
            "blu-invalid.png",
            content_type="application/pdf",
        )
        fake_job = {
            "id": "job-extension",
            "provider": "unknown",
            "status": "uploaded",
        }

        with patch("app.imports.services.import_service.create_import_job", return_value=fake_job), \
             patch("app.imports.services.import_service.save_temp_import_file") as save_temp_mock, \
             patch("app.imports.services.import_service.update_import_job_summary"), \
             patch("app.imports.services.import_service.update_import_job_status"):
            result = ImportService().receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=fake_upload,
                statement_owner="Reza",
            )

        self.assertEqual("failed", result.status)
        self.assertEqual("invalid_file_extension", result.error_code)
        self.assertEqual("File harus berformat PDF (.pdf).", result.message)
        save_temp_mock.assert_not_called()

    def test_import_service_rejects_non_pdf_content_type_before_temp_save(self):
        fake_upload = NamedBytesIO(
            b"%PDF-fake",
            "blu-invalid.pdf",
            content_type="image/png",
        )
        fake_job = {
            "id": "job-content-type",
            "provider": "blu",
            "status": "uploaded",
        }

        with patch("app.imports.services.import_service.create_import_job", return_value=fake_job), \
             patch("app.imports.services.import_service.save_temp_import_file") as save_temp_mock, \
             patch("app.imports.services.import_service.update_import_job_summary"), \
             patch("app.imports.services.import_service.update_import_job_status"):
            result = ImportService().receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=fake_upload,
                statement_owner="Reza",
            )

        self.assertEqual("failed", result.status)
        self.assertEqual("invalid_content_type", result.error_code)
        self.assertEqual("File yang diupload bukan PDF yang valid.", result.message)
        save_temp_mock.assert_not_called()

    def test_import_service_rejects_invalid_pdf_magic_bytes_before_temp_save(self):
        fake_upload = NamedBytesIO(
            b"not-a-pdf",
            "blu-invalid.pdf",
            content_type="application/pdf",
        )
        fake_job = {
            "id": "job-signature",
            "provider": "blu",
            "status": "uploaded",
        }

        with patch("app.imports.services.import_service.create_import_job", return_value=fake_job), \
             patch("app.imports.services.import_service.save_temp_import_file") as save_temp_mock, \
             patch("app.imports.services.import_service.update_import_job_summary"), \
             patch("app.imports.services.import_service.update_import_job_status"):
            result = ImportService().receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=fake_upload,
                statement_owner="Reza",
            )

        self.assertEqual("failed", result.status)
        self.assertEqual("invalid_pdf_signature", result.error_code)
        self.assertEqual("File PDF tidak valid atau isinya bukan PDF.", result.message)
        save_temp_mock.assert_not_called()

    def test_import_service_rejects_pdf_over_max_size_before_temp_save(self):
        fake_upload = NamedBytesIO(
            b"%PDF-small",
            "blu-large.pdf",
            content_type="application/pdf",
            size=(10 * 1024 * 1024) + 1,
        )
        fake_job = {
            "id": "job-too-large",
            "provider": "blu",
            "status": "uploaded",
        }

        with patch("app.imports.services.import_service.create_import_job", return_value=fake_job), \
             patch("app.imports.services.import_service.save_temp_import_file") as save_temp_mock, \
             patch("app.imports.services.import_service.update_import_job_summary"), \
             patch("app.imports.services.import_service.update_import_job_status"):
            result = ImportService().receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=fake_upload,
                statement_owner="Reza",
            )

        self.assertEqual("failed", result.status)
        self.assertEqual("file_too_large", result.error_code)
        self.assertEqual("Ukuran PDF terlalu besar. Maksimal upload adalah 10 MB.", result.message)
        save_temp_mock.assert_not_called()

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
                statement_owner="Reza",
            )

        self.assertEqual("failed", result.status)
        self.assertEqual("content", result.detection_source)
        self.assertEqual("PDF Blu terbaca, tapi transaksi tidak berhasil diparse.", result.error)
        self.assertEqual(0, result.transactions_found)

    def test_import_service_returns_controlled_failure_for_non_blu_pdf(self):
        fake_upload = NamedBytesIO(b"%PDF-bank", "bank-statement.pdf")
        fake_job = {
            "id": "job-unsupported",
            "provider": "unknown",
            "status": "uploaded",
        }

        with patch("app.imports.services.import_service.create_import_job", return_value=fake_job), \
             patch("app.imports.services.import_service.save_temp_import_file", return_value={
                 "path": str(FIXTURE_PATH),
                 "expires_at": "2026-06-18T10:00:00Z",
             }), \
             patch("app.imports.services.import_service.set_import_job_temp_file"), \
             patch("app.imports.services.import_service.update_import_job_provider"), \
             patch("app.imports.services.import_service.update_import_job_summary"), \
             patch("app.imports.services.import_service.update_import_job_status"), \
             patch.object(BluPdfParser, "extract_pdf_metadata", return_value={
                 "lines": ["Other Bank Statement"],
                 "page_count": 1,
                 "extracted_text": "Other Bank Statement",
                 "extracted_text_length": 20,
                 "extracted_text_hash": "hash",
             }):
            result = ImportService().receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=fake_upload,
                statement_owner="Reza",
            )

        self.assertEqual("failed", result.status)
        self.assertEqual("unsupported_provider", result.error_code)
        self.assertEqual(
            "File belum didukung. Saat ini Import Transaksi hanya mendukung PDF e-Statement Blu.",
            result.message,
        )
        self.assertEqual(0, result.transactions_found)

    def test_rejected_fingerprint_is_skipped_on_future_import(self):
        service = ImportService()
        parsed_result = ParsedImportResult(
            provider="blu",
            transactions=[{
                "transaction_fingerprint": "fp-rejected",
                "merchant_normalized": "SUPERINDO",
            }],
        )

        with patch(
            "app.imports.services.import_service.get_registered_transaction_fingerprint_statuses",
            return_value={"fp-rejected": "rejected"},
        ):
            result = service.mark_existing_transactions(
                connection=object(),
                workspace_id="workspace-1",
                parsed_result=parsed_result,
            )

        self.assertTrue(result.transactions[0]["is_existing"])

    def test_existing_spreadsheet_transaction_marks_import_as_already_recorded(self):
        service = ImportService()
        parsed_result = ParsedImportResult(
            provider="blu",
            transactions=[{
                "transaction_fingerprint": "fp-import",
                "canonical_fingerprint": "canon-fp",
                "canonical_fingerprint_date": "canon-date-fp",
                "merchant_normalized": "SUPERINDO",
            }],
        )

        with patch(
            "app.imports.services.import_service.get_registered_transaction_fingerprint_statuses",
            return_value={},
        ), patch(
            "app.imports.services.import_service.get_existing_transactions_by_canonical_fingerprint",
            return_value={
                "canon-fp": {
                    "id": "txn-existing",
                    "source_origin": "google_sheet",
                },
            },
        ):
            result = service.mark_existing_transactions(
                connection=object(),
                workspace_id="workspace-1",
                parsed_result=parsed_result,
            )

        self.assertTrue(result.transactions[0]["is_existing"])
        self.assertEqual("already_recorded", result.transactions[0]["registry_status"])

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
             patch(
                 "app.imports.services.import_service.get_import_review_filter_counts",
                 return_value={
                     "total_count": 2,
                     "needs_review_count": 2,
                     "review_groups": [
                         {"review_group": "Makan Bulanan", "count": 1},
                         {"review_group": "bluAccount", "count": 1},
                     ],
                 },
             ), \
             patch("app.imports.services.import_service.list_import_draft_transactions_paginated", return_value=draft_transactions):
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
        self.assertEqual(
            {
                "total": 2,
                "limit": 100,
                "offset": 0,
                "page": 1,
                "has_next": False,
                "has_previous": False,
            },
            payload["pagination"],
        )

    def test_review_payload_applies_limit_and_offset(self):
        service = ImportService()

        with patch("app.imports.services.import_service.get_import_review_summary", return_value={
            "id": "job-1",
            "filename": "blu_statement_juni.pdf",
            "provider": "blu",
            "status": "uploaded",
            "transactions_found": 120,
            "new_transactions": 120,
            "existing_transactions": 0,
            "created_at": "2026-06-16T10:00:00Z",
            "statement_owner": "Reza",
        }), \
             patch(
                 "app.imports.services.import_service.get_import_review_filter_counts",
                 return_value={
                     "total_count": 120,
                     "needs_review_count": 120,
                     "review_groups": [],
                 },
             ), \
             patch(
                 "app.imports.services.import_service.list_import_draft_transactions_paginated",
                 return_value=[],
             ) as list_drafts_mock:
            payload = service.get_review_payload(
                connection=object(),
                workspace_id="workspace-1",
                job_id="job-1",
                limit=25,
                offset=50,
            )

        list_drafts_mock.assert_called_once_with(
            unittest.mock.ANY,
            import_job_id="job-1",
            status="new",
            limit=25,
            offset=50,
        )
        self.assertEqual(3, payload["pagination"]["page"])
        self.assertTrue(payload["pagination"]["has_next"])
        self.assertTrue(payload["pagination"]["has_previous"])

    def test_category_options_payload_bootstraps_fresh_workspace(self):
        connection = object()

        with patch(
            "app.imports.services.import_service.list_workspace_transaction_categories",
            return_value=[],
        ) as list_categories_mock:
            payload = ImportService().get_category_options_payload(
                connection,
                workspace_id="workspace-1",
            )

        self.assertEqual(
            [
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
            ],
            payload["categories"],
        )
        list_categories_mock.assert_called_once_with(
            connection,
            workspace_id="workspace-1",
        )

    def test_category_options_payload_merges_historical_categories_case_insensitively(self):
        connection = object()

        with patch(
            "app.imports.services.import_service.list_workspace_transaction_categories",
            return_value=["groceries", "Makanan", "Parkir", "Pacaran", " food "],
        ) as list_categories_mock:
            payload = ImportService().get_category_options_payload(
                connection,
                workspace_id="workspace-1",
            )

        self.assertIn("Groceries", payload["categories"])
        self.assertIn("Food", payload["categories"])
        self.assertIn("Makanan", payload["categories"])
        self.assertIn("Parkir", payload["categories"])
        self.assertIn("Pacaran", payload["categories"])
        self.assertNotIn("groceries", payload["categories"])
        self.assertNotIn("food", payload["categories"])
        self.assertNotIn("Makan Bulanan", payload["categories"])
        self.assertEqual(
            sorted(
                payload["categories"],
                key=lambda category: (category.casefold(), category),
            ),
            payload["categories"],
        )
        list_categories_mock.assert_called_once_with(
            connection,
            workspace_id="workspace-1",
        )

    def test_approve_review_transactions_creates_final_transactions_and_registers_fingerprint(self):
        service = ImportService()
        service.spreadsheet_value_resolver = FakeSpreadsheetValueResolver()
        selected_drafts = [
            {
                "id": "draft-1",
                "transaction_fingerprint": "fp-1",
                "canonical_fingerprint": "canon-fp-1",
                "canonical_fingerprint_date": "canon-date-fp-1",
                "statement_owner": "Reza",
                "source_fund": "Blu",
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

        with patch("app.imports.services.import_service.get_import_review_summary", return_value={"id": "job-1", "provider": "blu", "statement_owner": "Reza"}), \
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
                current_user={
                    "sub": "user-1",
                    "display_name": "Reza Display",
                    "name": "Reza",
                    "email": "reza@example.com",
                },
                workspace_id="workspace-1",
                import_job_id="job-1",
                draft_ids=["draft-1"],
                sheet_source_id="sheet-source-1",
                sheet_name="Start 1 Juni",
                item_updates=[{
                    "draft_id": "draft-1",
                    "merchant_display": "Reimburse makan Divya",
                    "category": "Makan",
                    "notes": "Approved manually",
                }],
            )

        created_row = create_transactions_mock.call_args.kwargs["rows"][0]
        self.assertEqual("sheet-source-1", created_row["sheet_source_id"])
        self.assertEqual("Reza", created_row["user_name"])
        self.assertEqual("Reimburse makan Divya", created_row["title"])
        self.assertEqual("blu_pdf", created_row["source_origin"])
        self.assertEqual("canon-fp-1", created_row["canonical_fingerprint"])
        self.assertEqual(
            "Ayam Gepuk Pak Gembus, Ke M143872 | J2wouupDBSb6mc513120",
            created_row["raw_payload"]["merchant_original"],
        )
        self.assertEqual(
            "Reimburse makan Divya",
            created_row["raw_payload"]["merchant_display"],
        )
        self.assertEqual("fp-1", created_row["import_transaction_fingerprint"])
        self.assertEqual("canon-fp-1", created_row["canonical_fingerprint"])
        self.assertEqual("Makan", created_row["raw_category"])
        self.assertEqual("Approved manually", created_row["note"])
        self.assertEqual("Blu", created_row["source_fund"])
        self.assertEqual(
            "reimburse makan divya makan blu approved manually",
            created_row["search_text_normalized"],
        )
        self.assertEqual("Reza", sync_mock.call_args.kwargs["user_name"])
        self.assertEqual("Blu", sync_mock.call_args.kwargs["source_dana"])
        self.assertEqual("job-1", sync_mock.call_args.kwargs["job_id"])
        self.assertEqual("Start 1 Juni", sync_mock.call_args.kwargs["target_sheet_name"])
        self.assertEqual(
            "sheet-source-1",
            sync_mock.call_args.kwargs["target_sheet_source"]["id"],
        )
        register_fingerprints_mock.assert_called_once_with(
            unittest.mock.ANY,
            workspace_id="workspace-1",
            rows=[{
                "transaction_fingerprint": "fp-1",
                "provider": "blu",
            }],
        )
        update_sync_mock.assert_called_once_with(
            unittest.mock.ANY,
            workspace_id="workspace-1",
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

    def test_approve_review_transactions_without_target_persists_ledger_and_registry(self):
        service = ImportService()
        service.spreadsheet_value_resolver = FakeSpreadsheetValueResolver()
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

        with patch("app.imports.services.import_service.get_import_review_summary", return_value={"id": "job-1", "provider": "blu", "statement_owner": "Reza"}), \
             patch("app.imports.services.import_service.list_import_draft_transactions_by_ids", return_value=selected_drafts), \
             patch("app.imports.services.import_service.create_import_transactions", return_value=[{
                 "id": "txn-1",
                 "import_transaction_fingerprint": "fp-1",
                 "sync_status": "pending",
             }]) as create_transactions_mock, \
             patch("app.imports.services.import_service.register_transaction_fingerprints") as register_fingerprints_mock, \
             patch("app.imports.services.import_service.delete_import_draft_transactions") as delete_drafts_mock, \
             patch.object(ImportCleanupService, "delete_temp_pdf_for_job"), \
             patch("app.imports.services.import_service.count_new_import_draft_transactions", return_value=0), \
             patch("app.imports.services.import_service.update_import_job_status"), \
             patch("app.imports.services.import_service.refresh_import_job_aggregates"), \
             patch("app.imports.services.import_service.update_import_transaction_sync_status") as update_sync_mock, \
             patch.object(SpreadsheetSyncService, "sync_import_transactions") as sync_mock:
            result = service.approve_review_transactions(
                connection=object(),
                workspace={"id": "workspace-1", "google_sheet_id": ""},
                current_user={"sub": "user-1", "name": "Reza", "email": "reza@example.com"},
                workspace_id="workspace-1",
                import_job_id="job-1",
                draft_ids=["draft-1"],
                item_updates=[],
            )

        created_row = create_transactions_mock.call_args.kwargs["rows"][0]
        self.assertIsNone(created_row["sheet_source_id"])
        register_fingerprints_mock.assert_called_once_with(
            unittest.mock.ANY,
            workspace_id="workspace-1",
            rows=[{
                "transaction_fingerprint": "fp-1",
                "provider": "blu",
            }],
        )
        delete_drafts_mock.assert_called_once()
        sync_mock.assert_not_called()
        update_sync_mock.assert_called_once_with(
            unittest.mock.ANY,
            workspace_id="workspace-1",
            transaction_fingerprints=["fp-1"],
            sync_status="pending",
            sync_error_message=unittest.mock.ANY,
        )
        self.assertTrue(result["ledger_saved"])
        self.assertEqual("skipped", result["sync_status"])
        self.assertEqual(1, result["sync_failed"])
        self.assertEqual("skipped", result["sheet_delivery"]["status"])
        self.assertIn("sudah tersimpan di Omon", result["sync_error_message"])

    def test_review_update_without_merchant_display_keeps_parser_name(self):
        service = ImportService()
        draft = {
            "id": "draft-legacy",
            "transaction_fingerprint": "fp-legacy",
            "canonical_fingerprint": "canon-legacy",
            "canonical_fingerprint_date": "canon-date-legacy",
            "statement_owner": "Reza",
            "source_fund": "Blu",
            "datetime": "01/06/2026 08:00",
            "merchant_original": "Fore Coffee 61715",
            "merchant_normalized": "Fore Coffee",
            "amount": 28000,
            "direction": "expense",
            "transaction_type": "DB",
            "review_group": "Makan Bulanan",
            "raw_text": "raw-audit-value",
            "category": "",
            "notes": "",
        }

        merged = service._merge_review_item_updates(
            [draft],
            item_updates=[{
                "draft_id": "draft-legacy",
                "merchant_display": None,
                "category": "Food",
                "notes": "",
            }],
        )

        self.assertEqual("Fore Coffee", merged[0]["merchant_display"])
        self.assertEqual("Fore Coffee 61715", merged[0]["merchant_original"])
        self.assertEqual("raw-audit-value", merged[0]["raw_text"])
        self.assertEqual("fp-legacy", merged[0]["transaction_fingerprint"])

    def test_approve_stale_drafts_skips_approved_and_rejected_registry_rows(self):
        service = ImportService()
        service.spreadsheet_value_resolver = FakeSpreadsheetValueResolver()
        selected_drafts = [
            {
                "id": "draft-approved",
                "transaction_fingerprint": "fp-approved",
                "datetime": "01/06/2026 08:00",
                "merchant_original": "Existing Merchant",
                "merchant_normalized": "Existing Merchant",
                "amount": 28000,
                "direction": "expense",
                "transaction_type": "DB",
                "review_group": "Makan Bulanan",
                "raw_text": "raw-approved",
                "category": "Food",
                "notes": "",
            },
            {
                "id": "draft-rejected",
                "transaction_fingerprint": "fp-rejected",
                "datetime": "01/06/2026 09:00",
                "merchant_original": "Rejected Merchant",
                "merchant_normalized": "Rejected Merchant",
                "amount": 19000,
                "direction": "expense",
                "transaction_type": "DB",
                "review_group": "Makan Bulanan",
                "raw_text": "raw-rejected",
                "category": "Food",
                "notes": "",
            },
        ]

        with patch("app.imports.services.import_service.get_import_review_summary", return_value={"id": "job-1", "provider": "blu", "statement_owner": "Reza"}), \
             patch("app.imports.services.import_service.list_import_draft_transactions_by_ids", return_value=selected_drafts), \
             patch("app.imports.services.import_service.get_registered_transaction_fingerprint_statuses", return_value={
                 "fp-approved": "approved",
                 "fp-rejected": "rejected",
             }), \
             patch("app.imports.services.import_service.create_import_transactions") as create_transactions_mock, \
             patch("app.imports.services.import_service.register_transaction_fingerprints") as register_fingerprints_mock, \
             patch("app.imports.services.import_service.delete_import_draft_transactions") as delete_drafts_mock, \
             patch.object(ImportCleanupService, "delete_temp_pdf_for_job"), \
             patch("app.imports.services.import_service.count_new_import_draft_transactions", return_value=0), \
             patch("app.imports.services.import_service.update_import_job_status"), \
             patch("app.imports.services.import_service.refresh_import_job_aggregates"), \
             patch("app.imports.services.import_service.update_import_transaction_sync_status"):
            result = service.approve_review_transactions(
                connection=object(),
                workspace={"id": "workspace-1", "google_sheet_id": ""},
                current_user={"sub": "user-1", "name": "Reza"},
                workspace_id="workspace-1",
                import_job_id="job-1",
                draft_ids=["draft-approved", "draft-rejected"],
                item_updates=[],
            )

        create_transactions_mock.assert_called_once_with(
            unittest.mock.ANY,
            rows=[],
        )
        register_fingerprints_mock.assert_called_once_with(
            unittest.mock.ANY,
            workspace_id="workspace-1",
            rows=[],
        )
        delete_drafts_mock.assert_called_once_with(
            unittest.mock.ANY,
            import_job_id="job-1",
            draft_ids=["draft-approved", "draft-rejected"],
        )
        self.assertEqual(0, result["approved_count"])
        self.assertEqual(1, result["skipped_existing_count"])
        self.assertEqual(1, result["skipped_rejected_count"])
        self.assertFalse(result["ledger_saved"])

    def test_approve_review_transactions_invalid_target_header_keeps_ledger(self):
        service = ImportService()
        service.spreadsheet_value_resolver = FakeSpreadsheetValueResolver()
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

        with patch("app.imports.services.import_service.get_import_review_summary", return_value={"id": "job-1", "provider": "blu", "statement_owner": "Reza"}), \
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
             patch("app.imports.services.import_service.create_import_transactions", return_value=[{
                 "id": "txn-1",
                 "import_transaction_fingerprint": "fp-1",
             }]) as create_transactions_mock, \
             patch("app.imports.services.import_service.register_transaction_fingerprints") as register_fingerprints_mock, \
             patch("app.imports.services.import_service.delete_import_draft_transactions") as delete_drafts_mock, \
             patch.object(ImportCleanupService, "delete_temp_pdf_for_job"), \
             patch("app.imports.services.import_service.count_new_import_draft_transactions", return_value=0), \
             patch("app.imports.services.import_service.update_import_job_status"), \
             patch("app.imports.services.import_service.refresh_import_job_aggregates"), \
             patch("app.imports.services.import_service.update_import_transaction_sync_status") as update_sync_mock:
            result = service.approve_review_transactions(
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

        create_transactions_mock.assert_called_once()
        register_fingerprints_mock.assert_called_once()
        delete_drafts_mock.assert_called_once()
        update_sync_mock.assert_called_once_with(
            unittest.mock.ANY,
            workspace_id="workspace-1",
            transaction_fingerprints=["fp-1"],
            sync_status="failed",
            sync_error_message="Tab tujuan belum siap menerima salinan transaksi karena format kolomnya belum sesuai.",
        )
        self.assertTrue(result["ledger_saved"])
        self.assertEqual("failed", result["sync_status"])

    def test_approve_review_transactions_insert_failure_keeps_draft_and_skips_sync(self):
        service = ImportService()
        service.spreadsheet_value_resolver = FakeSpreadsheetValueResolver()
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
        service.spreadsheet_value_resolver = FakeSpreadsheetValueResolver()
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
             patch("app.imports.services.import_service.create_import_transactions", return_value=[{
                 "id": "txn-1",
                 "import_transaction_fingerprint": "fp-1",
             }]), \
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
        service.spreadsheet_value_resolver = FakeSpreadsheetValueResolver()
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
             patch("app.imports.services.import_service.create_import_transactions", return_value=[{
                 "id": "txn-1",
                 "import_transaction_fingerprint": "fp-1",
             }]), \
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
            workspace_id="workspace-1",
            transaction_fingerprints=["fp-1"],
            sync_status="failed",
            sync_error_message="append failed",
        )
        delete_drafts_mock.assert_called_once()
        self.assertEqual("failed", approve_result["sync_status"])
        self.assertEqual("append failed", approve_result["sync_error_message"])
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
                    "datetime": "2026-06-13 13:26",
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

    def test_spreadsheet_sync_appends_to_selected_sheet_with_user_name(self):
        sync_service = SpreadsheetSyncService()

        with patch("app.imports.services.spreadsheet_sync_service.get_active_google_oauth_connection", return_value={
            "id": "oauth-1",
            "access_token_encrypted": "encrypted-token",
            "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
        }), \
             patch("app.imports.services.spreadsheet_sync_service.decrypt_text", return_value="access-token"), \
             patch("app.imports.services.spreadsheet_sync_service.get_data_validation_values", side_effect=[
                 ["Reza", "Divya"],
                 ["BCA", "Blu", "GoPay", "OVO", "SeaBank"],
             ]), \
             patch("app.imports.services.spreadsheet_sync_service.append_sheet_values", return_value={
                 "updates": {
                     "updatedRange": "'Start 1 Juni'!A12:G12",
                     "updatedRows": 1,
                 },
             }) as append_values_mock, \
             patch("app.imports.services.spreadsheet_sync_service.get_spreadsheet_metadata", return_value={
                 "sheets": [{
                     "sheet_id": 321,
                     "title": "Start 1 Juni",
                 }],
             }), \
             patch("app.imports.services.spreadsheet_sync_service.read_sheet_values", return_value=[[
                 "Reza",
                 "06/01/2026 08:00",
                 "Template Transaction",
                 "Belanja",
                 100000,
                 "Blu",
                 "",
             ]]), \
             patch("app.imports.services.spreadsheet_sync_service.copy_sheet_row_format_and_validation") as copy_format_mock, \
             patch("app.imports.services.spreadsheet_sync_service.update_google_sheet_last_synced") as update_synced_mock:
            result = sync_service.sync_import_transactions(
                connection=object(),
                workspace={"id": "workspace-1", "google_sheet_id": "sheet-123"},
                current_user={
                    "sub": "user-1",
                    "display_name": "Reza Display",
                    "email": "reza@example.com",
                },
                approved_transactions=[{
                    "datetime": "2026-06-13 13:26",
                    "merchant_display": "SUPERINDO",
                    "merchant_normalized": "SUPERINDO",
                    "amount": 159750,
                    "category": "Belanja",
                    "notes": "Approved manually",
                }],
                target_sheet_source={
                    "id": "sheet-source-1",
                    "sheet_id": "sheet-123",
                    "sheet_name": "Default",
                },
                target_sheet_name="Start 1 Juni",
                user_name="Reza Display",
                source_dana="blu",
                job_id="job-1",
            )

        append_values_mock.assert_called_once_with(
            access_token="access-token",
            spreadsheet_id="sheet-123",
            range_name="Start 1 Juni",
            rows=[[
                "Reza",
                "06/13/2026 13:26",
                "SUPERINDO",
                "Belanja",
                159750,
                "Blu",
                "Approved manually",
            ]],
        )
        update_synced_mock.assert_called_once_with(
            unittest.mock.ANY,
            workspace_id="workspace-1",
            source_id="sheet-source-1",
        )
        copy_format_mock.assert_called_once_with(
            access_token="access-token",
            spreadsheet_id="sheet-123",
            sheet_id=321,
            template_row=2,
            destination_start_row=12,
            destination_end_row=12,
            column_count=7,
        )
        self.assertEqual("success", result["status"])
        self.assertEqual(1, result["sync_success"])
        self.assertEqual("success", result["formatting_status"])

    def test_spreadsheet_formatting_failure_keeps_append_success_with_warning(self):
        sync_service = SpreadsheetSyncService()

        with patch("app.imports.services.spreadsheet_sync_service.get_active_google_oauth_connection", return_value={
            "id": "oauth-1",
            "access_token_encrypted": "encrypted-token",
            "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
        }), \
             patch("app.imports.services.spreadsheet_sync_service.decrypt_text", return_value="access-token"), \
             patch("app.imports.services.spreadsheet_sync_service.get_data_validation_values", side_effect=[
                 ["Reza"],
                 ["Blu"],
             ]), \
             patch("app.imports.services.spreadsheet_sync_service.append_sheet_values", return_value={
                 "updates": {
                     "updatedRange": "'Start 1 Juni'!A12:G12",
                     "updatedRows": 1,
                 },
             }) as append_values_mock, \
             patch.object(
                 SpreadsheetSyncService,
                 "_copy_template_formatting",
                 side_effect=GoogleSheetsClientError("Formatting copy failed"),
             ), \
             patch("app.imports.services.spreadsheet_sync_service.update_google_sheet_last_synced"):
            result = sync_service.sync_import_transactions(
                connection=object(),
                workspace={"id": "workspace-1", "google_sheet_id": "sheet-123"},
                current_user={"sub": "user-1", "name": "Reza"},
                approved_transactions=[{
                    "datetime": "2026-06-13 13:26",
                    "merchant_display": "SUPERINDO",
                    "amount": 189400,
                    "category": "Belanja",
                    "notes": "",
                }],
                target_sheet_source={
                    "id": "sheet-source-1",
                    "sheet_id": "sheet-123",
                    "sheet_name": "Default",
                },
                target_sheet_name="Start 1 Juni",
                user_name="Reza",
                source_dana="Blu",
            )

        append_values_mock.assert_called_once()
        self.assertEqual("success", result["status"])
        self.assertEqual(1, result["sync_success"])
        self.assertEqual(0, result["sync_failed"])
        self.assertEqual("warning", result["formatting_status"])
        self.assertEqual("Formatting copy failed", result["error"])

    def test_validation_unavailable_still_appends_with_warning(self):
        sync_service = SpreadsheetSyncService()

        with patch("app.imports.services.spreadsheet_sync_service.get_active_google_oauth_connection", return_value={
            "id": "oauth-1",
            "access_token_encrypted": "encrypted-token",
            "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
        }), \
             patch("app.imports.services.spreadsheet_sync_service.decrypt_text", return_value="access-token"), \
             patch(
                 "app.imports.services.spreadsheet_sync_service.get_data_validation_values",
                 side_effect=GoogleSheetsClientError("Validation metadata unavailable"),
             ), \
             patch("app.imports.services.spreadsheet_sync_service.append_sheet_values", return_value={
                 "updates": {
                     "updatedRange": "'Start 1 Juni'!A12:G12",
                     "updatedRows": 1,
                 },
             }) as append_values_mock, \
             patch.object(SpreadsheetSyncService, "_copy_template_formatting", return_value={
                 "template_row": 2,
                 "appended_row_range": "12:12",
             }), \
             patch("app.imports.services.spreadsheet_sync_service.update_google_sheet_last_synced"):
            result = sync_service.sync_import_transactions(
                connection=object(),
                workspace={"id": "workspace-1", "google_sheet_id": "sheet-123"},
                current_user={"sub": "user-1", "name": "Reza"},
                approved_transactions=[{
                    "datetime": "2026-06-13 13:26",
                    "merchant_display": "SUPERINDO",
                    "amount": 189400,
                    "category": "Belanja",
                    "notes": "",
                }],
                target_sheet_source={
                    "id": "sheet-source-1",
                    "sheet_id": "sheet-123",
                    "sheet_name": "Default",
                },
                target_sheet_name="Start 1 Juni",
                user_name="Reza",
                source_dana="Blu",
                job_id="job-1",
            )

        append_values_mock.assert_called_once()
        self.assertEqual("success", result["status"])
        self.assertEqual("warning", result["formatting_status"])
        self.assertEqual(
            "Tidak bisa membaca dropdown Google Sheets untuk Nama/Source Dana.",
            result["error"],
        )

    def test_template_row_falls_back_to_nearest_non_empty_row(self):
        sync_service = SpreadsheetSyncService()

        with patch("app.imports.services.spreadsheet_sync_service.read_sheet_values", return_value=[
            [],
            ["Reza", "06/02/2026 08:00", "Existing Transaction"],
        ]):
            template_row = sync_service._resolve_template_row(
                access_token="access-token",
                spreadsheet_id="sheet-123",
                sheet_name="Start 1 Juni",
            )

        self.assertEqual(3, template_row)

    def test_google_client_copies_format_and_data_validation_without_values(self):
        response = MagicMock()
        response.json.return_value = {"replies": [{}, {}]}

        with patch(
            "app.services.google_sheets_client.httpx.post",
            return_value=response,
            create=True,
        ) as post_mock:
            copy_sheet_row_format_and_validation(
                access_token="access-token",
                spreadsheet_id="sheet-123",
                sheet_id=321,
                template_row=2,
                destination_start_row=12,
                destination_end_row=13,
                column_count=7,
            )

        response.raise_for_status.assert_called_once()
        requests = post_mock.call_args.kwargs["json"]["requests"]
        self.assertEqual(
            ["PASTE_FORMAT", "PASTE_DATA_VALIDATION"],
            [request["copyPaste"]["pasteType"] for request in requests],
        )
        self.assertEqual(
            {
                "sheetId": 321,
                "startRowIndex": 1,
                "endRowIndex": 2,
                "startColumnIndex": 0,
                "endColumnIndex": 7,
            },
            requests[0]["copyPaste"]["source"],
        )
        self.assertEqual(
            {
                "sheetId": 321,
                "startRowIndex": 11,
                "endRowIndex": 13,
                "startColumnIndex": 0,
                "endColumnIndex": 7,
            },
            requests[0]["copyPaste"]["destination"],
        )

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
            current_user={"display_name": "Reza Display", "name": "Reza"},
            user_name="Reza",
        )

        self.assertEqual("Reza", row[0])
        self.assertEqual("Ayam Gepuk Pak Gembus", row[2])

    def test_spreadsheet_row_formats_blu_datetime_without_timezone_shift(self):
        row = SpreadsheetSyncService()._build_sheet_row(
            {
                "datetime": "2026-06-13 13:26:00+00:00",
                "merchant_display": "SUPERINDO",
                "amount": 159750,
                "category": "Belanja",
                "notes": "",
                "source_dana": "Blu",
            },
            current_user={"display_name": "Reza Putra Pratama", "name": "Reza"},
        )

        self.assertEqual(
            [
                "Reza",
                "06/13/2026 13:26",
                "SUPERINDO",
                "Belanja",
                159750,
                "Blu",
                "",
            ],
            row,
        )

    def test_spreadsheet_value_resolver_uses_single_existing_name(self):
        resolver = SpreadsheetValueResolver()

        with patch(
            "app.imports.services.spreadsheet_value_resolver.list_workspace_transaction_user_names",
            return_value=["Reza Existing"],
        ):
            self.assertEqual(
                "Reza Existing",
                resolver.resolve_user_name_for_append(
                    connection=object(),
                    workspace_id="workspace-1",
                    current_user={
                        "name": "Different Reza",
                        "display_name": "Reza Putra Pratama",
                    },
                ),
            )

    def test_spreadsheet_value_resolver_user_name_fallback(self):
        resolver = SpreadsheetValueResolver()

        with patch(
            "app.imports.services.spreadsheet_value_resolver.list_workspace_transaction_user_names",
            return_value=[],
        ):
            self.assertEqual(
                "Reza",
                resolver.resolve_user_name_for_append(
                    connection=object(),
                    workspace_id="workspace-1",
                    current_user={
                        "name": "Reza",
                        "display_name": "Reza Putra Pratama",
                        "email": "reza@example.com",
                    },
                ),
            )

    def test_spreadsheet_value_resolver_normalizes_reza_owner_alias(self):
        resolver = SpreadsheetValueResolver()

        with patch(
            "app.imports.services.spreadsheet_value_resolver.list_workspace_transaction_user_names",
            return_value=["Reza"],
        ):
            self.assertEqual(
                "Reza",
                resolver.resolve_user_name_for_append(
                    connection=object(),
                    workspace_id="workspace-1",
                    current_user={
                        "name": "Different Reza",
                        "display_name": "Reza Putra Pratama",
                        "email": "reza@example.com",
                    },
                ),
            )

    def test_spreadsheet_value_resolver_preserves_source_dana_casing(self):
        resolver = SpreadsheetValueResolver()

        with patch(
            "app.imports.services.spreadsheet_value_resolver.list_workspace_transaction_source_funds",
            return_value=["blu"],
        ):
            self.assertEqual(
                "blu",
                resolver.resolve_source_dana_for_append(
                    connection=object(),
                    workspace_id="workspace-1",
                    provider="Blu",
                ),
            )

    def test_dropdown_resolver_matches_exact_case_trimmed_and_prefix_values(self):
        resolver = SpreadsheetValueResolver()

        self.assertEqual(
            {
                "value": "Blu",
                "strategy": "exact",
                "matched": True,
            },
            resolver.resolve_allowed_dropdown_value("Blu", ["BCA", "Blu"]),
        )
        self.assertEqual(
            "Blu",
            resolver.resolve_allowed_dropdown_value("blu", ["BCA", "Blu"])["value"],
        )
        self.assertEqual(
            "Reza",
            resolver.resolve_allowed_dropdown_value(" Reza ", ["Reza"])["value"],
        )
        self.assertEqual(
            {
                "value": "Reza",
                "strategy": "safe_prefix",
                "matched": True,
            },
            resolver.resolve_allowed_dropdown_value(
                "Reza Putra Pratama",
                ["Reza", "Divya"],
                allow_prefix_match=True,
            ),
        )

    def test_google_client_reads_explicit_data_validation_values(self):
        response = MagicMock()
        response.json.return_value = {
            "sheets": [{
                "data": [{
                    "rowData": [{
                        "values": [{
                            "dataValidation": {
                                "condition": {
                                    "type": "ONE_OF_LIST",
                                    "values": [
                                        {"userEnteredValue": "BCA"},
                                        {"userEnteredValue": "Blu"},
                                        {"userEnteredValue": "GoPay"},
                                    ],
                                },
                            },
                        }],
                    }],
                }],
            }],
        }

        with patch(
            "app.services.google_sheets_client.httpx.get",
            return_value=response,
            create=True,
        ) as get_mock:
            values = get_data_validation_values(
                access_token="access-token",
                spreadsheet_id="sheet-123",
                sheet_name="Start 1 Juni",
                column_index_or_letter="F",
                sample_row=2,
            )

        response.raise_for_status.assert_called_once()
        self.assertEqual(["BCA", "Blu", "GoPay"], values)
        self.assertEqual(
            "'Start 1 Juni'!F2:F100",
            get_mock.call_args.kwargs["params"]["ranges"],
        )

    def test_reject_review_transactions_removes_selected_drafts(self):
        service = ImportService()
        selected_drafts = [{
            "id": "draft-2",
            "transaction_fingerprint": "fp-rejected",
        }]

        with patch("app.imports.services.import_service.get_import_review_summary", return_value={
            "id": "job-1",
            "provider": "blu",
        }), \
             patch(
                 "app.imports.services.import_service.list_import_draft_transactions_by_ids",
                 return_value=selected_drafts,
             ), \
             patch(
                 "app.imports.services.import_service.register_rejected_transaction_fingerprints",
             ) as register_rejected_mock, \
             patch("app.imports.services.import_service.reject_import_draft_transactions", return_value=[{"id": "draft-2"}]), \
             patch("app.imports.services.import_service.create_import_transactions") as create_transactions_mock, \
             patch.object(SpreadsheetSyncService, "sync_import_transactions") as sync_mock, \
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
        register_rejected_mock.assert_called_once_with(
            unittest.mock.ANY,
            workspace_id="workspace-1",
            rows=[{
                "transaction_fingerprint": "fp-rejected",
                "provider": "blu",
            }],
        )
        create_transactions_mock.assert_not_called()
        sync_mock.assert_not_called()

    def test_reject_stale_drafts_does_not_change_registry_status(self):
        service = ImportService()
        selected_drafts = [
            {"id": "draft-approved", "transaction_fingerprint": "fp-approved"},
            {"id": "draft-rejected", "transaction_fingerprint": "fp-rejected"},
        ]

        with patch("app.imports.services.import_service.get_import_review_summary", return_value={"id": "job-1", "provider": "blu"}), \
             patch("app.imports.services.import_service.list_import_draft_transactions_by_ids", return_value=selected_drafts), \
             patch("app.imports.services.import_service.get_registered_transaction_fingerprint_statuses", return_value={
                 "fp-approved": "approved",
                 "fp-rejected": "rejected",
             }), \
             patch("app.imports.services.import_service.register_rejected_transaction_fingerprints") as register_mock, \
             patch("app.imports.services.import_service.reject_import_draft_transactions", return_value=[
                 {"id": "draft-approved"},
                 {"id": "draft-rejected"},
             ]), \
             patch("app.imports.services.import_service.increment_import_job_rejected_count") as increment_mock, \
             patch("app.imports.services.import_service.count_new_import_draft_transactions", return_value=0), \
             patch("app.imports.services.import_service.update_import_job_status"):
            result = service.reject_review_transactions(
                connection=object(),
                workspace_id="workspace-1",
                import_job_id="job-1",
                draft_ids=["draft-approved", "draft-rejected"],
            )

        register_mock.assert_called_once_with(
            unittest.mock.ANY,
            workspace_id="workspace-1",
            rows=[],
        )
        increment_mock.assert_called_once_with(
            unittest.mock.ANY,
            job_id="job-1",
            rejected_count=0,
        )
        self.assertEqual(0, result["rejected_count"])
        self.assertEqual(1, result["skipped_existing_count"])
        self.assertEqual(1, result["skipped_rejected_count"])

    def test_retry_sync_uses_existing_unsynced_transactions_and_selected_sheet(self):
        service = ImportService()
        service.spreadsheet_value_resolver = FakeSpreadsheetValueResolver()
        retryable_transactions = [
            {
                "id": "txn-1",
                "user_name": "Reza Display",
                "transaction_fingerprint": "fp-1",
                "datetime": "01/06/2026 08:00",
                "merchant_normalized": "Fore Coffee",
                "category": "Makan",
                "amount": 28000,
                "notes": "",
            },
            {
                "id": "txn-2",
                "user_name": "Reza Display",
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
             patch("app.imports.services.import_service.count_successful_import_transactions", return_value=10), \
             patch("app.imports.services.import_service.get_google_sheet_source", return_value={
                 "id": "sheet-source-1",
                 "sheet_id": "sheet-123",
                 "sheet_name": "Default",
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
             patch.object(SpreadsheetSyncService, "sync_import_transactions", return_value={
                 "status": "success",
                 "sync_success": 2,
                 "sync_failed": 0,
                 "source_id": "sheet-source-1",
                 "error": None,
             }) as sync_mock, \
             patch("app.imports.services.import_service.update_import_transaction_sync_status_by_ids") as update_sync_mock, \
             patch("app.imports.services.import_service.create_import_transactions") as create_transactions_mock, \
             patch("app.imports.services.import_service.register_transaction_fingerprints") as register_fingerprints_mock, \
             patch("app.imports.services.import_service.refresh_import_job_aggregates"):
            result = service.retry_sync_transactions(
                connection=object(),
                workspace={"id": "workspace-1", "google_sheet_id": "sheet-123"},
                current_user={"sub": "user-1", "name": "Reza", "email": "reza@example.com"},
                workspace_id="workspace-1",
                import_job_id="job-1",
                sheet_source_id="sheet-source-1",
                sheet_name="Start 1 Juni",
            )

        update_sync_mock.assert_called_once_with(
            unittest.mock.ANY,
            transaction_ids=["txn-1", "txn-2"],
            sync_status="success",
        )
        sync_mock.assert_called_once()
        self.assertEqual("Reza", sync_mock.call_args.kwargs["user_name"])
        self.assertEqual("Blu", sync_mock.call_args.kwargs["source_dana"])
        self.assertEqual("job-1", sync_mock.call_args.kwargs["job_id"])
        self.assertEqual("Start 1 Juni", sync_mock.call_args.kwargs["target_sheet_name"])
        self.assertEqual(
            "sheet-source-1",
            sync_mock.call_args.kwargs["target_sheet_source"]["id"],
        )
        create_transactions_mock.assert_not_called()
        register_fingerprints_mock.assert_not_called()
        self.assertEqual(2, result["retried_count"])
        self.assertEqual(10, result["skipped_success"])
        self.assertEqual("completed", result["status"])
        self.assertEqual("success", result["sync_status"])

    def test_retry_sync_failure_preserves_transactions_and_stores_error(self):
        service = ImportService()
        service.spreadsheet_value_resolver = FakeSpreadsheetValueResolver()
        retryable_transactions = [
            {
                "id": "txn-1",
                "transaction_fingerprint": "fp-1",
                "datetime": "01/06/2026 08:00",
                "merchant_normalized": "Fore Coffee",
                "category": "Makan",
                "amount": 28000,
                "notes": "",
            },
        ]

        with patch("app.imports.services.import_service.get_import_history_detail", return_value={"id": "job-1"}), \
             patch("app.imports.services.import_service.list_retryable_import_transactions", return_value=retryable_transactions), \
             patch("app.imports.services.import_service.count_successful_import_transactions", return_value=0), \
             patch("app.imports.services.import_service.get_google_sheet_source", return_value={
                 "id": "sheet-source-1",
                 "sheet_id": "sheet-123",
                 "sheet_name": "Default",
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
             patch.object(SpreadsheetSyncService, "sync_import_transactions", return_value={
                 "status": "failed",
                 "sync_success": 0,
                 "sync_failed": 1,
                 "source_id": "sheet-source-1",
                 "error": "append failed",
             }), \
             patch("app.imports.services.import_service.update_import_transaction_sync_status_by_ids") as update_sync_mock, \
             patch("app.imports.services.import_service.delete_import_draft_transactions") as delete_draft_mock, \
             patch("app.imports.services.import_service.create_import_transactions") as create_transactions_mock, \
             patch("app.imports.services.import_service.register_transaction_fingerprints") as register_fingerprints_mock, \
             patch("app.imports.services.import_service.refresh_import_job_aggregates"):
            result = service.retry_sync_transactions(
                connection=object(),
                workspace={"id": "workspace-1", "google_sheet_id": "sheet-123"},
                current_user={"sub": "user-1", "name": "Reza", "email": "reza@example.com"},
                workspace_id="workspace-1",
                import_job_id="job-1",
                sheet_source_id="sheet-source-1",
                sheet_name="Start 1 Juni",
            )

        update_sync_mock.assert_called_once_with(
            unittest.mock.ANY,
            transaction_ids=["txn-1"],
            sync_status="failed",
            sync_error_message="append failed",
        )
        delete_draft_mock.assert_not_called()
        create_transactions_mock.assert_not_called()
        register_fingerprints_mock.assert_not_called()
        self.assertEqual("failed", result["sync_status"])
        self.assertEqual("append failed", result["sync_error_message"])

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
                "spreadsheet_unconfigured": True,
                "temp_file_deleted_at": "2026-06-16T11:00:00Z",
            },
        ]

        with patch("app.imports.services.import_service.count_import_history", return_value=1), \
             patch("app.imports.services.import_service.list_import_history_paginated", return_value=history_rows):
            payload = service.get_history_payload(
                connection=object(),
                workspace_id="workspace-1",
            )

        self.assertEqual(1, len(payload["jobs"]))
        self.assertEqual("cleanup_completed", payload["jobs"][0]["status"])
        self.assertTrue(payload["jobs"][0]["spreadsheet_unconfigured"])
        self.assertEqual("already_deleted", payload["jobs"][0]["pdf_status"])
        self.assertEqual(20, payload["pagination"]["limit"])

    def test_history_detail_includes_unsynced_transactions(self):
        service = ImportService()
        history_job = {
            "id": "job-1",
            "filename": "blu_statement_juni.pdf",
            "provider": "blu",
            "status": "completed",
            "created_at": "2026-06-16T10:00:00Z",
            "transactions_found": 10,
            "new_transactions": 10,
            "existing_transactions": 0,
            "approved_transactions": 10,
            "rejected_transactions": 0,
            "sync_success": 8,
            "sync_failed": 2,
            "retryable_sync_count": 2,
            "needs_reconnect": False,
            "temp_file_deleted_at": "2026-06-16T11:00:00Z",
        }
        unsynced_transactions = [
            {
                "id": "txn-1",
                "date": "01/06/2026",
                "merchant_display": "Fore Coffee",
                "merchant_normalized": "Fore Coffee",
                "category": "Makan",
                "amount": 28000,
                "source_dana": "Blu",
                "sync_status": "failed",
                "sync_error_message": "append failed",
            },
        ]

        with patch("app.imports.services.import_service.get_import_history_detail", return_value=history_job), \
             patch("app.imports.services.import_service.list_retryable_import_transactions", return_value=unsynced_transactions):
            payload = service.get_history_detail_payload(
                connection=object(),
                workspace_id="workspace-1",
                job_id="job-1",
            )

        self.assertEqual(1, payload["unsynced_count"])
        self.assertEqual(8, payload["sync_success_count"])
        self.assertEqual(2, payload["sync_failed_count"])
        self.assertEqual(
            {
                "id": "txn-1",
                "date": "01/06/2026",
                "transaction_name": "Fore Coffee",
                "category": "Makan",
                "amount": 28000.0,
                "source_dana": "Blu",
                "sync_status": "failed",
                "sync_error_message": "append failed",
            },
            payload["unsynced_transactions"][0],
        )


if __name__ == "__main__":
    unittest.main()
