from fastapi import APIRouter, Body, Depends, HTTPException
from psycopg.errors import UndefinedTable
from pydantic import BaseModel
from app.auth import require_auth, require_current_user, require_premium_role
from app.config import settings
from app.database import get_db_connection
from app.repositories.insight_settings_repository import get_effective_insight_settings
from app.repositories.workspaces import (
    ensure_default_workspace_for_user,
    get_primary_workspace_for_user,
    list_workspace_members,
    normalize_google_sheet_sources,
    upsert_workspace_member,
    update_google_sheet_id_for_user,
)
from app.repositories.users import upsert_invited_member_user
from app.repositories import analytics_repository as analytics
from app.services.financial_insight_service import generate_rule_based_insights
from scripts.data_processing import load_and_process_data_from_spreadsheet
from app.services.finance_service import *


def validate_google_sheet_sources(sources):
    for source in sources:
        try:
            load_and_process_data_from_spreadsheet(source["id"])
        except Exception as exc:
            detail = str(exc)

            if "429" in detail or "Quota exceeded" in detail:
                raise ValueError(
                    "Kuota baca Google Sheets sedang habis. Tunggu sekitar 1 menit, lalu coba lagi."
                ) from exc

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
            "workspace_id": None,
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
        "workspace_id": str(workspace["id"]) if workspace else None,
        "sheet_id": workspace["google_sheet_id"] if workspace else None,
        "sheet_ids": sheet_ids,
        "use_default_sheet": False,
    }


def get_transaction_available_years(auth_payload=Depends(require_auth)):
    if auth_payload is True:
        return []

    with get_db_connection() as connection:
        workspace = get_primary_workspace_for_user(
            connection,
            user_id=auth_payload["sub"],
        )

        if not workspace:
            return []

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select distinct
                        extract(year from transaction_date)::int as year
                    from transactions
                    where workspace_id = %s
                      and transaction_date is not null
                      and transaction_date <= current_date
                    order by year desc
                    """,
                    (str(workspace["id"]),),
                )

                return [
                    row[0]
                    for row in cursor.fetchall()
                    if row[0] is not None
                ]
        except UndefinedTable:
            return []


def legacy_sheet_context(sheet_context: dict):
    return {
        key: value
        for key, value in sheet_context.items()
        if key != "workspace_id"
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
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_summary(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
            )

    return get_summary(year, month, **legacy_sheet_context(sheet_context))


@router.post("/refresh")
def refresh_data(
    year: int | None = None,
    sheet_context=Depends(get_active_sheet_context),
):
    df_all, df_pengeluaran, df_saving, df_income = refresh_financial_data(
        year,
        **legacy_sheet_context(sheet_context),
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
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_monthly_totals(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
                direction="expense",
            )

    return get_monthly_spending(year, month, **legacy_sheet_context(sheet_context))

@router.get("/monthly-saving")
def monthly_saving(
    year: int = None,
    month: int = None,
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_monthly_totals(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
                direction="saving_transfer",
            )

    return get_monthly_saving(year, month, **legacy_sheet_context(sheet_context))

@router.get("/monthly-income")
def monthly_income(
    year: int = None,
    month: int = None,
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_monthly_totals(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
                direction="income",
            )

    return get_monthly_income(year, month, **legacy_sheet_context(sheet_context))

@router.get("/top-spending")
def top_spending(
    year: int  = None, 
    month: int = None,
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_top_spending(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
            )

    return get_top_spending(year, month, **legacy_sheet_context(sheet_context))

@router.get("/spending-by-category")
def spending_by_category(
    year: int  = None,
    month: int  = None,
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_spending_by_category(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
            )

    return get_spending_by_category(year, month, **legacy_sheet_context(sheet_context))


@router.get("/financial-types")
def financial_types(
    year: int | None = None,
    month: int | None = None,
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_financial_type_breakdown(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
            )

    return [
        {"type": "need", "amount": 0, "count": 0},
        {"type": "want", "amount": 0, "count": 0},
        {"type": "saving", "amount": 0, "count": 0},
        {"type": "income", "amount": 0, "count": 0},
        {"type": "uncategorized", "amount": 0, "count": 0},
    ]


@router.get("/monthly-financial-types")
def monthly_financial_types(
    year: int,
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_monthly_financial_type_breakdown(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
            )

    return []


@router.get("/category-heatmap")
def category_heatmap(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_category_heatmap(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
                name=name,
            )

    return get_category_heatmap(year, month, name, **legacy_sheet_context(sheet_context))


@router.get("/transactions")
def transactions(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_transactions(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
                name=name,
            )

    return get_transactions(year, month, name, **legacy_sheet_context(sheet_context))


@router.get("/category-trends")
def category_trends(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_category_trends(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
                name=name,
            )

    return get_category_trends(year, month, name, **legacy_sheet_context(sheet_context))

@router.get("/source-dana-analytics")
def source_dana_analytics(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_source_dana_analytics(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
                name=name,
            )

    return get_source_dana_analytics(year, month, name, **legacy_sheet_context(sheet_context))

@router.get("/monthly-allocation")
def monthly_allocation(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_monthly_allocation(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
                name=name,
            )

    return get_monthly_allocation(year, month, name, **legacy_sheet_context(sheet_context))

@router.get("/spending-per-person")
def spending_per_person(
    year: int | None = None,
    month: int | None = None,
    sheet_context=Depends(get_active_sheet_context),
):
    return get_spending_per_person(year, month, **legacy_sheet_context(sheet_context))

@router.get("/personal-analytics")
def personal_analytics(
    year: int | None = None,
    month: int | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_personal_analytics(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
            )

    return get_personal_analytics(year, month, **legacy_sheet_context(sheet_context))

@router.get("/grocery-vs-food")
def grocery_vs_food(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_grocery_vs_food(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
                name=name,
            )

    return get_grocery_vs_food(year, month, name, **legacy_sheet_context(sheet_context))

@router.get("/anomalies")
def anomalies(
    year: int | None = None,
    month: int | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            insight_settings = get_effective_insight_settings(
                connection,
                workspace_id=sheet_context["workspace_id"],
                default_settings=settings.get_default_insight_settings(),
            )
            return analytics.get_anomalies(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
                insight_settings=insight_settings,
            )

    return get_anomalies(year, month, **legacy_sheet_context(sheet_context))

@router.get("/latest-insight")
def latest_insight(
    year: int | None = None,
    month: int | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_latest_insight(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
            )

    return get_latest_insight(year, month, **legacy_sheet_context(sheet_context))


@router.get("/rule-based-insights")
def rule_based_insights(
    year: int | None = None,
    month: int | None = None,
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return generate_rule_based_insights(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
            )

    return {
        "period": str(year or "all"),
        "summary": "Not enough data to generate insights yet.",
        "highlights": [],
        "metrics": {
            "need_ratio": 0,
            "want_ratio": 0,
            "saving_rate": 0,
            "uncategorized_count": 0,
            "settings_source": "default",
        },
    }


@router.get("/available-years")
def available_years(years=Depends(get_transaction_available_years)):
    return years


@router.get("/budget-forecast")
def budget_forecast(
    year: int | None = None,
    month: int | None = None,
    premium_user=Depends(require_premium_role),
    sheet_context=Depends(get_active_sheet_context),
):
    if sheet_context.get("workspace_id"):
        with get_db_connection() as connection:
            return analytics.get_budget_forecast(
                connection,
                workspace_id=sheet_context["workspace_id"],
                year=year,
                month=month,
            )

    return get_budget_forecast(year, month, **legacy_sheet_context(sheet_context))


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
