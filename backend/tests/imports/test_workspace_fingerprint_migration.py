import unittest
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "db"
    / "migrations"
    / "019_scope_import_fingerprints_by_workspace.sql"
)


class WorkspaceFingerprintMigrationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION_PATH.read_text(encoding="utf-8").lower()

    def test_registry_primary_key_is_workspace_scoped(self):
        self.assertIn(
            "primary key (workspace_id, transaction_fingerprint)",
            self.sql,
        )

    def test_final_transaction_unique_indexes_are_workspace_scoped(self):
        self.assertIn(
            "on public.transactions (workspace_id, import_transaction_fingerprint)",
            self.sql,
        )
        self.assertIn(
            "on public.transactions (workspace_id, canonical_fingerprint)",
            self.sql,
        )

    def test_unresolved_legacy_registry_rows_are_archived(self):
        self.assertIn(
            "legacy_unscoped_import_transaction_registry",
            self.sql,
        )
        self.assertIn(
            "where workspace_id is null",
            self.sql,
        )

    def test_within_workspace_duplicates_block_migration(self):
        self.assertIn(
            "duplicate import fingerprints exist within a workspace",
            self.sql,
        )
        self.assertIn(
            "duplicate canonical fingerprints exist within a workspace",
            self.sql,
        )


if __name__ == "__main__":
    unittest.main()
