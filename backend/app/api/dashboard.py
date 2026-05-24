from fastapi import APIRouter
from app.services.finance_service import *

router = APIRouter()

@router.get("/summary")
def summary():
    return get_summary()

@router.get("/monthly-spending")
def monthly_spending():
    return get_monthly_spending()

@router.get("/monthly-saving")
def monthly_saving():
    return get_monthly_saving()

@router.get("/monthly-income")
def monthly_income():
    return get_monthly_income()

@router.get("/top-spending")
def top_spending():
    return get_top_spending()

@router.get("/spending-by-category")
def spending_by_category():
    return get_spending_by_category()

@router.get("/spending-per-person")
def spending_per_person():
    return get_spending_per_person()

@router.get("/grocery-vs-food")
def grocery_vs_food():
    return get_grocery_vs_food()

@router.get("/anomalies")
def anomalies():
    return get_anomalies()

@router.get("/latest-insight")
def latest_insight():
    return get_latest_insight()