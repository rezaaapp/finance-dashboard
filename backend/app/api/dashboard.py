from fastapi import APIRouter
from app.services.finance_service import *

router = APIRouter()

@router.get("/summary")
def summary(year: int | None = None):
    return get_summary(year)

@router.get("/monthly-spending")
def monthly_spending(year: int | None = None):
    return get_monthly_spending(year)

@router.get("/monthly-saving")
def monthly_saving(year: int | None = None):
    return get_monthly_saving(year)

@router.get("/monthly-income")
def monthly_income(year: int | None = None):
    return get_monthly_income(year)

@router.get("/top-spending")
def top_spending(year: int | None = None):
    return get_top_spending(year)

@router.get("/spending-by-category")
def spending_by_category(year: int | None = None):
    return get_spending_by_category(year)

@router.get("/spending-per-person")
def spending_per_person(year: int | None = None):
    return get_spending_per_person(year)

@router.get("/grocery-vs-food")
def grocery_vs_food(year: int | None = None):
    return get_grocery_vs_food(year)

@router.get("/anomalies")
def anomalies(year: int | None = None):
    return get_anomalies(year)

@router.get("/latest-insight")
def latest_insight(year: int | None = None):
    return get_latest_insight(year)

@router.get("/available-years")
def available_years():
    return get_available_years()