import unittest

from app.repositories.google_sheet_source_repository import (
    create_google_sheet_source,
)


class FakeCursor:
    def __init__(self, existing_source):
        self.existing_source = existing_source
        self.executed = []
        self._result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, query, params):
        self.executed.append((query, params))

        if "from google_sheet_sources" in query:
            self._result = self.existing_source
        elif "update google_sheet_sources" in query:
            self._result = {
                **self.existing_source,
                "oauth_connection_id": params[0],
                "sheet_url": params[1],
                "spreadsheet_title": params[2],
                "sheet_name": params[3],
                "status": params[4],
            }

    def fetchone(self):
        return self._result


class FakeConnection:
    def __init__(self, existing_source):
        self.cursor_instance = FakeCursor(existing_source)

    def cursor(self, **_kwargs):
        return self.cursor_instance


class GoogleSheetSourceRepositoryTests(unittest.TestCase):
    def test_existing_active_source_updates_default_sheet_name(self):
        connection = FakeConnection({
            "id": "source-1",
            "workspace_id": "workspace-1",
            "oauth_connection_id": "oauth-old",
            "sheet_id": "spreadsheet-1",
            "sheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1",
            "spreadsheet_title": "Household 2026",
            "sheet_name": None,
            "year": None,
            "status": "active",
            "last_synced_at": None,
            "created_at": None,
            "updated_at": None,
        })

        source = create_google_sheet_source(
            connection,
            workspace_id="workspace-1",
            oauth_connection_id="oauth-new",
            sheet_id="spreadsheet-1",
            sheet_url="https://docs.google.com/spreadsheets/d/spreadsheet-1",
            spreadsheet_title="Household 2026",
            sheet_name="Start 1 Juni",
            year=None,
        )

        self.assertEqual("Start 1 Juni", source["sheet_name"])
        self.assertEqual("active", source["status"])
        self.assertEqual(2, len(connection.cursor_instance.executed))
        update_query, update_params = connection.cursor_instance.executed[1]
        self.assertIn("update google_sheet_sources", update_query)
        self.assertEqual("Start 1 Juni", update_params[3])


if __name__ == "__main__":
    unittest.main()
