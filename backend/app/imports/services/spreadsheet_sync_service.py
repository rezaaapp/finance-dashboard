from app.repositories.google_sheet_source_repository import (
    ensure_import_google_sheet_source,
    mark_google_sheet_source_error,
    update_google_sheet_last_synced,
)
from app.repositories.google_oauth_repository import get_active_google_oauth_connection
from app.security.encryption import decrypt_text
from app.services.google_sheets_client import (
    GoogleSheetsClientError,
    append_sheet_values,
)


GOOGLE_SHEETS_WRITE_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
GOOGLE_SHEETS_READ_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"


class SpreadsheetSyncService:
    def sync_import_transactions(
        self,
        connection,
        *,
        workspace: dict,
        current_user: dict,
        approved_transactions: list[dict],
    ) -> dict:
        if not approved_transactions:
            return {
                "status": "skipped",
                "sync_success": 0,
                "sync_failed": 0,
                "source_id": None,
                "error": None,
            }

        oauth_connection = get_active_google_oauth_connection(
            connection,
            workspace_id=str(workspace["id"]),
            user_id=current_user["sub"],
        )

        if not oauth_connection:
            return {
                "status": "failed",
                "sync_success": 0,
                "sync_failed": len(approved_transactions),
                "source_id": None,
                "error": "Google OAuth connection is not active",
            }

        if self.requires_reconnect(oauth_connection.get("scopes") or []):
            return {
                "status": "needs_reconnect",
                "sync_success": 0,
                "sync_failed": len(approved_transactions),
                "source_id": None,
                "error": "needs_reconnect",
            }

        sheet_source = self._resolve_sheet_source(
            connection,
            workspace_id=str(workspace["id"]),
            oauth_connection_id=str(oauth_connection["id"]),
            fallback_sheet_id=str(workspace.get("google_sheet_id") or ""),
        )

        if not sheet_source:
            return {
                "status": "failed",
                "sync_success": 0,
                "sync_failed": len(approved_transactions),
                "source_id": None,
                "error": "Google Sheet source is not configured",
            }

        access_token = decrypt_text(oauth_connection["access_token_encrypted"])
        rows = [
            self._build_sheet_row(transaction, current_user=current_user)
            for transaction in approved_transactions
        ]

        try:
            append_sheet_values(
                access_token=access_token,
                spreadsheet_id=sheet_source["sheet_id"],
                range_name=sheet_source["sheet_name"] or "Sheet1",
                rows=rows,
            )
            update_google_sheet_last_synced(
                connection,
                workspace_id=str(workspace["id"]),
                source_id=str(sheet_source["id"]),
            )
        except GoogleSheetsClientError as exc:
            mark_google_sheet_source_error(
                connection,
                workspace_id=str(workspace["id"]),
                source_id=str(sheet_source["id"]),
            )
            return {
                "status": "failed",
                "sync_success": 0,
                "sync_failed": len(approved_transactions),
                "source_id": str(sheet_source["id"]),
                "error": str(exc),
            }

        return {
            "status": "success",
            "sync_success": len(approved_transactions),
            "sync_failed": 0,
            "source_id": str(sheet_source["id"]),
            "error": None,
        }

    def requires_reconnect(self, scopes: list[str]) -> bool:
        normalized_scopes = {
            str(scope or "").strip()
            for scope in scopes
            if str(scope or "").strip()
        }

        return (
            GOOGLE_SHEETS_READ_SCOPE in normalized_scopes
            and GOOGLE_SHEETS_WRITE_SCOPE not in normalized_scopes
        )

    def _resolve_sheet_source(
        self,
        connection,
        *,
        workspace_id: str,
        oauth_connection_id: str,
        fallback_sheet_id: str,
    ):
        return ensure_import_google_sheet_source(
            connection,
            workspace_id=workspace_id,
            oauth_connection_id=oauth_connection_id,
            sheet_id=fallback_sheet_id,
        )

    def _build_sheet_row(self, transaction: dict, *, current_user: dict) -> list:
        return [
            current_user.get("name") or current_user.get("email") or "User",
            str(transaction.get("datetime", "")),
            str(transaction.get("merchant_normalized", "")),
            str(transaction.get("category", "")),
            transaction.get("amount", 0),
            "Blu",
            str(transaction.get("notes", "")),
        ]
