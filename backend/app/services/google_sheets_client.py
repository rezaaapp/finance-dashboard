from urllib.parse import quote

import httpx


GOOGLE_SHEETS_API_BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"


class GoogleSheetsClientError(ValueError):
    pass


def _authorization_headers(access_token: str) -> dict:
    token = (access_token or "").strip()

    if not token:
        raise GoogleSheetsClientError("Google Sheets access token is required")

    return {"Authorization": f"Bearer {token}"}


def _raise_safe_google_error(exc: Exception):
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code

        if status_code == 401:
            raise GoogleSheetsClientError(
                "Google Sheets authorization failed"
            ) from exc

        if status_code == 403:
            raise GoogleSheetsClientError(
                "Google Sheets access is not allowed"
            ) from exc

        if status_code == 404:
            raise GoogleSheetsClientError(
                "Google spreadsheet was not found"
            ) from exc

    raise GoogleSheetsClientError("Google Sheets request failed") from exc


def get_spreadsheet_metadata(access_token: str, spreadsheet_id: str) -> dict:
    try:
        response = httpx.get(
            f"{GOOGLE_SHEETS_API_BASE_URL}/{spreadsheet_id}",
            params={
                "fields": (
                    "properties.title,"
                    "sheets.properties(sheetId,title)"
                ),
            },
            headers=_authorization_headers(access_token),
            timeout=20,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        _raise_safe_google_error(exc)

    payload = response.json()
    sheets = [
        {
            "sheet_id": sheet.get("properties", {}).get("sheetId"),
            "title": sheet.get("properties", {}).get("title"),
        }
        for sheet in payload.get("sheets", [])
        if sheet.get("properties", {}).get("title")
    ]

    return {
        "title": payload.get("properties", {}).get("title", ""),
        "sheet_names": [sheet["title"] for sheet in sheets],
        "sheets": sheets,
    }


def read_sheet_values(
    access_token: str,
    spreadsheet_id: str,
    range_name: str,
) -> list:
    safe_range_name = (range_name or "").strip()

    if not safe_range_name:
        raise GoogleSheetsClientError("Google Sheets range is required")

    encoded_range = quote(safe_range_name, safe="")

    try:
        response = httpx.get(
            f"{GOOGLE_SHEETS_API_BASE_URL}/{spreadsheet_id}/values/{encoded_range}",
            headers=_authorization_headers(access_token),
            timeout=20,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        _raise_safe_google_error(exc)

    return response.json().get("values", [])


def append_sheet_values(
    access_token: str,
    spreadsheet_id: str,
    range_name: str,
    rows: list[list],
):
    safe_range_name = (range_name or "").strip()

    if not safe_range_name:
        raise GoogleSheetsClientError("Google Sheets range is required")

    if not rows:
        return {"updatedRows": 0}

    encoded_range = quote(safe_range_name, safe="")

    try:
        response = httpx.post(
            f"{GOOGLE_SHEETS_API_BASE_URL}/{spreadsheet_id}/values/{encoded_range}:append",
            params={
                "valueInputOption": "USER_ENTERED",
                "insertDataOption": "INSERT_ROWS",
            },
            headers=_authorization_headers(access_token),
            json={
                "values": rows,
            },
            timeout=20,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        _raise_safe_google_error(exc)

    return response.json()


def copy_sheet_row_format_and_validation(
    access_token: str,
    spreadsheet_id: str,
    *,
    sheet_id: int,
    template_row: int,
    destination_start_row: int,
    destination_end_row: int,
    column_count: int = 7,
):
    if template_row < 1:
        raise GoogleSheetsClientError("Template row must be positive")

    if destination_start_row < 1 or destination_end_row < destination_start_row:
        raise GoogleSheetsClientError("Destination row range is invalid")

    source_range = {
        "sheetId": sheet_id,
        "startRowIndex": template_row - 1,
        "endRowIndex": template_row,
        "startColumnIndex": 0,
        "endColumnIndex": column_count,
    }
    destination_range = {
        "sheetId": sheet_id,
        "startRowIndex": destination_start_row - 1,
        "endRowIndex": destination_end_row,
        "startColumnIndex": 0,
        "endColumnIndex": column_count,
    }
    requests = [
        {
            "copyPaste": {
                "source": source_range,
                "destination": destination_range,
                "pasteType": "PASTE_FORMAT",
                "pasteOrientation": "NORMAL",
            },
        },
        {
            "copyPaste": {
                "source": source_range,
                "destination": destination_range,
                "pasteType": "PASTE_DATA_VALIDATION",
                "pasteOrientation": "NORMAL",
            },
        },
    ]

    try:
        response = httpx.post(
            f"{GOOGLE_SHEETS_API_BASE_URL}/{spreadsheet_id}:batchUpdate",
            headers=_authorization_headers(access_token),
            json={"requests": requests},
            timeout=20,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        _raise_safe_google_error(exc)

    return response.json()
