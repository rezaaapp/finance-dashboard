from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg import DatabaseError
from pydantic import BaseModel

from app.api.google_connection import get_current_workspace
from app.database import get_db_connection
from app.services import inquiry_service


router = APIRouter(
    prefix="/api/inquiry",
    tags=["Inquiry"],
)


class InquiryRequest(BaseModel):
    query: str
    year: int | None = None
    month: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    period_mode: str | None = None


@router.post("")
def search_inquiry(
    payload: InquiryRequest,
    workspace=Depends(get_current_workspace),
):
    try:
        with get_db_connection() as connection:
            return inquiry_service.search_transactions(
                connection,
                workspace_id=str(workspace["id"]),
                query=payload.query,
                year=payload.year,
                month=payload.month,
                start_date=payload.start_date,
                end_date=payload.end_date,
                period_mode=payload.period_mode,
            )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Inquiry search failed",
        ) from exc


@router.get("/detail")
def inquiry_detail(
    query: str = Query(...),
    year: int | None = None,
    month: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    period_mode: str | None = None,
    limit: int = Query(25, ge=1, le=25),
    offset: int = Query(0, ge=0),
    workspace=Depends(get_current_workspace),
):
    try:
        with get_db_connection() as connection:
            return inquiry_service.get_transaction_detail(
                connection,
                workspace_id=str(workspace["id"]),
                query=query,
                year=year,
                month=month,
                start_date=start_date,
                end_date=end_date,
                period_mode=period_mode,
                limit=limit,
                offset=offset,
            )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Inquiry detail failed",
        ) from exc
