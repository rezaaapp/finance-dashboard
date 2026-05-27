from fastapi import APIRouter, Body, Depends, HTTPException
from app.auth import require_auth
from app.services.finance_service import *

router = APIRouter(dependencies=[Depends(require_auth)])

@router.get("/summary")
def summary(
    year: int = None,
    month: int = None 
):
    return get_summary(year, month)


@router.post("/refresh")
def refresh_data(year: int | None = None):
    df_all, df_pengeluaran, df_saving, df_income = refresh_financial_data(year)

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
    month: int = None
):
    return get_monthly_spending(year, month)

@router.get("/monthly-saving")
def monthly_saving(
    year: int = None,
    month: int = None
):
    return get_monthly_saving(year, month)

@router.get("/monthly-income")
def monthly_income(
    year: int = None,
    month: int = None
):
    return get_monthly_income(year, month)

@router.get("/top-spending")
def top_spending(
    year: int  = None, 
    month: int = None):
    return get_top_spending(year, month)

@router.get("/spending-by-category")
def spending_by_category(
    year: int  = None,
    month: int  = None
):
    return get_spending_by_category(year, month)

@router.get("/category-heatmap")
def category_heatmap(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None
):
    return get_category_heatmap(year, month, name)


@router.get("/transactions")
def transactions(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None
):
    return get_transactions(year, month, name)


@router.get("/category-trends")
def category_trends(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None
):
    return get_category_trends(year, month, name)

@router.get("/source-dana-analytics")
def source_dana_analytics(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None
):
    return get_source_dana_analytics(year, month, name)

@router.get("/spending-per-person")
def spending_per_person(
    year: int | None = None,
    month: int | None = None
):
    return get_spending_per_person(year, month)

@router.get("/personal-analytics")
def personal_analytics(
    year: int | None = None,
    month: int | None = None
):
    return get_personal_analytics(year, month)

@router.get("/grocery-vs-food")
def grocery_vs_food(
    year: int | None = None,
    month: int | None = None,
    name: str | None = None
):
    return get_grocery_vs_food(year, month, name)

@router.get("/anomalies")
def anomalies(
    year: int | None = None,
    month: int | None = None
):
    return get_anomalies(year, month)

@router.get("/latest-insight")
def latest_insight(
    year: int | None = None,
    month: int | None = None
):
    return get_latest_insight(year, month)

@router.get("/available-years")
def available_years():
    return get_available_years()


@router.get("/budget-forecast")
def budget_forecast(
    year: int | None = None,
    month: int | None = None
):
    return get_budget_forecast(year, month)


@router.post("/configuration")
def save_configuration(config: dict = Body(...)):
    try:
        return save_configuration_settings(config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
