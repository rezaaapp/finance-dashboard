from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.google_connection import get_current_workspace
from app.auth import require_current_user
from app.config import settings
from app.database import get_db_connection
from app.repositories.insight_settings_repository import (
    get_effective_insight_settings,
    upsert_workspace_insight_settings,
)


router = APIRouter(
    prefix="/api/settings",
    tags=["Settings"],
)


class InsightThresholdRequest(BaseModel):
    need_warning_ratio: float
    need_danger_ratio: float
    want_warning_ratio: float
    want_danger_ratio: float
    saving_warning_ratio: float
    saving_good_ratio: float
    uncategorized_warning_count: int
    uncategorized_danger_count: int
    anomaly_warning_multiplier: float
    anomaly_danger_multiplier: float


def _validate_ratio(name: str, value: float) -> float:
    ratio = float(value)

    if ratio < 0 or ratio > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{name} must be between 0 and 1",
        )

    return ratio


def _validate_count(name: str, value: int) -> int:
    count = int(value)

    if count < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{name} must be greater than or equal to 0",
        )

    return count


def _validate_multiplier(name: str, value: float) -> float:
    multiplier = float(value)

    if multiplier < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{name} must be greater than or equal to 1",
        )

    return multiplier


def _validate_payload(payload: InsightThresholdRequest) -> dict:
    validated = {
        "need_warning_ratio": _validate_ratio(
            "need_warning_ratio",
            payload.need_warning_ratio,
        ),
        "need_danger_ratio": _validate_ratio(
            "need_danger_ratio",
            payload.need_danger_ratio,
        ),
        "want_warning_ratio": _validate_ratio(
            "want_warning_ratio",
            payload.want_warning_ratio,
        ),
        "want_danger_ratio": _validate_ratio(
            "want_danger_ratio",
            payload.want_danger_ratio,
        ),
        "saving_warning_ratio": _validate_ratio(
            "saving_warning_ratio",
            payload.saving_warning_ratio,
        ),
        "saving_good_ratio": _validate_ratio(
            "saving_good_ratio",
            payload.saving_good_ratio,
        ),
        "uncategorized_warning_count": _validate_count(
            "uncategorized_warning_count",
            payload.uncategorized_warning_count,
        ),
        "uncategorized_danger_count": _validate_count(
            "uncategorized_danger_count",
            payload.uncategorized_danger_count,
        ),
        "anomaly_warning_multiplier": _validate_multiplier(
            "anomaly_warning_multiplier",
            payload.anomaly_warning_multiplier,
        ),
        "anomaly_danger_multiplier": _validate_multiplier(
            "anomaly_danger_multiplier",
            payload.anomaly_danger_multiplier,
        ),
    }

    ordered_pairs = (
        ("need_warning_ratio", "need_danger_ratio"),
        ("want_warning_ratio", "want_danger_ratio"),
        ("saving_warning_ratio", "saving_good_ratio"),
        ("uncategorized_warning_count", "uncategorized_danger_count"),
        ("anomaly_warning_multiplier", "anomaly_danger_multiplier"),
    )

    for lower_key, upper_key in ordered_pairs:
        if validated[lower_key] > validated[upper_key]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{lower_key} must be less than or equal to {upper_key}",
            )

    return validated


@router.get("/insight-thresholds")
def get_insight_thresholds(
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    with get_db_connection() as connection:
        return get_effective_insight_settings(
            connection,
            workspace_id=str(workspace["id"]),
            default_settings=settings.get_default_insight_settings(),
        )


@router.put("/insight-thresholds")
def update_insight_thresholds(
    payload: InsightThresholdRequest,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    validated_payload = _validate_payload(payload)

    with get_db_connection() as connection:
        with connection.transaction():
            return upsert_workspace_insight_settings(
                connection,
                workspace_id=str(workspace["id"]),
                settings_payload=validated_payload,
            )
