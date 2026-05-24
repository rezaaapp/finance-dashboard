from fastapi import APIRouter
from app.services.finance_service import (
    get_monthly_spending
)

router = APIRouter()

@router.get("/monthly-spending")
def monthly_spending():
    return get_monthly_spending()