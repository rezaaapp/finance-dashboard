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


def get_data_validation_values(
    access_token: str,
    spreadsheet_id: str,
    sheet_name: str,
    column_index_or_letter,
    sample_row: int = 2,
) -> list[str]:
    column_letter = _column_letter(column_index_or_letter)
    escaped_sheet_name = str(sheet_name or "").strip().replace("'", "''")

    if not escaped_sheet_name:
        raise GoogleSheetsClientError("Google Sheets sheet name is required")

    if sample_row < 1:
        raise GoogleSheetsClientError("Google Sheets sample row must be positive")

    range_name = (
        f"'{escaped_sheet_name}'!"
        f"{column_letter}{sample_row}:{column_letter}{sample_row + 98}"
    )

    try:
        response = httpx.get(
            f"{GOOGLE_SHEETS_API_BASE_URL}/{spreadsheet_id}",
            params={
                "includeGridData": "true",
                "ranges": range_name,
            },
            headers=_authorization_headers(access_token),
            timeout=20,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        _raise_safe_google_error(exc)

    allowed_values = []
    range_references = []

    for sheet in response.json().get("sheets", []):
        for grid_data in sheet.get("data", []):
            for row in grid_data.get("rowData", []):
                for cell in row.get("values", []):
                    condition = (
                        cell.get("dataValidation", {})
                        .get("condition", {})
                    )
                    condition_type = condition.get("type")
                    condition_values = condition.get("values", [])

                    if condition_type == "ONE_OF_LIST":
                        allowed_values.extend(
                            str(value.get("userEnteredValue") or "").strip()
                            for value in condition_values
                            if str(value.get("userEnteredValue") or "").strip()
                        )
                    elif condition_type == "ONE_OF_RANGE":
                        range_references.extend(
                            str(value.get("userEnteredValue") or "").strip()
                            for value in condition_values
                            if str(value.get("userEnteredValue") or "").strip()
                        )

    for range_reference in range_references:
        referenced_range = range_reference.removeprefix("=")
        if not referenced_range:
            continue

        referenced_rows = read_sheet_values(
            access_token=access_token,
            spreadsheet_id=spreadsheet_id,
            range_name=referenced_range,
        )
        allowed_values.extend(
            str(value or "").strip()
            for row in referenced_rows
            for value in row
            if str(value or "").strip()
        )

    return list(dict.fromkeys(allowed_values))


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


def _column_letter(column_index_or_letter) -> str:
    if isinstance(column_index_or_letter, int):
        if column_index_or_letter < 0:
            raise GoogleSheetsClientError("Google Sheets column index is invalid")

        column_number = column_index_or_letter + 1
        letters = []
        while column_number:
            column_number, remainder = divmod(column_number - 1, 26)
            letters.append(chr(65 + remainder))

        return "".join(reversed(letters))

    column_letter = str(column_index_or_letter or "").strip().upper()
    if not column_letter.isalpha():
        raise GoogleSheetsClientError("Google Sheets column letter is invalid")

    return column_letter


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


def format_sheet_datetime_column(
    access_token: str,
    spreadsheet_id: str,
    *,
    sheet_id: int,
    destination_start_row: int,
    destination_end_row: int,
    column_index: int = 1,
    pattern: str = "yyyy-mm-dd hh:mm",
):
    if destination_start_row < 1 or destination_end_row < destination_start_row:
        raise GoogleSheetsClientError("Destination row range is invalid")

    if column_index < 0:
        raise GoogleSheetsClientError("Google Sheets column index is invalid")

    requests = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": destination_start_row - 1,
                    "endRowIndex": destination_end_row,
                    "startColumnIndex": column_index,
                    "endColumnIndex": column_index + 1,
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {
                            "type": "DATE_TIME",
                            "pattern": pattern,
                        },
                    },
                },
                "fields": "userEnteredFormat.numberFormat",
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
