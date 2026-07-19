import unittest
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "db"
    / "migrations"
    / "024_add_import_job_section_context.sql"
)


class BcaSectionContextMigrationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION_PATH.read_text(encoding="utf-8").lower()

    def test_adds_safe_json_context_without_touching_transactions(self):
        self.assertIn("alter table public.import_jobs", self.sql)
        self.assertIn("section_context jsonb not null default '{}'::jsonb", self.sql)
        self.assertNotIn("alter table public.transactions", self.sql)

    def test_context_must_be_a_json_object(self):
        self.assertIn("jsonb_typeof(section_context) = 'object'", self.sql)
        self.assertIn("pg_constraint", self.sql)


if __name__ == "__main__":
    unittest.main()
