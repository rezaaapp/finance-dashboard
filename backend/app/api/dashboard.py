from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from app.auth import require_auth, require_current_user, require_premium_role
from app.database import get_db_connection
from app.repositories.workspaces import (
    ensure_default_workspace_for_user,
    get_primary_workspace_for_user,
    list_workspace_members,
    normalize_google_sheet_sources,
    upsert_workspace_member,
    update_google_sheet_id_for_user,
)
from app.repositories.users import upsert_invited_member_user
from scripts.data_processing import get_google_sheets_client
from scripts.data_processing import load_and_process_data_from_spreadsheet
from app.services.finance_service import *


def validate_google_sheet_sources(sources):
    client = get_google_sheets_client([
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ])

    for source in sources:
        try:
            client.open_by_key(source["id"])
            load_and_process_data_from_spreadsheet(source["id"])
        except Exception as exc:
            detail = str(exc)

            if "Tidak ada data yang bisa diproses" in detail:
                raise ValueError(
                    f"Google Sheet ID '{source['id']}' kosong atau format datanya tidak sesuai."
                ) from exc

            raise ValueError(
                f"Google Sheet ID '{source['id']}' tidak ditemukan atau tidak bisa diakses."
            ) from exc


def get_active_sheet_context(auth_payload=Depends(require_auth)):
    if auth_payload is True:
        return {
            "sheet_id": None,
            "sheet_ids": [],
            "use_default_sheet": False,
        }

    with get_db_connection() as connection:
        workspace = get_primary_workspace_for_user(
            connection,
            user_id=auth_payload["sub"],
        )

    sources = workspace["google_sheet_sources"] if workspace else []
    sheet_ids = [
        source.get("id")
        for source in sources
        if isinstance(source, dict)
        and source.get("id")
        and source.get("status", "active") == "active"
    ]

    return {
        "sheet_id": workspace["google_sheet_id"] if workspace else None,
        "sheet_ids": sheet_ids,
        "use_default_sheet": False,
    }


router = APIRouter(dependencies=[Depends(require_auth)])


class WorkspaceMemberInvite(BaseModel):
    email: str
    name: str | None = None


def serialize_workspace_member(member):
    return {
        "id": str(member["id"]),
        "workspace_id": str(member["workspace_id"]),
        "user_id": str(member["user_id"]),
        "email": member["email"],
        "name": member["name"],
        "avatar_url": member["avatar_url"],
        "workspace_role": member["role"],
        "role": member["global_role"],
        "created_at": member["created_at"],
        "updated_at": member["updated_at"],
    }


def ensure_can_invite_workspace_member(current_user, workspace):
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if current_user.get("role") == "super_admin" or workspace["role"] == "owner":
        return

    raise HTTPException(
        status_code=403,
        detail="Only workspace owners can invite members.",
    )

@router.get("/summary")
def summary(
    year: int = None,
    month: int = None,
    sheet_context=Depends(get_active_sheet_context),
):
    return get_summary(year, month, **sheet_context)


@router.post("/refresh")
def refresh_data(
    year: int | None = None,
    sheet_context=Depends(get_active_sheet_context),
):
    df_all, df_pengeluaran, df_saving, df_income = refresh_financial_data(
        year,
        **sheet_context,
    )

    return {
        "status": "ok",
        "rows_all": len(df_all),
        "rows_spending": len(df_pengeluaran),
        "rows_saving": len(df_saving),
        "rows_income": len(df_income),
    }

@router.get("/monthly-spending")
def monthly_spending(
    year: int = None,
    month: int = None,
    sheet_context=Depends(get_active_sheet_context),
):
    return get_monthly_spending(year, month, **sheet_context)

@router.get("/monthly-saving")
def monthly_saving(
    year: int = None,
    month: int = None,
    sheet_context=Depends(get_active_sheet_context),
):
    return get_monthly_saving(year, month, **sheet_context)

@router.get("/monthly-income")
def monthly_income(
    year: int = None,
    month: int = None,
    sheet_context=Depends(get_active_sheet_context),
):
    return get_monthly_income(year, month, **sheet_context)

@router.get("/top-spending")
def top_spending(
    year: int  = None, 
    month: int = None,
    sheet_context=Depends(get_active_sheet_context),
):
    return get_top_spending(year, month, **sheet_context)

@router.get("/spending-by-category")
def spending_by_category(
    year: int  = None,
    month: int  = None,
    sheet_context=Depends(get_active_sheet_context),
):
    return get_spending_by_category(year, month, **sheet_context)

@router.get("/category-heatmap")
def category_heatmap(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    return get_category_heatmap(year, month, name, **sheet_context)


@router.get("/transactions")
def transactions(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    return get_transactions(year, month, name, **sheet_context)


@router.get("/category-trends")
def category_trends(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    return get_category_trends(year, month, name, **sheet_context)

@router.get("/source-dana-analytics")
def source_dana_analytics(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    return get_source_dana_analytics(year, month, name, **sheet_context)

@router.get("/monthly-allocation")
def monthly_allocation(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    return get_monthly_allocation(year, month, name, **sheet_context)

@router.get("/spending-per-person")
def spending_per_person(
    year: int | None = None,
    month: int | None = None,
    sheet_context=Depends(get_active_sheet_context),
):
    return get_spending_per_person(year, month, **sheet_context)

@router.get("/personal-analytics")
def personal_analytics(
    year: int | None = None,
    month: int | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    return get_personal_analytics(year, month, **sheet_context)

@router.get("/grocery-vs-food")
def grocery_vs_food(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    return get_grocery_vs_food(year, month, name, **sheet_context)

@router.get("/anomalies")
def anomalies(
    year: int | None = None,
    month: int | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    return get_anomalies(year, month, **sheet_context)

@router.get("/latest-insight")
def latest_insight(
    year: int | None = None,
    month: int | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    return get_latest_insight(year, month, **sheet_context)

@router.get("/available-years")
def available_years(sheet_context=Depends(get_active_sheet_context)):
    return get_available_years(**sheet_context)


@router.get("/budget-forecast")
def budget_forecast(
    year: int | None = None,
    month: int | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    return get_budget_forecast(year, month, **sheet_context)


@router.post("/configuration")
def save_configuration(
    config: dict = Body(...),
    current_user=Depends(require_current_user),
):
    try:
        with get_db_connection() as connection:
            workspace = get_primary_workspace_for_user(
                connection,
                user_id=current_user["sub"],
            )

        return save_configuration_settings(
            config,
            sheet_id=workspace["google_sheet_id"] if workspace else None,
            use_default_sheet=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/workspace/configuration")
def get_workspace_configuration(current_user=Depends(require_current_user)):
    with get_db_connection() as connection:
        with connection.transaction():
            workspace = get_primary_workspace_for_user(
                connection,
                user_id=current_user["sub"],
            )

            if not workspace:
                workspace = ensure_default_workspace_for_user(
                    connection,
                    user_id=current_user["sub"],
                    user_name=current_user.get("name") or "User",
                )

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    return {
        "workspace": {
            "id": str(workspace["id"]),
            "name": workspace["name"],
            "role": workspace["role"],
            "subscription_status": workspace["subscription_status"],
        },
        "configuration": {
            "google_sheet_id": workspace["google_sheet_id"],
            "google_sheet_sources": workspace["google_sheet_sources"] or [],
            "max_google_sheet_sources": settings.MAX_GOOGLE_SHEET_SOURCES,
        },
    }


@router.get("/workspace/members")
def get_workspace_members(current_user=Depends(require_current_user)):
    with get_db_connection() as connection:
        workspace = get_primary_workspace_for_user(
            connection,
            user_id=current_user["sub"],
        )

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        members = list_workspace_members(
            connection,
            workspace_id=str(workspace["id"]),
        )

    return {
        "workspace": {
            "id": str(workspace["id"]),
            "name": workspace["name"],
            "role": workspace["role"],
        },
        "members": [serialize_workspace_member(member) for member in members],
    }


@router.post("/workspace/members")
def invite_workspace_member(
    payload: WorkspaceMemberInvite,
    current_user=Depends(require_current_user),
):
    email = payload.email.strip().lower()

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")

    invited_name = (
        payload.name.strip()
        if payload.name and payload.name.strip()
        else email.split("@")[0]
    )

    with get_db_connection() as connection:
        with connection.transaction():
            workspace = get_primary_workspace_for_user(
                connection,
                user_id=current_user["sub"],
            )
            ensure_can_invite_workspace_member(current_user, workspace)

            invited_user = upsert_invited_member_user(
                connection,
                email=email,
                name=invited_name,
            )
            membership = upsert_workspace_member(
                connection,
                workspace_id=str(workspace["id"]),
                user_id=str(invited_user["id"]),
                role="member",
            )
            members = list_workspace_members(
                connection,
                workspace_id=str(workspace["id"]),
            )

    return {
        "status": "ok",
        "member": {
            "id": str(invited_user["id"]),
            "email": invited_user["email"],
            "name": invited_user["name"],
            "role": invited_user["role"],
            "workspace_role": membership["role"],
        },
        "members": [serialize_workspace_member(member) for member in members],
    }


@router.put("/workspace/configuration")
def update_workspace_configuration(
    config: dict = Body(...),
    current_user=Depends(require_current_user),
):
    if current_user.get("role") == "member":
        raise HTTPException(
            status_code=403,
            detail="Members can view Google Sheets shortcuts but cannot change workspace configuration.",
        )

    google_sheet_id = config.get("google_sheet_id")
    google_sheet_sources = config.get("google_sheet_sources")

    if google_sheet_id is not None:
        google_sheet_id = str(google_sheet_id).strip() or None

    try:
        normalized_sources = normalize_google_sheet_sources(
            google_sheet_sources,
            google_sheet_id,
        )
        validate_google_sheet_sources(normalized_sources)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        with get_db_connection() as connection:
            with connection.transaction():
                workspace = update_google_sheet_id_for_user(
                    connection,
                    user_id=current_user["sub"],
                    google_sheet_id=google_sheet_id,
                    google_sheet_sources=normalized_sources,
                )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "status": "ok",
        "workspace": {
            "id": str(workspace["id"]),
            "name": workspace["name"],
            "role": workspace["role"],
            "subscription_status": workspace["subscription_status"],
        },
        "configuration": {
            "google_sheet_id": workspace["google_sheet_id"],
            "google_sheet_sources": workspace["google_sheet_sources"] or [],
            "max_google_sheet_sources": settings.MAX_GOOGLE_SHEET_SOURCES,
        },
    }
