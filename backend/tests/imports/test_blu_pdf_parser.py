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


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "blu_statement_sample.pdf"


class NamedBytesIO(io.BytesIO):
    def __init__(self, content: bytes, name: str):
        super().__init__(content)
        self.filename = name
        self.file = self


class BluPdfParserTestCase(unittest.TestCase):
    def setUp(self):
        self.parser = BluPdfParser()
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
        self.assertEqual("Top Up dari Bank Lain", transactions[0]["merchant"])
        self.assertEqual(1500000.0, transactions[0]["amount"])
        self.assertEqual("income", transactions[0]["direction"])
        self.assertEqual("CR", transactions[0]["transaction_type"])
        self.assertIn("Fore Coffee", transactions[1]["merchant"])
        self.assertEqual(28000.0, transactions[1]["amount"])

    def test_import_service_calls_blu_parser_and_returns_preview(self):
        fake_upload = NamedBytesIO(self.fixture_bytes, "blu-estatement-june.pdf")
        fake_job = {
            "id": "job-123",
            "provider": "blu",
            "status": "uploaded",
        }

        with patch("app.imports.services.import_service.create_import_job", return_value=fake_job):
            result = ImportService().receive_upload(
                connection=object(),
                workspace_id="workspace-1",
                file=fake_upload,
            )

        self.assertEqual("blu", result.provider)
        self.assertEqual("uploaded", result.status)
        self.assertEqual(4, result.transactions_found)
        self.assertEqual(4, len(result.preview))
        self.assertEqual("14/06/2026 09:15", result.preview[0].datetime)
        self.assertEqual("Top Up dari Bank Lain", result.preview[0].merchant)


if __name__ == "__main__":
    unittest.main()
