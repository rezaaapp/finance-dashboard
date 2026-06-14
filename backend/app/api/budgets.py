from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.google_connection import get_current_workspace
from app.auth import require_current_user
from app.database import get_db_connection
from app.repositories.budget_repository import (
    delete_budget_category,
    get_budgets_by_period,
    update_budget_category,
    upsert_budget_category,
)


router = APIRouter(
    prefix="/api/budgets",
    tags=["Budgets"],
)


class BudgetCreateRequest(BaseModel):
    year: int
    month: int
    category: str
    amount: float


class BudgetUpdateRequest(BaseModel):
    category: str
    amount: float


def _validate_period(year: int, month: int) -> tuple[int, int]:
    normalized_year = int(year)
    normalized_month = int(month)

    if normalized_year < 2000 or normalized_year > 2100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="year must be between 2000 and 2100",
        )

    if normalized_month < 1 or normalized_month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="month must be between 1 and 12",
        )

    return normalized_year, normalized_month


def _validate_category(category: str) -> str:
    normalized_category = str(category or "").strip()

    if not normalized_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="category is required",
        )

    return normalized_category


def _validate_amount(amount: float) -> float:
    normalized_amount = float(amount)

    if normalized_amount < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount must be greater than or equal to 0",
        )

    return normalized_amount


@router.get("")
def list_budgets(
    year: int,
    month: int,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    selected_year, selected_month = _validate_period(year, month)

    with get_db_connection() as connection:
        budgets = get_budgets_by_period(
            connection,
            workspace_id=str(workspace["id"]),
            year=selected_year,
            month=selected_month,
        )

    return {
        "year": selected_year,
        "month": selected_month,
        "budgets": budgets,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_or_update_budget(
    payload: BudgetCreateRequest,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    selected_year, selected_month = _validate_period(payload.year, payload.month)
    category = _validate_category(payload.category)
    amount = _validate_amount(payload.amount)

    with get_db_connection() as connection:
        with connection.transaction():
            budget = upsert_budget_category(
                connection,
                workspace_id=str(workspace["id"]),
                year=selected_year,
                month=selected_month,
                category=category,
                amount=amount,
            )

    return {"budget": budget}


@router.put("/{budget_id}")
def update_budget(
    budget_id: str,
    payload: BudgetUpdateRequest,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    category = _validate_category(payload.category)
    amount = _validate_amount(payload.amount)

    with get_db_connection() as connection:
        with connection.transaction():
            budget = update_budget_category(
                connection,
                workspace_id=str(workspace["id"]),
                budget_id=budget_id,
                category=category,
                amount=amount,
            )

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    return {"budget": budget}


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: str,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    with get_db_connection() as connection:
        with connection.transaction():
            deleted_budget = delete_budget_category(
                connection,
                workspace_id=str(workspace["id"]),
                budget_id=budget_id,
            )

    if not deleted_budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )
