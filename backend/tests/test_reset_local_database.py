import unittest
from urllib.parse import urlparse

from backend.scripts.reset_local_database import (
    EXPECTED_DATABASE,
    build_admin_database_url,
    parse_database_target,
    validate_configured_database_urls,
)


class ResetLocalDatabaseGuardTestCase(unittest.TestCase):
    def test_accepts_only_expected_local_target(self):
        parsed = parse_database_target(
            "postgresql://postgres:secret@127.0.0.1:5432/"
            f"{EXPECTED_DATABASE}"
        )

        self.assertEqual("127.0.0.1", parsed.hostname)
        self.assertEqual(f"/{EXPECTED_DATABASE}", parsed.path)

    def test_accepts_localhost_and_ipv6_loopback(self):
        for host in ("localhost", "[::1]"):
            with self.subTest(host=host):
                parsed = parse_database_target(
                    f"postgresql://postgres:secret@{host}:5432/"
                    f"{EXPECTED_DATABASE}"
                )
                self.assertIn(parsed.hostname, {"localhost", "::1"})

    def test_rejects_remote_and_supabase_hosts(self):
        rejected_hosts = (
            "db.example.com",
            "db.project.supabase.co",
            "192.168.1.20",
        )

        for host in rejected_hosts:
            with self.subTest(host=host):
                with self.assertRaises(ValueError):
                    parse_database_target(
                        f"postgresql://postgres:secret@{host}:5432/"
                        f"{EXPECTED_DATABASE}"
                    )

    def test_rejects_wrong_database_name(self):
        with self.assertRaisesRegex(ValueError, "must be exactly"):
            parse_database_target(
                "postgresql://postgres:secret@127.0.0.1:5432/postgres"
            )

    def test_validates_every_configured_database_url(self):
        environment = {
            "DATABASE_URL": (
                "postgresql://postgres:secret@127.0.0.1:5432/"
                f"{EXPECTED_DATABASE}"
            ),
            "SUPABASE_DATABASE_URL": (
                "postgresql://postgres:secret@db.project.supabase.co:5432/"
                f"{EXPECTED_DATABASE}"
            ),
        }

        with self.assertRaisesRegex(ValueError, "Supabase"):
            validate_configured_database_urls(environment)

    def test_prefers_guarded_migration_url(self):
        environment = {
            "DATABASE_URL": (
                "postgresql://postgres:secret@localhost:5432/"
                f"{EXPECTED_DATABASE}"
            ),
            "DATABASE_MIGRATION_URL": (
                "postgresql://postgres:secret@127.0.0.1:5432/"
                f"{EXPECTED_DATABASE}"
            ),
        }

        selected_key, parsed = validate_configured_database_urls(environment)

        self.assertEqual("DATABASE_MIGRATION_URL", selected_key)
        self.assertEqual("127.0.0.1", parsed.hostname)

    def test_admin_url_keeps_credentials_and_switches_database(self):
        target = urlparse(
            "postgresql://postgres:secret@127.0.0.1:5432/"
            f"{EXPECTED_DATABASE}"
        )

        admin_url = urlparse(build_admin_database_url(target))

        self.assertEqual(target.netloc, admin_url.netloc)
        self.assertEqual("/postgres", admin_url.path)


if __name__ == "__main__":
    unittest.main()
