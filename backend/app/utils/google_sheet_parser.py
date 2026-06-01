from urllib.parse import urlparse
import re


SPREADSHEET_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,}$")


def _validate_spreadsheet_id(spreadsheet_id: str) -> str:
    normalized_id = (spreadsheet_id or "").strip()

    if not SPREADSHEET_ID_PATTERN.fullmatch(normalized_id):
        raise ValueError("Invalid Google spreadsheet ID")

    return normalized_id


def extract_spreadsheet_id(value: str) -> str:
    raw_value = (value or "").strip()

    if not raw_value:
        raise ValueError("Google spreadsheet URL or ID is required")

    parsed_url = urlparse(raw_value)

    if parsed_url.scheme or parsed_url.netloc:
        path_parts = [part for part in parsed_url.path.split("/") if part]

        if (
            parsed_url.netloc != "docs.google.com"
            or len(path_parts) < 3
            or path_parts[0] != "spreadsheets"
            or path_parts[1] != "d"
        ):
            raise ValueError("Invalid Google spreadsheet URL")

        return _validate_spreadsheet_id(path_parts[2])

    return _validate_spreadsheet_id(raw_value)
