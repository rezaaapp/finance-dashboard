import unittest

from backend.scripts.database_lifecycle import (
    LOCAL_DATABASE,
    SUPABASE_MIGRATE_PHRASE,
    SUPABASE_RESET_PHRASE,
    parse_database_target,
    validate_environment,
)


def environment_for(target):
    if target == "local-dev":
        return {
            "APP_ENV": "local-dev",
            "ENV_PROFILE": "local-dev",
            "DB_TARGET": "postgres-local",
            "DATABASE_URL": (
                "postgresql://postgres:secret@127.0.0.1:5432/"
                f"{LOCAL_DATABASE}"
            ),
        }
    return {
        "APP_ENV": "local-prod",
        "ENV_PROFILE": "local-prod",
        "DB_TARGET": "supabase",
        "DATABASE_URL": "postgresql://postgres:secret@db.project.supabase.co:5432/postgres",
    }


class DatabaseLifecycleGuardTestCase(unittest.TestCase):
    def test_local_prod_rejects_localhost(self):
        with self.assertRaisesRegex(ValueError, "loopback"):
            parse_database_target(
                "postgresql://postgres:secret@localhost:5432/postgres", "local-prod"
            )

    def test_local_dev_rejects_supabase(self):
        with self.assertRaisesRegex(ValueError, "Supabase"):
            parse_database_target(
                "postgresql://postgres:secret@db.project.supabase.co:5432/"
                f"{LOCAL_DATABASE}",
                "local-dev",
            )

    def test_supabase_reset_requires_confirmation_phrase(self):
        with self.assertRaisesRegex(ValueError, SUPABASE_RESET_PHRASE):
            validate_environment(environment_for("local-prod"), "local-prod", "reset")

    def test_supabase_migration_requires_confirmation_phrase(self):
        with self.assertRaisesRegex(ValueError, SUPABASE_MIGRATE_PHRASE):
            validate_environment(environment_for("local-prod"), "local-prod", "migrate")

    def test_supabase_confirmation_phrases_are_accepted(self):
        for action, phrase in (
            ("reset", SUPABASE_RESET_PHRASE),
            ("migrate", SUPABASE_MIGRATE_PHRASE),
        ):
            with self.subTest(action=action):
                selected, _, parsed = validate_environment(
                    environment_for("local-prod"), "local-prod", action, phrase
                )
                self.assertEqual("DATABASE_URL", selected)
                self.assertIn("supabase", parsed.hostname)

    def test_wrong_identity_and_db_target_are_rejected(self):
        for key, value in (
            ("APP_ENV", "local-prod"),
            ("ENV_PROFILE", "local-prod"),
            ("DB_TARGET", "supabase"),
        ):
            with self.subTest(key=key):
                environment = environment_for("local-dev")
                environment[key] = value
                with self.assertRaisesRegex(ValueError, key):
                    validate_environment(environment, "local-dev", "verify")

    def test_migration_url_is_preferred_and_validated(self):
        environment = environment_for("local-dev")
        environment["DATABASE_MIGRATION_URL"] = (
            "postgresql://postgres:secret@localhost:5432/" f"{LOCAL_DATABASE}"
        )
        selected, _, parsed = validate_environment(environment, "local-dev", "migrate")
        self.assertEqual("DATABASE_MIGRATION_URL", selected)
        self.assertEqual("localhost", parsed.hostname)


if __name__ == "__main__":
    unittest.main()
