import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.google_connection import get_current_workspace
from app.auth import require_current_user
from app.database import get_db_connection
from app.repositories.google_oauth_repository import (
    get_active_google_oauth_connection,
)
from app.repositories.google_sheet_source_repository import (
    create_google_sheet_source,
    delete_google_sheet_source,
    get_google_sheet_source,
    get_google_sheet_source_by_id,
    get_google_sheet_sources,
    mark_google_sheet_source_error,
    update_google_sheet_last_synced,
)
from app.repositories.sync_job_repository import (
    create_sync_job,
    mark_sync_job_failed,
    mark_sync_job_running,
    mark_sync_job_success,
    update_sync_job_progress,
)
from app.repositories.transaction_repository import batch_upsert_transactions
from app.services.google_sheets_client import (
    GoogleSheetsClientError,
    get_spreadsheet_metadata,
    read_sheet_values,
)
from app.services.google_token_service import (
    GoogleOAuthAuthorizationError,
    GoogleOAuthNeedsReconnectError,
    get_valid_google_access_token,
)
from app.services.google_sheet_tab_filter import (
    get_syncable_tabs,
    is_skipped_tab,
)
from app.services.classification_service import classify_transactions_by_ids
from app.services.sheet_header_validator import validate_sheet_header
from app.services.transaction_normalizer import (
    map_sheet_rows,
    normalize_transaction_row,
    RowNormalizationError,
)
from app.utils.google_sheet_parser import extract_spreadsheet_id


router = APIRouter(
    prefix="/api/data-sources",
    tags=["Data Sources"],
)

logger = logging.getLogger(__name__)


class GoogleSheetTestRequest(BaseModel):
    spreadsheet_url: str
    sheet_name: str | None = None


class GoogleSheetCreateRequest(BaseModel):
    spreadsheet_url: str
    sheet_name: str | None = None
    year: int | None = None


def _serialize_source(source):
    return {
        "source_id": str(source["id"]),
        "sheet_id": source["sheet_id"],
        "spreadsheet_title": source.get("spreadsheet_title"),
        "sheet_name": source["sheet_name"],
        "year": source["year"],
        "status": source["status"],
        "last_synced_at": source["last_synced_at"],
        "created_at": source["created_at"],
    }


def _serialize_sync_response(
    job,
    *,
    processed_tabs: list[str] | None = None,
    skipped_tabs: list[str] | None = None,
    failed_tabs: list[str] | None = None,
    failed_reasons: dict | None = None,
    skipped_reasons: dict | None = None,
    failed_samples: list[dict] | None = None,
    skipped_samples: list[dict] | None = None,
    classification: dict | None = None,
    warnings: list[str] | None = None,
):
    response = {
        "job_id": str(job["id"]),
        "status": job["status"],
        "total_rows": job["total_rows"],
        "inserted_rows": job["inserted_rows"],
        "updated_rows": job["updated_rows"],
        "skipped_rows": job["skipped_rows"],
        "failed_rows": job["failed_rows"],
    }

    if processed_tabs is not None:
        response["processed_tabs"] = processed_tabs

    if skipped_tabs is not None:
        response["skipped_tabs"] = skipped_tabs

    if failed_tabs is not None:
        response["failed_tabs"] = failed_tabs

    response["failed_reasons"] = failed_reasons or {}
    response["skipped_reasons"] = skipped_reasons or {}
    response["failed_samples"] = failed_samples or []
    response["skipped_samples"] = skipped_samples or []
    response["classification"] = classification
    response["warnings"] = warnings or []

    return response


def _record_sync_diagnostic(
    reason_counts: dict,
    samples: list[dict],
    *,
    reason: str,
    sheet_name: str,
    row_number: int | None = None,
    category: str | None = None,
    count: int = 1,
):
    reason_counts[reason] = reason_counts.get(reason, 0) + count

    if len(samples) >= 25:
        return

    sample = {
        "sheet_name": sheet_name,
        "reason": reason,
    }

    if row_number is not None:
        sample["row_number"] = row_number

    if category:
        sample["category"] = str(category).strip()

    samples.append(sample)


def _format_reason_summary(*, failed_reasons: dict, skipped_reasons: dict) -> str | None:
    if not failed_reasons and not skipped_reasons:
        return None

    return (
        "failed_reasons="
        f"{json.dumps(failed_reasons, sort_keys=True)}; "
        "skipped_reasons="
        f"{json.dumps(skipped_reasons, sort_keys=True)}"
    )


def _get_sheet_range(sheet_name: str | None) -> str:
    normalized_sheet_name = (sheet_name or "").strip()

    if not normalized_sheet_name:
        return "A:Z"

    escaped_sheet_name = normalized_sheet_name.replace("'", "''")

    return f"'{escaped_sheet_name}'!A:Z"


def _validate_optional_year(year: int | None) -> int | None:
    if year is None:
        return None

    normalized_year = int(year)

    if normalized_year < 2000 or normalized_year > 2100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="year must be between 2000 and 2100",
        )

    return normalized_year


def _parse_source_id(source_id: str) -> str:
    normalized_source_id = str(source_id or "").strip()

    if not normalized_source_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Sheet source ID is required",
        )

    try:
        return str(UUID(normalized_source_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google Sheet source ID",
        ) from exc


def _get_workspace_source_or_raise(
    connection,
    *,
    workspace_id: str,
    source_id: str,
):
    source = get_google_sheet_source(
        connection,
        workspace_id=workspace_id,
        source_id=source_id,
    )

    if source:
        return source

    foreign_source = get_google_sheet_source_by_id(
        connection,
        source_id=source_id,
    )

    if foreign_source:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Google Sheet source access denied",
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Google Sheet source not found",
    )


def _get_access_context(connection, *, workspace_id: str, user_id: str):
    oauth_connection = get_active_google_oauth_connection(
        connection,
        workspace_id=workspace_id,
        user_id=user_id,
    )

    if not oauth_connection:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account is not connected",
        )

    try:
        access_token = get_valid_google_access_token(connection, oauth_connection)
    except GoogleOAuthNeedsReconnectError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google connection expired. Reconnect Google and try again.",
        ) from exc
    except GoogleOAuthAuthorizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google authorization failed. Reconnect Google and try again.",
        ) from exc

    return oauth_connection, access_token


def _fetch_spreadsheet_metadata(
    *,
    access_token: str,
    spreadsheet_id: str,
    sheet_name: str | None = None,
):
    try:
        metadata = get_spreadsheet_metadata(
            access_token,
            spreadsheet_id,
        )
    except GoogleSheetsClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to access spreadsheet",
        ) from exc

    tabs = metadata.get("sheet_names", [])
    normalized_sheet_name = (sheet_name or "").strip()

    if normalized_sheet_name and normalized_sheet_name not in tabs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sheet tab was not found in spreadsheet",
        )

    return metadata


def _get_tabs_for_source(
    *,
    access_token: str,
    spreadsheet_id: str,
    sheet_name: str | None,
):
    normalized_sheet_name = (sheet_name or "").strip()

    if normalized_sheet_name:
        _fetch_spreadsheet_metadata(
            access_token=access_token,
            spreadsheet_id=spreadsheet_id,
            sheet_name=normalized_sheet_name,
        )

        return [normalized_sheet_name], []

    metadata = _fetch_spreadsheet_metadata(
        access_token=access_token,
        spreadsheet_id=spreadsheet_id,
    )
    tabs = metadata.get("sheet_names", [])
    syncable_tabs = get_syncable_tabs(tabs)
    skipped_tabs = [
        tab
        for tab in tabs
        if is_skipped_tab(tab)
    ]

    return syncable_tabs, skipped_tabs


@router.get("")
def list_data_sources(
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    with get_db_connection() as connection:
        sources = get_google_sheet_sources(
            connection,
            workspace_id=str(workspace["id"]),
        )

    return {
        "sources": [_serialize_source(source) for source in sources],
    }


@router.get("/{source_id}/worksheets")
def list_google_sheet_source_worksheets(
    source_id: str,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    source_id = _parse_source_id(source_id)
    workspace_id = str(workspace["id"])

    with get_db_connection() as connection:
        source = _get_workspace_source_or_raise(
            connection,
            workspace_id=workspace_id,
            source_id=source_id,
        )

        _oauth_connection, access_token = _get_access_context(
            connection,
            workspace_id=workspace_id,
            user_id=current_user["sub"],
        )

    metadata = _fetch_spreadsheet_metadata(
        access_token=access_token,
        spreadsheet_id=source["sheet_id"],
    )

    return {
        "source_id": str(source["id"]),
        "spreadsheet_id": source["sheet_id"],
        "spreadsheet_title": source.get("spreadsheet_title") or metadata.get("title"),
        "worksheets": metadata.get("sheet_names", []),
    }


@router.post("/google-sheet/test")
def test_google_sheet_access(
    payload: GoogleSheetTestRequest,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    try:
        spreadsheet_id = extract_spreadsheet_id(payload.spreadsheet_url)
    except ValueError:
        return {
            "valid": False,
            "message": "Invalid Google spreadsheet URL or ID",
        }

    try:
        with get_db_connection() as connection:
            _oauth_connection, access_token = _get_access_context(
                connection,
                workspace_id=str(workspace["id"]),
                user_id=current_user["sub"],
            )

        metadata = _fetch_spreadsheet_metadata(
            access_token=access_token,
            spreadsheet_id=spreadsheet_id,
            sheet_name=payload.sheet_name,
        )
    except HTTPException:
        return {
            "valid": False,
            "message": "Unable to access spreadsheet",
        }

    return {
        "valid": True,
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_title": metadata["title"],
        "tabs": metadata["sheet_names"],
        "detected_tabs": get_syncable_tabs(metadata["sheet_names"]),
        "skipped_tabs": [
            tab
            for tab in metadata["sheet_names"]
            if is_skipped_tab(tab)
        ],
    }


@router.post("/google-sheet", status_code=status.HTTP_201_CREATED)
def create_google_sheet_data_source(
    payload: GoogleSheetCreateRequest,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    try:
        spreadsheet_id = extract_spreadsheet_id(payload.spreadsheet_url)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google spreadsheet URL or ID",
        ) from exc

    sheet_name = (payload.sheet_name or "").strip() or None
    year = _validate_optional_year(payload.year)

    with get_db_connection() as connection:
        oauth_connection, access_token = _get_access_context(
            connection,
            workspace_id=str(workspace["id"]),
            user_id=current_user["sub"],
        )

        metadata = _fetch_spreadsheet_metadata(
            access_token=access_token,
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
        )
        spreadsheet_title = (metadata.get("title") or "").strip() or None

        with connection.transaction():
            source = create_google_sheet_source(
                connection,
                workspace_id=str(workspace["id"]),
                oauth_connection_id=str(oauth_connection["id"]),
                sheet_id=spreadsheet_id,
                sheet_url=payload.spreadsheet_url,
                spreadsheet_title=spreadsheet_title,
                sheet_name=sheet_name,
                year=year,
                status="active",
            )

    if not source:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Google Sheet source already exists for this workspace",
        )

    return {
        "source_id": str(source["id"]),
        "spreadsheet_id": source["sheet_id"],
        "spreadsheet_title": source.get("spreadsheet_title"),
        "sheet_name": source["sheet_name"],
        "year": source["year"],
        "status": source["status"],
    }


@router.post("/{source_id}/sync")
def sync_google_sheet_source(
    source_id: str,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    source_id = _parse_source_id(source_id)
    workspace_id = str(workspace["id"])

    with get_db_connection() as connection:
        source = _get_workspace_source_or_raise(
            connection,
            workspace_id=workspace_id,
            source_id=source_id,
        )

        with connection.transaction():
            job = create_sync_job(
                connection,
                workspace_id=workspace_id,
                sheet_source_id=source_id,
            )
            job = mark_sync_job_running(
                connection,
                job_id=str(job["id"]),
            )

        try:
            _oauth_connection, access_token = _get_access_context(
                connection,
                workspace_id=workspace_id,
                user_id=current_user["sub"],
            )
            tabs_to_sync, skipped_tabs = _get_tabs_for_source(
                access_token=access_token,
                spreadsheet_id=source["sheet_id"],
                sheet_name=source["sheet_name"],
            )
            processed_tabs = []
            failed_tabs = []
            inserted_rows = 0
            updated_rows = 0
            skipped_rows = 0
            failed_rows = 0
            total_rows = 0
            failed_reasons = {}
            skipped_reasons = {}
            failed_samples = []
            skipped_samples = []
            synced_transaction_ids = []
            classification_summary = None
            sync_warnings = []

            if not tabs_to_sync:
                raise ValueError("Spreadsheet has no syncable tabs")

            for tab_name in tabs_to_sync:
                try:
                    values = read_sheet_values(
                        access_token,
                        source["sheet_id"],
                        _get_sheet_range(tab_name),
                    )
                except GoogleSheetsClientError:
                    failed_tabs.append(tab_name)
                    _record_sync_diagnostic(
                        failed_reasons,
                        failed_samples,
                        reason="google_read_failed",
                        sheet_name=tab_name,
                    )
                    with connection.transaction():
                        job = update_sync_job_progress(
                            connection,
                            job_id=str(job["id"]),
                            total_rows=total_rows,
                            inserted_rows=inserted_rows,
                            updated_rows=updated_rows,
                            skipped_rows=skipped_rows,
                            failed_rows=failed_rows,
                        )
                    continue

                if not values:
                    skipped_tabs.append(tab_name)
                    skipped_rows += 1
                    _record_sync_diagnostic(
                        skipped_reasons,
                        skipped_samples,
                        reason="skipped_tab",
                        sheet_name=tab_name,
                    )
                    with connection.transaction():
                        job = update_sync_job_progress(
                            connection,
                            job_id=str(job["id"]),
                            total_rows=total_rows,
                            inserted_rows=inserted_rows,
                            updated_rows=updated_rows,
                            skipped_rows=skipped_rows,
                            failed_rows=failed_rows,
                        )
                    continue

                header = values[0]
                validation = validate_sheet_header(header)
                data_row_count = max(len(values) - 1, 0)

                if not validation["valid"]:
                    total_rows += data_row_count
                    failed_rows += data_row_count
                    failed_tabs.append(tab_name)
                    _record_sync_diagnostic(
                        failed_reasons,
                        failed_samples,
                        reason="invalid_header",
                        sheet_name=tab_name,
                        count=data_row_count,
                    )
                    with connection.transaction():
                        job = update_sync_job_progress(
                            connection,
                            job_id=str(job["id"]),
                            total_rows=total_rows,
                            inserted_rows=inserted_rows,
                            updated_rows=updated_rows,
                            skipped_rows=skipped_rows,
                            failed_rows=failed_rows,
                        )
                    continue

                mapped_rows = map_sheet_rows(header, values[1:])
                total_rows += len(mapped_rows)
                normalized_rows = []
                tab_skipped_rows = 0
                tab_failed_rows = 0

                for row_number, row in mapped_rows:
                    try:
                        normalized_payload = normalize_transaction_row(
                            row,
                            raw_metadata={
                                "_sheet_name": tab_name,
                                "_row_number": row_number,
                            },
                        )
                        normalized_rows.append(
                            {
                                "workspace_id": workspace_id,
                                "sheet_source_id": source_id,
                                "external_row_key": (
                                    f"tab:{tab_name}:row:{row_number}"
                                ),
                                "row_number": row_number,
                                "payload": normalized_payload,
                            }
                        )
                    except RowNormalizationError as exc:
                        if exc.skipped:
                            skipped_rows += 1
                            tab_skipped_rows += 1
                            _record_sync_diagnostic(
                                skipped_reasons,
                                skipped_samples,
                                reason=exc.reason,
                                sheet_name=tab_name,
                                row_number=row_number,
                                category=exc.category,
                            )
                        else:
                            failed_rows += 1
                            tab_failed_rows += 1
                            _record_sync_diagnostic(
                                failed_reasons,
                                failed_samples,
                                reason=exc.reason,
                                sheet_name=tab_name,
                                row_number=row_number,
                                category=exc.category,
                            )
                    except (KeyError, TypeError, ValueError):
                        failed_rows += 1
                        tab_failed_rows += 1
                        _record_sync_diagnostic(
                            failed_reasons,
                            failed_samples,
                            reason="normalization_failed",
                            sheet_name=tab_name,
                            row_number=row_number,
                        )

                if normalized_rows:
                    try:
                        with connection.transaction():
                            batch_result = batch_upsert_transactions(
                                connection,
                                workspace_id=workspace_id,
                                sheet_source_id=source_id,
                                payloads=normalized_rows,
                            )

                        inserted_rows += batch_result["inserted"]
                        updated_rows += batch_result["updated"]
                        skipped_rows += batch_result["skipped"]
                        failed_rows += batch_result["failed"]
                        if batch_result.get("skipped_duplicates", 0):
                            _record_sync_diagnostic(
                                skipped_reasons,
                                skipped_samples,
                                reason="skipped_duplicate",
                                sheet_name=tab_name,
                                count=batch_result["skipped_duplicates"],
                            )
                        synced_transaction_ids.extend(
                            batch_result.get("inserted_transaction_ids", [])
                        )
                        synced_transaction_ids.extend(
                            batch_result.get("updated_transaction_ids", [])
                        )
                        processed_tabs.append(tab_name)
                    except Exception as exc:
                        diag = getattr(exc, "diag", None)
                        logger.exception(
                            "google_sheet_sync.database_write_failed",
                            extra={
                                "database_diagnostic": {
                                    "sqlstate": getattr(exc, "sqlstate", None),
                                    "exception_class": exc.__class__.__name__,
                                    "constraint": (
                                        getattr(diag, "constraint_name", None)
                                        if diag else None
                                    ),
                                    "table": (
                                        getattr(diag, "table_name", None)
                                        if diag else None
                                    ),
                                    "column": (
                                        getattr(diag, "column_name", None)
                                        if diag else None
                                    ),
                                    "sheet_name": tab_name,
                                    "normalized_row_count": len(normalized_rows),
                                },
                            },
                        )
                        failed_rows += len(normalized_rows)
                        failed_tabs.append(tab_name)
                        _record_sync_diagnostic(
                            failed_reasons,
                            failed_samples,
                            reason="database_write_failed",
                            sheet_name=tab_name,
                            count=len(normalized_rows),
                        )
                elif tab_skipped_rows > 0 and tab_failed_rows == 0:
                    processed_tabs.append(tab_name)

                with connection.transaction():
                    job = update_sync_job_progress(
                        connection,
                        job_id=str(job["id"]),
                        total_rows=total_rows,
                        inserted_rows=inserted_rows,
                        updated_rows=updated_rows,
                        skipped_rows=skipped_rows,
                        failed_rows=failed_rows,
                    )

            try:
                classification_summary = classify_transactions_by_ids(
                    connection,
                    workspace_id=workspace_id,
                    transaction_ids=synced_transaction_ids,
                    force_rule_reclassify=True,
                )
            except Exception:
                classification_summary = {
                    "processed": 0,
                    "classified": 0,
                    "updated": 0,
                    "low_confidence": 0,
                    "skipped_manual": 0,
                    "errors": 1,
                    "duration_ms": 0,
                }
                sync_warnings.append("classification_failed")

            with connection.transaction():
                reason_summary = _format_reason_summary(
                    failed_reasons=failed_reasons,
                    skipped_reasons=skipped_reasons,
                )

                if not processed_tabs or (
                    failed_rows == total_rows and total_rows > 0
                ):
                    mark_google_sheet_source_error(
                        connection,
                        workspace_id=workspace_id,
                        source_id=source_id,
                    )
                    job = mark_sync_job_failed(
                        connection,
                        job_id=str(job["id"]),
                        error_message=reason_summary or "All spreadsheet rows failed to sync",
                        total_rows=total_rows,
                        inserted_rows=inserted_rows,
                        updated_rows=updated_rows,
                        skipped_rows=skipped_rows,
                        failed_rows=failed_rows,
                    )
                else:
                    update_google_sheet_last_synced(
                        connection,
                        workspace_id=workspace_id,
                        source_id=source_id,
                    )
                    job = mark_sync_job_success(
                        connection,
                        job_id=str(job["id"]),
                        total_rows=total_rows,
                        inserted_rows=inserted_rows,
                        updated_rows=updated_rows,
                        skipped_rows=skipped_rows,
                        failed_rows=failed_rows,
                        error_message=reason_summary,
                    )
        except (GoogleSheetsClientError, HTTPException, ValueError):
            with connection.transaction():
                mark_google_sheet_source_error(
                    connection,
                    workspace_id=workspace_id,
                    source_id=source_id,
                )
                job = mark_sync_job_failed(
                    connection,
                    job_id=str(job["id"]),
                    error_message="Google Sheet sync failed",
                )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "job_id": str(job["id"]),
                    "status": "failed",
                    "message": "Google Sheet sync failed",
                },
            )

    return _serialize_sync_response(
        job,
        processed_tabs=processed_tabs,
        skipped_tabs=skipped_tabs,
        failed_tabs=failed_tabs,
        failed_reasons=failed_reasons,
        skipped_reasons=skipped_reasons,
        failed_samples=failed_samples,
        skipped_samples=skipped_samples,
        classification=classification_summary,
        warnings=sync_warnings,
    )


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_google_sheet_data_source(
    source_id: str,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    source_id = _parse_source_id(source_id)

    with get_db_connection() as connection:
        _get_workspace_source_or_raise(
            connection,
            workspace_id=str(workspace["id"]),
            source_id=source_id,
        )

        with connection.transaction():
            deleted_source = delete_google_sheet_source(
                connection,
                workspace_id=str(workspace["id"]),
                source_id=source_id,
            )

    if not deleted_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google Sheet source not found",
        )
