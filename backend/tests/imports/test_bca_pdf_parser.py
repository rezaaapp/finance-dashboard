from __future__ import annotations

import io
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

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
fake_psycopg_errors = types.ModuleType("psycopg.errors")
fake_psycopg_rows = types.ModuleType("psycopg.rows")
fake_psycopg_types = types.ModuleType("psycopg.types")
fake_psycopg_types_json = types.ModuleType("psycopg.types.json")
fake_psycopg_pool = types.ModuleType("psycopg_pool")
fake_dotenv = types.ModuleType("dotenv")
fake_httpx = types.ModuleType("httpx")
fake_psycopg_rows.dict_row = object()
fake_psycopg.connect = lambda *args, **kwargs: None
fake_psycopg.DatabaseError = type("DatabaseError", (Exception,), {})
fake_psycopg_errors.UndefinedTable = type("UndefinedTable", (Exception,), {})
fake_psycopg_errors.NotSupportedError = type("NotSupportedError", (Exception,), {})
fake_psycopg.errors = fake_psycopg_errors
fake_psycopg_types_json.Jsonb = lambda value: value
fake_psycopg_pool.ConnectionPool = object
fake_dotenv.dotenv_values = lambda _path: {}
fake_httpx.HTTPError = Exception
fake_httpx.HTTPStatusError = Exception
sys.modules.setdefault("psycopg", fake_psycopg)
sys.modules.setdefault("psycopg.errors", fake_psycopg_errors)
sys.modules.setdefault("psycopg.rows", fake_psycopg_rows)
sys.modules.setdefault("psycopg.types", fake_psycopg_types)
sys.modules.setdefault("psycopg.types.json", fake_psycopg_types_json)
sys.modules.setdefault("psycopg_pool", fake_psycopg_pool)
sys.modules.setdefault("dotenv", fake_dotenv)
sys.modules.setdefault("httpx", fake_httpx)

from app.imports.models.import_models import ImportJobStatus, ParsedImportResult
from app.imports.parsers.base_parser import (
    InvalidSectionSelectionError,
    MalformedTransactionRowError,
    NoParseableTransactionsError,
    SectionSelectionRequiredError,
    UnsupportedStatementError,
)
from app.imports.parsers.bca_pdf_parser import BcaPdfParser
from app.imports.provider_registry import require_import_provider_config
from app.imports.repositories.final_transaction_repository import (
    serialize_import_transaction_row,
)
from app.imports.services.import_service import ImportService
from app.imports.utils.fingerprint import build_transaction_fingerprint
from app.imports.utils.pdf_text_extractor import (
    PdfPasswordRequiredError,
    extract_pdf_metadata,
)
from app.imports.utils.provider_detection import detect_import_provider


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
STATEMENT_PATH = FIXTURE_ROOT / "bca_statement_synthetic.txt"
OVERLAP_PATH = FIXTURE_ROOT / "bca_statement_overlap_synthetic.txt"
EMPTY_PATH = FIXTURE_ROOT / "bca_statement_empty_synthetic.txt"
MALFORMED_PATH = FIXTURE_ROOT / "bca_statement_malformed_synthetic.txt"
MULTI_ACCOUNT_PATH = FIXTURE_ROOT / "bca_statement_multi_account_synthetic.txt"
THREE_SECTION_PATH = FIXTURE_ROOT / "bca_statement_three_section_synthetic.txt"
AMBIGUOUS_SECTION_PATH = (
    FIXTURE_ROOT / "bca_statement_ambiguous_sections_synthetic.txt"
)
GROUND_TRUTH_PATH = FIXTURE_ROOT / "bca_statement_synthetic_ground_truth.json"
STATEMENT_PDF_PATH = FIXTURE_ROOT / "bca_statement_synthetic.pdf"
PERMISSION_ENCRYPTED_PDF_PATH = (
    FIXTURE_ROOT / "bca_permission_encrypted_synthetic.pdf"
)
PASSWORD_REQUIRED_PDF_PATH = FIXTURE_ROOT / "bca_password_required_synthetic.pdf"
SCAN_ONLY_PDF_PATH = FIXTURE_ROOT / "bca_scan_only_synthetic.pdf"


class NamedBytesIO(io.BytesIO):
    def __init__(self, content: bytes, name: str):
        super().__init__(content)
        self.filename = name
        self.file = self
        self.content_type = "application/pdf"
        self.size = len(content)


def read_fixture_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


class BcaPdfParserTestCase(unittest.TestCase):
    def setUp(self):
        self.parser = BcaPdfParser()
        self.statement_lines = read_fixture_lines(STATEMENT_PATH)

    def parse_lines(self, lines: list[str]):
        return self.parser.parse_extracted_lines(
            lines,
            page_count=2,
            extracted_text_length=sum(len(line) for line in lines),
        )

    def extraction_for_lines(self, lines: list[str], *, page_count: int = 1):
        return {
            "lines": lines,
            "page_count": page_count,
            "extracted_text": "\n".join(lines),
            "extracted_text_length": sum(len(line) for line in lines),
            "extracted_text_hash": "synthetic-hash",
        }

    def apply_fingerprints(self, lines: list[str]) -> list[dict]:
        service = ImportService()
        parsed = service.enrich_transactions(self.parse_lines(lines))
        return service.apply_statement_owner(
            parsed,
            statement_owner="Synthetic User",
            source_fund="BCA",
        ).transactions

    def test_synthetic_fixture_matches_ground_truth(self):
        ground_truth = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
        result = self.parse_lines(self.statement_lines)
        compared_fields = (
            "transaction_date",
            "transaction_time",
            "merchant_original",
            "amount",
            "direction",
            "transaction_type",
            "review_group",
            "balance_after",
            "source_reference",
            "source_sequence",
            "raw_text",
        )
        actual = [
            {field: transaction.get(field) for field in compared_fields}
            for transaction in result.transactions
        ]

        self.assertEqual(ground_truth["expected_transaction_count"], len(actual))
        self.assertEqual(ground_truth["transactions"], actual)
        self.assertEqual("bca", result.provider)
        self.assertEqual(BcaPdfParser.PROVIDER_METADATA, result.provider_metadata)
        self.assertTrue(all(item["transaction_time"] is None for item in actual))
        self.assertTrue(all(item["datetime"].endswith(" 00:00") for item in result.transactions))
        self.assertEqual(
            list(range(1, 14)),
            [item["source_sequence"] for item in result.transactions],
        )

    def test_actual_synthetic_pdf_supports_multiple_pages(self):
        result = self.parser.parse(io.BytesIO(STATEMENT_PDF_PATH.read_bytes()))

        self.assertEqual(2, result.page_count)
        self.assertEqual(13, len(result.transactions))
        self.assertEqual(
            list(range(1, 14)),
            [item["source_sequence"] for item in result.transactions],
        )

    def test_valid_empty_statement_is_successful(self):
        result = self.parse_lines(read_fixture_lines(EMPTY_PATH))

        self.assertTrue(result.statement_empty)
        self.assertEqual([], result.transactions)
        self.assertEqual([], result.warnings)

    def test_malformed_transaction_row_is_controlled(self):
        with self.assertRaises(MalformedTransactionRowError) as raised:
            self.parse_lines(read_fixture_lines(MALFORMED_PATH))

        self.assertEqual("malformed_transaction_row", raised.exception.error_code)

    def test_ambiguous_printed_balance_is_omitted_with_warning(self):
        lines = [
            "REKENING TAHAPAN XPRESI",
            "NASABAH SINTETIS NO. REKENING : 1234567890",
            "PERIODE : JUNI 2026",
            "TANGGAL KETERANGAN CBG MUTASI SALDO",
            "14/06 TRANSAKSI DEBIT SALDO AMBIGU 20,000.00 DB TIDAK-TERBACA",
        ]

        result = self.parse_lines(lines)

        self.assertEqual(1, len(result.transactions))
        self.assertIsNone(result.transactions[0]["balance_after"])
        self.assertEqual(["ambiguous_balance"], result.warnings)

    def test_multi_account_statement_requires_section_selection(self):
        with self.assertRaises(SectionSelectionRequiredError) as raised:
            self.parse_lines(read_fixture_lines(MULTI_ACCOUNT_PATH))

        self.assertEqual("section_selection_required", raised.exception.error_code)

    def test_discovers_deterministic_masked_section_candidates(self):
        lines = read_fixture_lines(THREE_SECTION_PATH)

        first = self.parser.discover_sections(lines)
        repeated = self.parser.discover_sections(lines)
        candidates = first.candidates

        self.assertEqual(3, len(candidates))
        self.assertEqual(
            ["Rekening 1", "Pocket 1", "Pocket 2"],
            [candidate.display_label for candidate in candidates],
        )
        self.assertEqual(
            ["account", "pocket", "pocket"],
            [candidate.section_type for candidate in candidates],
        )
        self.assertEqual(
            [2, 2, 0],
            [candidate.transaction_count_estimate for candidate in candidates],
        )
        self.assertEqual(
            [True, True, False],
            [candidate.is_selectable for candidate in candidates],
        )
        self.assertEqual(
            [candidate.model_dump() for candidate in candidates],
            [candidate.model_dump() for candidate in repeated.candidates],
        )
        self.assertTrue(
            all(candidate.masked_identity.startswith("**** ") for candidate in candidates)
        )
        for full_identity in ("1111222233", "4444555566", "7777888899"):
            self.assertTrue(
                all(full_identity not in candidate.masked_identity for candidate in candidates)
            )
            self.assertTrue(
                all(full_identity not in candidate.section_id for candidate in candidates)
            )

    def test_multi_page_section_remains_single_and_preserves_sequence(self):
        discovery = self.parser.discover_sections(
            read_fixture_lines(THREE_SECTION_PATH)
        )
        result = self.parser.parse_selected_section(
            discovery,
            selected_section_id=discovery.candidates[0].section_id,
        )

        self.assertEqual(3, len(discovery.sections))
        self.assertEqual(2, len(result.transactions))
        self.assertEqual([1, 2], [item["source_sequence"] for item in result.transactions])
        self.assertIn(
            "DESKRIPSI LANJUTAN SINTETIS",
            result.transactions[1]["merchant_original"],
        )

    def test_account_reference_in_description_is_masked_not_split(self):
        lines = [
            "REKENING TAHAPAN XPRESI",
            "NASABAH SINTETIS NO. REKENING : 1111222233",
            "PERIODE : JUNI 2026",
            "TANGGAL KETERANGAN CBG MUTASI SALDO",
            "01/06 TRSF E-BANKING DB 25,000.00 DB 975,000.00",
            "NO. REKENING : 9999000012",
            "PENERIMA SINTETIS",
        ]

        discovery = self.parser.discover_sections(lines)
        result = self.parser.parse_selected_section(
            discovery,
            selected_section_id=discovery.candidates[0].section_id,
        )

        self.assertEqual(1, len(discovery.sections))
        self.assertEqual(1, len(result.transactions))
        self.assertNotIn("9999000012", result.transactions[0]["merchant_original"])
        self.assertNotIn("9999000012", result.transactions[0]["raw_text"])
        self.assertIn("**** 0012", result.transactions[0]["merchant_original"])

    def test_selected_section_is_isolated(self):
        discovery = self.parser.discover_sections(
            read_fixture_lines(THREE_SECTION_PATH)
        )
        result = self.parser.parse_selected_section(
            discovery,
            selected_section_id=discovery.candidates[1].section_id,
        )

        self.assertEqual(2, len(result.transactions))
        self.assertTrue(
            any("POCKET SINTETIS" in item["merchant_original"] for item in result.transactions)
        )
        self.assertTrue(
            all("SYNTH001" not in item["merchant_original"] for item in result.transactions)
        )
        self.assertEqual(discovery.candidates[1], result.selected_section)
        self.assertTrue(result.is_multi_account)

    def test_invalid_and_empty_section_selection_are_controlled(self):
        discovery = self.parser.discover_sections(
            read_fixture_lines(THREE_SECTION_PATH)
        )

        with self.assertRaises(InvalidSectionSelectionError) as invalid:
            self.parser.parse_selected_section(
                discovery,
                selected_section_id="bca-section-not-from-this-file",
            )
        self.assertEqual("invalid_section_selection", invalid.exception.error_code)

        with self.assertRaises(NoParseableTransactionsError) as empty:
            self.parser.parse_selected_section(
                discovery,
                selected_section_id=discovery.candidates[2].section_id,
            )
        self.assertEqual("no_parseable_transactions", empty.exception.error_code)

    def test_reappearing_account_boundary_is_unsupported(self):
        with self.assertRaises(UnsupportedStatementError) as raised:
            self.parser.discover_sections(read_fixture_lines(AMBIGUOUS_SECTION_PATH))

        self.assertEqual("unsupported_statement", raised.exception.error_code)

    def test_same_transaction_in_different_pockets_has_distinct_fingerprint(self):
        service = ImportService()
        lines = read_fixture_lines(THREE_SECTION_PATH)
        discovery = self.parser.discover_sections(lines)

        def selected_fingerprints(candidate_index: int):
            parsed = self.parser.parse_selected_section(
                discovery,
                selected_section_id=discovery.candidates[candidate_index].section_id,
            )
            enriched = service.enrich_transactions(parsed)
            return service.apply_statement_owner(
                enriched,
                statement_owner="Synthetic User",
                source_fund="BCA",
            ).transactions

        main_first = selected_fingerprints(0)
        main_reimport = selected_fingerprints(0)
        pocket = selected_fingerprints(1)
        main_duplicate = next(
            item for item in main_first if "LINTAS SECTION" in item["merchant_original"]
        )
        pocket_duplicate = next(
            item for item in pocket if "LINTAS SECTION" in item["merchant_original"]
        )

        self.assertNotEqual(
            main_duplicate["transaction_fingerprint"],
            pocket_duplicate["transaction_fingerprint"],
        )
        self.assertEqual(
            [item["transaction_fingerprint"] for item in main_first],
            [item["transaction_fingerprint"] for item in main_reimport],
        )

    def test_identical_transactions_remain_distinct_and_stable(self):
        first_import = self.apply_fingerprints(self.statement_lines)
        repeated_import = self.apply_fingerprints(self.statement_lines)
        identical = [
            transaction
            for transaction in first_import
            if transaction["transaction_date"] == "11/06/2026"
        ]

        self.assertEqual([1, 2], [item["source_occurrence"] for item in identical])
        self.assertEqual(2, len({item["transaction_fingerprint"] for item in identical}))
        self.assertEqual(
            [item["transaction_fingerprint"] for item in first_import],
            [item["transaction_fingerprint"] for item in repeated_import],
        )

    def test_overlap_uses_the_same_fingerprints_without_source_sequence(self):
        full_statement = self.apply_fingerprints(self.statement_lines)
        overlapping_statement = self.apply_fingerprints(read_fixture_lines(OVERLAP_PATH))
        full_fingerprints = {
            item["transaction_fingerprint"]
            for item in full_statement
        }
        overlap_fingerprints = {
            item["transaction_fingerprint"]
            for item in overlapping_statement
        }

        self.assertTrue(overlap_fingerprints)
        self.assertTrue(overlap_fingerprints.issubset(full_fingerprints))
        self.assertNotEqual(
            [10, 11, 12, 13],
            [item["source_sequence"] for item in overlapping_statement],
        )

    def test_reimport_and_overlap_are_marked_existing(self):
        service = ImportService()
        first_import = self.apply_fingerprints(self.statement_lines)
        fingerprint_statuses = {
            item["transaction_fingerprint"]: "approved"
            for item in first_import
        }
        repeated_result = ParsedImportResult(
            provider="bca",
            transactions=self.apply_fingerprints(self.statement_lines),
        )
        overlap_result = ParsedImportResult(
            provider="bca",
            transactions=self.apply_fingerprints(read_fixture_lines(OVERLAP_PATH)),
        )

        with patch(
            "app.imports.services.import_service.get_registered_transaction_fingerprint_statuses",
            return_value=fingerprint_statuses,
        ), patch(
            "app.imports.services.import_service."
            "get_existing_transactions_by_canonical_fingerprint",
            return_value={},
        ):
            repeated_marked = service.mark_existing_transactions(
                connection=object(),
                workspace_id="workspace-synthetic",
                parsed_result=repeated_result,
            )
            overlap_marked = service.mark_existing_transactions(
                connection=object(),
                workspace_id="workspace-synthetic",
                parsed_result=overlap_result,
            )

        self.assertTrue(all(item["is_existing"] for item in repeated_marked.transactions))
        self.assertTrue(all(item["is_existing"] for item in overlap_marked.transactions))

    def test_bca_detection_preserves_blu_and_reports_mismatch(self):
        self.assertEqual(
            {"provider": "bca", "detection_source": "content"},
            detect_import_provider(
                filename="statement.pdf",
                extracted_text="REKENING TAHAPAN XPRESI",
            ),
        )
        self.assertEqual(
            {"provider": "blu", "detection_source": "content"},
            detect_import_provider(
                filename="statement.pdf",
                extracted_text="bluAccount | bluSpending dari BCA Digital",
            ),
        )
        digital_result = detect_import_provider(
            filename="bca-digital.pdf",
            extracted_text="bluAccount | bluSpending dari BCA Digital",
        )
        self.assertEqual("blu", digital_result["provider"])
        mismatch_result = detect_import_provider(
            filename="bca-statement.pdf",
            extracted_text="bluAccount | bluSpending dari BCA Digital",
        )
        self.assertEqual("provider_mismatch", mismatch_result["error_code"])
        self.assertEqual("mismatch", mismatch_result["detection_source"])

    def test_bca_provider_and_persistence_metadata(self):
        provider = require_import_provider_config("bca")
        parsed_transaction = self.apply_fingerprints(self.statement_lines)[0]
        row = serialize_import_transaction_row(
            workspace_id="workspace-synthetic",
            sheet_source_id=None,
            import_job_id="job-synthetic",
            user_name="Synthetic User",
            provider=provider.key,
            source_fund=provider.source_fund,
            source_origin=provider.source_origin,
            transaction={
                **parsed_transaction,
                "merchant_display": parsed_transaction["merchant_normalized"],
                "_section_id": "bca-section-synthetic",
                "_section_label": "Pocket 1",
                "_masked_section_identity": "**** 5566",
                "_is_multi_account_statement": True,
            },
        )

        self.assertEqual("BCA", row["source_fund"])
        self.assertEqual("bca_pdf", row["source_origin"])
        self.assertEqual("bca", row["raw_payload"]["_import_provider"])
        self.assertIsNone(row["raw_payload"]["transaction_time"])
        self.assertTrue(row["raw_payload"]["_technical_datetime_adapter"])
        self.assertEqual(1, row["raw_payload"]["source_sequence"])
        self.assertEqual("bca-section-synthetic", row["raw_payload"]["section_id"])
        self.assertEqual("Pocket 1", row["raw_payload"]["section_label"])
        self.assertEqual("**** 5566", row["raw_payload"]["masked_section_identity"])
        self.assertTrue(row["raw_payload"]["is_multi_account_statement"])

        review_item = ImportService()._serialize_review_transaction(
            {
                **parsed_transaction,
                "id": "draft-synthetic",
                "status": "new",
                "category": "",
                "notes": "",
            },
            summary={
                "provider": "bca",
                "statement_owner": "Synthetic User",
            },
        )
        self.assertEqual("01/06/2026", review_item["datetime"])
        self.assertEqual("01/06/2026", review_item["transaction_date"])
        self.assertIsNone(review_item["transaction_time"])

    def test_review_and_history_expose_safe_section_context(self):
        section_context = {
            "section_id": "bca-section-synthetic",
            "display_label": "Pocket 1",
            "masked_identity": "**** 5566",
            "section_type": "pocket",
            "transaction_count": 2,
            "is_multi_account": True,
        }
        summary = {
            "id": "job-synthetic",
            "filename": "statement.pdf",
            "provider": "bca",
            "statement_owner": "Synthetic User",
            "transactions_found": 2,
            "new_transactions": 2,
            "existing_transactions": 0,
            "created_at": "2026-06-30T10:00:00Z",
            "section_context": section_context,
        }
        service = ImportService()

        with patch(
            "app.imports.services.import_service.get_import_review_summary",
            return_value=summary,
        ), patch(
            "app.imports.services.import_service.get_import_review_filter_counts",
            return_value={"total_count": 0},
        ), patch(
            "app.imports.services.import_service."
            "list_import_draft_transactions_paginated",
            return_value=[],
        ):
            review = service.get_review_payload(
                connection=object(),
                workspace_id="workspace-synthetic",
                job_id="job-synthetic",
            )

        history = service._serialize_history_job({
            **summary,
            "status": "review",
            "approved_transactions": 0,
            "rejected_transactions": 0,
            "sync_success": 0,
            "sync_failed": 0,
        })

        self.assertEqual(section_context, review["summary"]["section_context"])
        self.assertEqual(section_context, history["section_context"])

    def test_password_required_pdf_is_distinct_from_permission_encryption(self):
        with self.assertRaises(PdfPasswordRequiredError):
            extract_pdf_metadata(io.BytesIO(PASSWORD_REQUIRED_PDF_PATH.read_bytes()))

        extraction = extract_pdf_metadata(
            io.BytesIO(PERMISSION_ENCRYPTED_PDF_PATH.read_bytes())
        )
        self.assertGreater(extraction["extracted_text_length"], 0)

    def test_scan_only_pdf_has_no_text_layer(self):
        extraction = extract_pdf_metadata(io.BytesIO(SCAN_ONLY_PDF_PATH.read_bytes()))

        self.assertEqual(0, extraction["extracted_text_length"])

    def test_valid_empty_upload_completes_without_parser_error(self):
        lines = read_fixture_lines(EMPTY_PATH)
        extraction = {
            "lines": lines,
            "page_count": 1,
            "extracted_text": "\n".join(lines),
            "extracted_text_length": sum(len(line) for line in lines),
            "extracted_text_hash": "synthetic-hash",
        }
        result = self._receive_with_extraction(
            filename="bca-empty.pdf",
            extraction=extraction,
        )

        self.assertEqual(ImportJobStatus.COMPLETED, result.status)
        self.assertEqual(0, result.transactions_found)
        self.assertTrue(result.no_new_transactions)
        self.assertIsNone(result.error_code)

    def test_multi_section_upload_returns_candidates_without_drafts(self):
        lines = read_fixture_lines(THREE_SECTION_PATH)

        result = self._receive_with_extraction(
            filename="bca-multi-synthetic.pdf",
            extraction=self.extraction_for_lines(lines, page_count=3),
            expected_provider="bca",
        )

        self.assertEqual(ImportJobStatus.FAILED, result.status)
        self.assertEqual("section_selection_required", result.error_code)
        self.assertEqual(3, len(result.section_candidates))
        self.assertTrue(result.is_multi_account)
        self.assertEqual([], self.last_persisted_drafts)
        self.assertEqual([], self.last_section_contexts)

    def test_selected_upload_persists_only_one_section_and_safe_context(self):
        lines = read_fixture_lines(THREE_SECTION_PATH)
        discovery = self.parser.discover_sections(lines)

        result = self._receive_with_extraction(
            filename="bca-multi-synthetic.pdf",
            extraction=self.extraction_for_lines(lines, page_count=3),
            expected_provider="bca",
            expected_section_id=discovery.candidates[1].section_id,
        )

        self.assertEqual(ImportJobStatus.REVIEW, result.status)
        self.assertEqual(2, result.transactions_found)
        self.assertEqual(discovery.candidates[1], result.selected_section)
        self.assertEqual(2, len(self.last_persisted_drafts))
        self.assertTrue(
            all("SYNTH001" not in draft["raw_text"] for draft in self.last_persisted_drafts)
        )
        self.assertEqual(1, len(self.last_section_contexts))
        self.assertEqual(
            {
                "section_id": discovery.candidates[1].section_id,
                "display_label": "Pocket 1",
                "masked_identity": discovery.candidates[1].masked_identity,
                "section_type": "pocket",
                "transaction_count": 2,
                "is_multi_account": True,
            },
            self.last_section_contexts[0],
        )

    def test_upload_rejects_invalid_or_empty_selected_section(self):
        lines = read_fixture_lines(THREE_SECTION_PATH)
        discovery = self.parser.discover_sections(lines)

        invalid = self._receive_with_extraction(
            filename="bca-multi-synthetic.pdf",
            extraction=self.extraction_for_lines(lines, page_count=3),
            expected_provider="bca",
            expected_section_id="bca-section-foreign",
        )
        self.assertEqual("invalid_section_selection", invalid.error_code)
        self.assertEqual(3, len(invalid.section_candidates))
        self.assertEqual([], self.last_persisted_drafts)

        empty = self._receive_with_extraction(
            filename="bca-multi-synthetic.pdf",
            extraction=self.extraction_for_lines(lines, page_count=3),
            expected_provider="bca",
            expected_section_id=discovery.candidates[2].section_id,
        )
        self.assertEqual("no_parseable_transactions", empty.error_code)
        self.assertEqual([], self.last_persisted_drafts)

    def test_expected_provider_is_validated_against_server_detection(self):
        lines = read_fixture_lines(STATEMENT_PATH)

        result = self._receive_with_extraction(
            filename="statement.pdf",
            extraction=self.extraction_for_lines(lines),
            expected_provider="blu",
        )

        self.assertEqual(ImportJobStatus.FAILED, result.status)
        self.assertEqual("provider_mismatch", result.error_code)
        self.assertEqual([], self.last_persisted_drafts)

    def test_provider_mismatch_upload_is_controlled(self):
        extraction = {
            "lines": ["bluAccount | bluSpending"],
            "page_count": 1,
            "extracted_text": "bluAccount | bluSpending dari BCA Digital",
            "extracted_text_length": 45,
            "extracted_text_hash": "synthetic-hash",
        }
        result = self._receive_with_extraction(
            filename="bca-statement.pdf",
            extraction=extraction,
        )

        self.assertEqual(ImportJobStatus.FAILED, result.status)
        self.assertEqual("provider_mismatch", result.error_code)

    def test_bca_scan_only_upload_is_controlled(self):
        result = self._receive_with_extraction(
            filename="bca-scan.pdf",
            extraction={
                "lines": [],
                "page_count": 1,
                "extracted_text": "",
                "extracted_text_length": 0,
                "extracted_text_hash": "synthetic-hash",
            },
        )

        self.assertEqual(ImportJobStatus.FAILED, result.status)
        self.assertEqual("scan_only_pdf", result.error_code)

    def test_expected_bca_scan_only_upload_with_generic_filename_is_controlled(self):
        result = self._receive_with_extraction(
            filename="statement.pdf",
            extraction={
                "lines": [],
                "page_count": 1,
                "extracted_text": "",
                "extracted_text_length": 0,
                "extracted_text_hash": "synthetic-hash",
            },
            expected_provider="bca",
        )

        self.assertEqual(ImportJobStatus.FAILED, result.status)
        self.assertEqual("scan_only_pdf", result.error_code)

    def test_password_required_upload_is_controlled(self):
        result = self._receive_with_extraction(
            filename="bca-password.pdf",
            extraction_error=PdfPasswordRequiredError("password required"),
        )

        self.assertEqual(ImportJobStatus.FAILED, result.status)
        self.assertEqual("encrypted_pdf", result.error_code)

    def test_blu_fingerprint_regression_value_is_unchanged(self):
        self.assertEqual(
            "ac7ec82fb1c370473727c8e808fb63f319c398456aa103759b3cb3f8df35e764",
            build_transaction_fingerprint(
                owner_name="Reza",
                source_dana="Blu",
                datetime_value="16/06/2026 08:30",
                merchant_normalized="Fore Coffee",
                amount=28000,
                direction="expense",
            ),
        )

    def _receive_with_extraction(
        self,
        *,
        filename: str,
        extraction: dict | None = None,
        extraction_error: Exception | None = None,
        expected_provider: str | None = None,
        expected_section_id: str | None = None,
    ):
        upload = NamedBytesIO(b"%PDF-synthetic", filename)
        captured_drafts = []
        captured_section_contexts = []
        fake_job = {
            "id": "job-synthetic",
            "provider": "bca",
            "status": "uploaded",
        }
        with patch(
            "app.imports.services.import_service.create_import_job",
            return_value=fake_job,
        ), patch(
            "app.imports.services.import_service.save_temp_import_file",
            return_value={
                "path": str(EMPTY_PATH),
                "expires_at": "2026-06-17T10:00:00Z",
            },
        ), patch(
            "app.imports.services.import_service.set_import_job_temp_file",
        ), patch(
            "app.imports.services.import_service.update_import_job_provider",
        ), patch(
            "app.imports.services.import_service.update_import_job_section_context",
            side_effect=lambda *args, **kwargs: captured_section_contexts.append(
                kwargs["section_context"]
            ),
        ), patch(
            "app.imports.services.import_service.update_import_job_summary",
        ), patch(
            "app.imports.services.import_service.update_import_job_status",
        ), patch(
            "app.imports.services.import_service.extract_pdf_metadata",
            return_value=extraction,
            side_effect=extraction_error,
        ), patch(
            "app.imports.services.import_service.create_import_draft_transactions",
            side_effect=lambda *args, **kwargs: captured_drafts.extend(
                kwargs["draft_transactions"]
            ),
        ), patch(
            "app.imports.services.import_service."
            "get_registered_transaction_fingerprint_statuses",
            return_value={},
        ), patch(
            "app.imports.services.import_service."
            "get_existing_transactions_by_canonical_fingerprint",
            return_value={},
        ):
            result = ImportService().receive_upload(
                connection=object(),
                workspace_id="workspace-synthetic",
                file=upload,
                statement_owner="Synthetic User",
                expected_provider=expected_provider,
                expected_section_id=expected_section_id,
            )
        self.last_persisted_drafts = captured_drafts
        self.last_section_contexts = captured_section_contexts
        return result


if __name__ == "__main__":
    unittest.main()
