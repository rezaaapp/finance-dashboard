from __future__ import annotations

import io
import unittest
from pathlib import Path

from app.imports.parsers.blu_pdf_parser import BluPdfParser
from app.imports.provider_registry import (
    ImportProviderUnavailableError,
    UnknownImportProviderError,
    get_import_provider_config,
    require_import_parser_class,
    require_import_provider_config,
)
from app.imports.repositories.final_transaction_repository import (
    serialize_import_transaction_row,
)
from app.imports.services.import_service import ImportService
from app.imports.utils.pdf_text_extractor import extract_pdf_metadata
from app.imports.utils.provider_detection import detect_import_provider


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REAL_BLU_FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "blu_statement_june_real.pdf"
BCA_SOURCE_ORIGIN_MIGRATION = (
    PROJECT_ROOT / "db" / "migrations" / "023_allow_bca_pdf_source_origin.sql"
)


class ImportProviderRegistryTestCase(unittest.TestCase):
    def test_blu_metadata_matches_protected_baseline(self):
        provider = require_import_provider_config("blu")

        self.assertEqual("blu", provider.key)
        self.assertEqual("Blu", provider.label)
        self.assertEqual("Blu", provider.source_fund)
        self.assertEqual("blu_pdf", provider.source_origin)
        self.assertIs(BluPdfParser, provider.parser_class)
        self.assertTrue(provider.import_enabled)
        self.assertTrue(provider.parser_available)

    def test_bca_metadata_is_registered_but_import_is_disabled(self):
        provider = require_import_provider_config("bca")

        self.assertEqual("bca", provider.key)
        self.assertEqual("BCA", provider.label)
        self.assertEqual("BCA", provider.source_fund)
        self.assertEqual("bca_pdf", provider.source_origin)
        self.assertIsNone(provider.parser_class)
        self.assertFalse(provider.import_enabled)
        self.assertFalse(provider.parser_available)

        with self.assertRaises(ImportProviderUnavailableError):
            require_import_parser_class("bca")

    def test_unknown_provider_never_falls_back_to_blu(self):
        self.assertIsNone(get_import_provider_config("unknown-bank"))

        with self.assertRaises(UnknownImportProviderError):
            require_import_provider_config("unknown-bank")

        with self.assertRaises(UnknownImportProviderError):
            ImportService().parse(io.BytesIO(b"not-read"), provider="unknown-bank")

    def test_existing_blu_detection_markers_are_preserved(self):
        self.assertEqual(
            {"provider": "blu", "detection_source": "filename"},
            detect_import_provider(filename="blu-estatement.pdf"),
        )
        self.assertEqual(
            {"provider": "blu", "detection_source": "content"},
            detect_import_provider(
                filename="statement.pdf",
                extracted_text="Ringkasan bluAccount | bluSpending dari BCA Digital",
            ),
        )

    def test_disabled_bca_is_not_detected_as_an_active_provider(self):
        self.assertEqual(
            {"provider": "unknown", "detection_source": "unknown"},
            detect_import_provider(
                filename="bca-estatement.pdf",
                extracted_text="Bank Central Asia account statement",
            ),
        )

    def test_generic_pdf_extraction_matches_blu_compatibility_method(self):
        with REAL_BLU_FIXTURE_PATH.open("rb") as fixture:
            generic_extraction = extract_pdf_metadata(fixture)
        with REAL_BLU_FIXTURE_PATH.open("rb") as fixture:
            blu_extraction = BluPdfParser().extract_pdf_metadata(fixture)

        self.assertEqual(blu_extraction, generic_extraction)

    def test_blu_serializer_metadata_matches_protected_baseline(self):
        provider = require_import_provider_config("blu")
        row = serialize_import_transaction_row(
            workspace_id="workspace-1",
            sheet_source_id=None,
            import_job_id="job-1",
            user_name="Reza",
            provider=provider.key,
            source_fund=provider.source_fund,
            source_origin=provider.source_origin,
            transaction={
                "datetime": "16/06/2026 08:30",
                "merchant_original": "Fore Coffee",
                "merchant_normalized": "Fore Coffee",
                "merchant_display": "Fore Coffee",
                "amount": 28000,
                "direction": "expense",
                "transaction_type": "DB",
                "transaction_fingerprint": "fingerprint-1",
            },
        )

        self.assertEqual("Blu", row["source_fund"])
        self.assertEqual("blu_pdf", row["source_origin"])
        self.assertEqual("blu", row["raw_payload"]["_import_provider"])

    def test_migration_extends_source_origin_constraint_without_editing_history(self):
        sql = BCA_SOURCE_ORIGIN_MIGRATION.read_text(encoding="utf-8").lower()

        self.assertIn("drop constraint if exists transactions_source_origin_check", sql)
        self.assertIn(
            "check (source_origin in ('google_sheet', 'blu_pdf', 'bca_pdf'))",
            sql,
        )


if __name__ == "__main__":
    unittest.main()
