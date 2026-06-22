import unittest
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "db"
    / "migrations"
    / "021_backfill_blu_transaction_search_index.sql"
)


class BluSearchIndexMigrationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION_PATH.read_text(encoding="utf-8").lower()

    def test_backfill_is_scoped_to_blu_transactions_with_empty_search_index(self):
        self.assertIn("where source_origin = 'blu_pdf'", self.sql)
        self.assertIn("and search_text_normalized = ''", self.sql)

    def test_backfill_uses_the_existing_search_field_contract(self):
        for field in (
            "title",
            "raw_category",
            "raw_payload->>'_category_normalized'",
            "source_fund",
            "note",
        ):
            self.assertIn(field, self.sql)


if __name__ == "__main__":
    unittest.main()
