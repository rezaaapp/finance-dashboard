from datetime import datetime

from app.imports.repositories.final_transaction_repository import (
    list_workspace_transaction_source_funds,
    list_workspace_transaction_user_names,
)


class SpreadsheetValueResolver:
    def resolve_allowed_dropdown_value(
        self,
        desired_value,
        allowed_values: list[str],
        *,
        allow_prefix_match: bool = False,
        allow_single_value_fallback: bool = False,
    ) -> dict:
        desired_text = str(desired_value or "")
        normalized_allowed_values = [
            str(value or "").strip()
            for value in allowed_values
            if str(value or "").strip()
        ]

        for allowed_value in normalized_allowed_values:
            if desired_text == allowed_value:
                return {
                    "value": allowed_value,
                    "strategy": "exact",
                    "matched": True,
                }

        for allowed_value in normalized_allowed_values:
            if desired_text.casefold() == allowed_value.casefold():
                return {
                    "value": allowed_value,
                    "strategy": "case_insensitive",
                    "matched": True,
                }

        trimmed_desired = desired_text.strip()
        for allowed_value in normalized_allowed_values:
            if trimmed_desired == allowed_value:
                return {
                    "value": allowed_value,
                    "strategy": "trimmed",
                    "matched": True,
                }

        if allow_prefix_match and trimmed_desired:
            desired_folded = trimmed_desired.casefold()
            prefix_matches = [
                allowed_value
                for allowed_value in normalized_allowed_values
                if (
                    desired_folded.startswith(f"{allowed_value.casefold()} ")
                    or desired_folded.startswith(f"{allowed_value.casefold()}-")
                )
            ]
            if len(prefix_matches) == 1:
                return {
                    "value": prefix_matches[0],
                    "strategy": "safe_prefix",
                    "matched": True,
                }

        if allow_single_value_fallback and len(normalized_allowed_values) == 1:
            return {
                "value": normalized_allowed_values[0],
                "strategy": "single_allowed_value",
                "matched": True,
            }

        return {
            "value": trimmed_desired,
            "strategy": "fallback",
            "matched": False,
        }

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
