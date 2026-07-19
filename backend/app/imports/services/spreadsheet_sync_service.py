import logging
import re

from app.repositories.google_sheet_source_repository import (
    ensure_import_google_sheet_source,
    mark_google_sheet_source_error,
    update_google_sheet_last_synced,
)
from app.repositories.google_oauth_repository import get_active_google_oauth_connection
from app.services.google_sheets_client import (
    GoogleSheetsClientError,
    append_sheet_values,
    copy_sheet_row_format_and_validation,
    format_sheet_datetime_column,
    get_data_validation_values,
    get_spreadsheet_metadata,
    read_sheet_values,
)
from app.services.google_token_service import (
    GoogleOAuthAuthorizationError,
    GoogleOAuthNeedsReconnectError,
    get_valid_google_access_token,
)
from app.imports.services.spreadsheet_value_resolver import SpreadsheetValueResolver


GOOGLE_SHEETS_WRITE_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
GOOGLE_SHEETS_READ_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
logger = logging.getLogger(__name__)


class SpreadsheetSyncService:
    def __init__(self):
        self.value_resolver = SpreadsheetValueResolver()

    def sync_import_transactions(
        self,
        connection,
        *,
        workspace: dict,
        current_user: dict,
        approved_transactions: list[dict],
        target_sheet_source: dict | None = None,
        target_sheet_name: str | None = None,
        user_name: str | None = None,
        source_dana: str | None = None,
        job_id: str | None = None,
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

        sheet_source = target_sheet_source or self._resolve_sheet_source(
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

        try:
            access_token = get_valid_google_access_token(connection, oauth_connection)
        except GoogleOAuthNeedsReconnectError:
            return {
                "status": "needs_reconnect",
                "sync_success": 0,
                "sync_failed": len(approved_transactions),
                "source_id": str(sheet_source["id"]),
                "error": "needs_reconnect",
            }
        except GoogleOAuthAuthorizationError as exc:
            return {
                "status": "failed",
                "sync_success": 0,
                "sync_failed": len(approved_transactions),
                "source_id": str(sheet_source["id"]),
                "error": str(exc),
            }
        resolved_user_name = user_name or self.value_resolver.resolve_user_name_for_append(
            connection,
            workspace_id=str(workspace["id"]),
            current_user=current_user,
        )
        resolved_source_dana = str(source_dana or "").strip()
        if not resolved_source_dana:
            raise ValueError("source_dana is required for import spreadsheet sync")
        validation_warnings = []
        resolved_user_name = self._resolve_validated_dropdown_value(
            access_token=access_token,
            spreadsheet_id=sheet_source["sheet_id"],
            sheet_name=target_sheet_name or sheet_source["sheet_name"] or "Sheet1",
            column="A",
            column_name="Nama",
            desired_value=resolved_user_name,
            job_id=job_id,
            allow_prefix_match=True,
            allow_single_value_fallback=True,
            warnings=validation_warnings,
        )
        resolved_source_dana = self._resolve_validated_dropdown_value(
            access_token=access_token,
            spreadsheet_id=sheet_source["sheet_id"],
            sheet_name=target_sheet_name or sheet_source["sheet_name"] or "Sheet1",
            column="F",
            column_name="Source Dana",
            desired_value=resolved_source_dana,
            job_id=job_id,
            warnings=validation_warnings,
        )
        rows = [
            self._build_sheet_row(
                transaction,
                current_user=current_user,
                user_name=resolved_user_name,
                source_dana=resolved_source_dana,
            )
            for transaction in approved_transactions
        ]

        target_sheet_name = target_sheet_name or sheet_source["sheet_name"] or "Sheet1"
        sync_warnings = list(validation_warnings)

        try:
            append_result = append_sheet_values(
                access_token=access_token,
                spreadsheet_id=sheet_source["sheet_id"],
                range_name=target_sheet_name,
                rows=rows,
            )
            try:
                formatting_result = self._format_appended_rows(
                    access_token=access_token,
                    spreadsheet_id=sheet_source["sheet_id"],
                    sheet_name=target_sheet_name,
                    append_result=append_result,
                    row_count=len(rows),
                )
                logger.info(
                    "smart_import.spreadsheet_formatting.completed",
                    extra={
                        "smart_import": {
                            "sheet_name": target_sheet_name,
                            "template_row": formatting_result.get("template_row"),
                            "appended_row_range": formatting_result["appended_row_range"],
                            "row_count": len(rows),
                        },
                    },
                )
                if formatting_result.get("warning"):
                    sync_warnings.append(formatting_result["warning"])
            except GoogleSheetsClientError as formatting_error:
                formatting_warning = str(formatting_error)
                sync_warnings.append(formatting_warning)
                logger.warning(
                    "smart_import.spreadsheet_formatting.failed",
                    extra={
                        "smart_import": {
                            "sheet_name": target_sheet_name,
                            "row_count": len(rows),
                            "reason": formatting_warning,
                        },
                    },
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
            "error": " ".join(dict.fromkeys(sync_warnings)) or None,
            "formatting_status": "warning" if sync_warnings else "success",
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

    def _build_sheet_row(
        self,
        transaction: dict,
        *,
        current_user: dict,
        user_name: str | None = None,
        source_dana: str | None = None,
    ) -> list:
        return [
            str(
                user_name
                or transaction.get("user_name")
                or current_user.get("name")
                or current_user.get("display_name")
                or current_user.get("email")
                or "User"
            ),
            self.value_resolver.format_datetime_for_append(transaction.get("datetime", "")),
            str(
                transaction.get("merchant_display")
                or transaction.get("merchant_normalized", "")
            ),
            str(transaction.get("category", "")),
            transaction.get("amount", 0),
            str(source_dana or transaction.get("source_dana") or transaction.get("source_fund") or ""),
            str(transaction.get("notes", "")),
        ]

    def _resolve_validated_dropdown_value(
        self,
        *,
        access_token: str,
        spreadsheet_id: str,
        sheet_name: str,
        column: str,
        column_name: str,
        desired_value: str,
        job_id: str | None,
        warnings: list[str],
        allow_prefix_match: bool = False,
        allow_single_value_fallback: bool = False,
    ) -> str:
        try:
            allowed_values = get_data_validation_values(
                access_token=access_token,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                column_index_or_letter=column,
                sample_row=2,
            )
        except GoogleSheetsClientError as exc:
            warning_message = (
                "Tidak bisa membaca dropdown Google Sheets untuk Nama/Source Dana."
            )
            warnings.append(warning_message)
            logger.warning(
                "smart_import.sheet_validation.warning",
                extra={
                    "smart_import": {
                        "job_id": job_id,
                        "column": column_name,
                        "reason": str(exc),
                    },
                },
            )
            return desired_value

        logger.info(
            "smart_import.sheet_validation.loaded",
            extra={
                "smart_import": {
                    "job_id": job_id,
                    "sheet_name": sheet_name,
                    "column": column_name,
                    "allowed_count": len(allowed_values),
                },
            },
        )

        if not allowed_values:
            warning_message = (
                "Tidak bisa membaca dropdown Google Sheets untuk Nama/Source Dana."
            )
            warnings.append(warning_message)
            logger.warning(
                "smart_import.sheet_validation.warning",
                extra={
                    "smart_import": {
                        "job_id": job_id,
                        "column": column_name,
                        "reason": "No explicit or resolvable validation values were found",
                    },
                },
            )
            return desired_value

        resolution = self.value_resolver.resolve_allowed_dropdown_value(
            desired_value,
            allowed_values,
            allow_prefix_match=allow_prefix_match,
            allow_single_value_fallback=allow_single_value_fallback,
        )
        event_fields = {
            "job_id": job_id,
            "column": column_name,
            "desired_value": desired_value,
            "resolved_value": resolution["value"],
            "strategy": resolution["strategy"],
        }

        if resolution["matched"]:
            logger.info(
                "smart_import.sheet_validation.resolved",
                extra={"smart_import": event_fields},
            )
        else:
            logger.warning(
                "smart_import.sheet_validation.warning",
                extra={
                    "smart_import": {
                        **event_fields,
                        "reason": "Desired value did not match the allowed dropdown values",
                    },
                },
            )

        return resolution["value"]

    def _format_appended_rows(
        self,
        *,
        access_token: str,
        spreadsheet_id: str,
        sheet_name: str,
        append_result: dict,
        row_count: int,
    ) -> dict:
        sheet_id = self._resolve_sheet_id(
            access_token=access_token,
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
        )
        destination_start_row, destination_end_row = self._parse_appended_row_range(
            append_result,
            expected_row_count=row_count,
        )
        formatting_warnings = []

        try:
            template_row = self._resolve_template_row(
                access_token=access_token,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
            )
            copy_sheet_row_format_and_validation(
                access_token=access_token,
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                template_row=template_row,
                destination_start_row=destination_start_row,
                destination_end_row=destination_end_row,
                column_count=7,
            )
        except GoogleSheetsClientError as exc:
            template_row = None
            formatting_warnings.append(str(exc))

        format_sheet_datetime_column(
            access_token=access_token,
            spreadsheet_id=spreadsheet_id,
            sheet_id=sheet_id,
            destination_start_row=destination_start_row,
            destination_end_row=destination_end_row,
            column_index=1,
            pattern="mm/dd/yyyy",
        )

        result = {
            "template_row": template_row,
            "appended_row_range": f"{destination_start_row}:{destination_end_row}",
        }
        if formatting_warnings:
            result["warning"] = " ".join(dict.fromkeys(formatting_warnings))

        return result

    def _resolve_sheet_id(
        self,
        *,
        access_token: str,
        spreadsheet_id: str,
        sheet_name: str,
    ) -> int:
        metadata = get_spreadsheet_metadata(
            access_token=access_token,
            spreadsheet_id=spreadsheet_id,
        )

        for sheet in metadata.get("sheets", []):
            if sheet.get("title") == sheet_name and sheet.get("sheet_id") is not None:
                return int(sheet["sheet_id"])

        raise GoogleSheetsClientError("Target sheet metadata was not found")

    def _resolve_template_row(
        self,
        *,
        access_token: str,
        spreadsheet_id: str,
        sheet_name: str,
    ) -> int:
        escaped_sheet_name = str(sheet_name).replace("'", "''")
        template_values = read_sheet_values(
            access_token=access_token,
            spreadsheet_id=spreadsheet_id,
            range_name=f"'{escaped_sheet_name}'!A2:G100",
        )

        for offset, row in enumerate(template_values):
            if any(str(value or "").strip() for value in row):
                return offset + 2

        raise GoogleSheetsClientError("Spreadsheet template row was not found")

    def _parse_appended_row_range(
        self,
        append_result: dict,
        *,
        expected_row_count: int,
    ) -> tuple[int, int]:
        updated_range = str(
            append_result.get("updates", {}).get("updatedRange")
            or append_result.get("updatedRange")
            or ""
        )
        matched_range = re.search(
            r"![A-Z]+(?P<start>\d+):[A-Z]+(?P<end>\d+)$",
            updated_range,
            flags=re.IGNORECASE,
        )

        if not matched_range:
            raise GoogleSheetsClientError("Appended spreadsheet row range was not returned")

        start_row = int(matched_range.group("start"))
        end_row = int(matched_range.group("end"))

        if end_row - start_row + 1 != expected_row_count:
            raise GoogleSheetsClientError("Appended spreadsheet row count did not match")

        return start_row, end_row
