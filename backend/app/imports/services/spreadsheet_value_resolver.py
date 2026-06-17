from datetime import datetime

from app.imports.repositories.final_transaction_repository import (
    list_workspace_transaction_source_funds,
    list_workspace_transaction_user_names,
)


class SpreadsheetValueResolver:
    def resolve_user_name_for_append(
        self,
        connection,
        *,
        workspace_id: str,
        current_user: dict,
    ) -> str:
        existing_names = list_workspace_transaction_user_names(
            connection,
            workspace_id=workspace_id,
        )
        user_candidates = [
            current_user.get("name"),
            current_user.get("display_name"),
            current_user.get("email"),
        ]

        for candidate in user_candidates:
            matched_name = self._find_case_insensitive_match(
                existing_names,
                str(candidate or "").strip(),
            )
            if matched_name:
                return matched_name

        if len(existing_names) == 1:
            return existing_names[0]

        for candidate in user_candidates:
            normalized_candidate = str(candidate or "").strip()
            if normalized_candidate:
                return normalized_candidate

        return "User"

    def resolve_source_dana_for_append(
        self,
        connection,
        *,
        workspace_id: str,
        provider: str = "Blu",
    ) -> str:
        existing_sources = list_workspace_transaction_source_funds(
            connection,
            workspace_id=workspace_id,
        )
        matched_source = self._find_case_insensitive_match(
            existing_sources,
            provider,
        )

        return matched_source or provider

    def format_datetime_for_append(self, datetime_value) -> str:
        parsed_datetime = self._parse_datetime(datetime_value)

        if parsed_datetime:
            return parsed_datetime.strftime("%m/%d/%Y %H:%M")

        return str(datetime_value or "").strip()

    def _parse_datetime(self, value):
        if not value:
            return None

        if isinstance(value, datetime):
            return value.replace(tzinfo=None)

        raw_value = str(value or "").strip()
        if not raw_value:
            return None

        for date_format in (
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
        ):
            try:
                return datetime.strptime(raw_value, date_format)
            except ValueError:
                pass

        try:
            normalized_value = raw_value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized_value).replace(tzinfo=None)
        except ValueError:
            return None

    def _find_case_insensitive_match(self, values: list[str], target: str) -> str | None:
        normalized_target = str(target or "").strip().casefold()

        if not normalized_target:
            return None

        for value in values:
            normalized_value = str(value or "").strip()
            if normalized_value.casefold() == normalized_target:
                return normalized_value

        return None
