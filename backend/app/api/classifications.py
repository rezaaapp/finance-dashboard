from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.google_connection import get_current_workspace
from app.auth import require_current_user
from app.config import settings
from app.database import get_db_connection
from app.repositories.classification_repository import (
    get_classification_summary,
    get_low_confidence_transactions,
    get_uncategorized_transaction_groups,
    manual_correct_transaction_classification,
    reclassify_transactions_by_pattern,
)
from app.repositories.classification_rule_repository import (
    create_classification_rule,
    delete_classification_rule,
    list_classification_rules,
    update_classification_rule,
    upsert_classification_rule_for_pattern,
)
from app.repositories.sync_job_repository import (
    create_sync_job,
    mark_sync_job_failed,
    mark_sync_job_running,
    mark_sync_job_success,
)
from app.services.classification_service import run_rule_based_classification
from app.services.classification_suggestion_service import build_suggestions


router = APIRouter(
    prefix="/api/classifications",
    tags=["Classifications"],
)

VALID_DIRECTIONS = {"income", "expense", "saving_transfer"}
VALID_FINANCIAL_TYPES = {"income", "need", "want", "saving", "uncategorized"}
VALID_MATCH_TYPES = {"exact", "contains", "regex"}
VALID_SUGGESTION_PATTERN_TYPES = {
    "raw_category_equals",
    "raw_category_contains",
    "title_contains",
    "source_fund_contains",
}
MAX_RULE_PATTERN_LENGTH = 200


class RunClassificationRequest(BaseModel):
    limit: int | None = None


class ManualCorrectionRequest(BaseModel):
    direction: str
    financial_type: str
    category: str
    confidence_score: float | None = 1.0
    explanation: str | None = "Manual correction"


class ClassificationRuleRequest(BaseModel):
    match_type: str = "contains"
    title_pattern: str | None = None
    raw_category_pattern: str | None = None
    direction: str | None = None
    financial_type: str
    category: str
    confidence_score: float | None = 0.95
    explanation: str | None = None
    priority: int | None = 100
    is_active: bool = True


class ApplySuggestionRequest(BaseModel):
    pattern_type: str
    pattern: str
    target_direction: str
    target_financial_type: str
    target_category: str
    confidence_score: float | None = 0.90
    reason: str | None = None
    apply_to_existing: bool = True


def _normalize_text(value) -> str:
    return str(value or "").strip()


def _validate_direction(direction: str) -> str:
    normalized = _normalize_text(direction).casefold()

    if normalized not in VALID_DIRECTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid direction",
        )

    return normalized


def _validate_financial_type(financial_type: str) -> str:
    normalized = _normalize_text(financial_type).casefold()

    if normalized not in VALID_FINANCIAL_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid financial_type",
        )

    return normalized


def _direction_for_financial_type(financial_type: str) -> str:
    if financial_type == "income":
        return "income"

    if financial_type == "saving":
        return "saving_transfer"

    return "expense"


def _validate_direction_financial_type(direction: str, financial_type: str):
    valid_combo = (
        (direction == "income" and financial_type == "income")
        or (direction == "saving_transfer" and financial_type == "saving")
        or (
            direction == "expense"
            and financial_type in {"need", "want", "uncategorized"}
        )
    )

    if not valid_combo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="direction and financial_type are not compatible",
        )


def _validate_confidence_score(confidence_score: float | None, default: float) -> float:
    score = float(default if confidence_score is None else confidence_score)

    if score < 0 or score > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="confidence_score must be between 0 and 1",
        )

    return round(score, 4)


def _validate_rule_payload(payload: ClassificationRuleRequest) -> dict:
    match_type = _normalize_text(payload.match_type).casefold() or "contains"

    if match_type not in VALID_MATCH_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid match_type",
        )

    title_pattern = _normalize_text(payload.title_pattern)
    raw_category_pattern = _normalize_text(payload.raw_category_pattern)

    if not title_pattern and not raw_category_pattern:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="title_pattern or raw_category_pattern is required",
        )

    if (
        len(title_pattern) > MAX_RULE_PATTERN_LENGTH
        or len(raw_category_pattern) > MAX_RULE_PATTERN_LENGTH
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rule patterns must be 200 characters or fewer",
        )

    financial_type = _validate_financial_type(payload.financial_type)
    direction = (
        _validate_direction(payload.direction)
        if payload.direction
        else _direction_for_financial_type(financial_type)
    )
    _validate_direction_financial_type(direction, financial_type)
    category = _normalize_text(payload.category)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="category is required",
        )

    return {
        "match_type": match_type,
        "title_pattern": title_pattern or raw_category_pattern,
        "raw_category_pattern": raw_category_pattern or None,
        "direction": direction,
        "financial_type": financial_type,
        "category": category,
        "confidence_score": _validate_confidence_score(
            payload.confidence_score,
            0.95,
        ),
        "explanation": _normalize_text(payload.explanation) or None,
        "priority": int(payload.priority or 100),
        "is_active": bool(payload.is_active),
    }


def _validate_suggestion_pattern(pattern_type: str, pattern: str) -> tuple[str, str]:
    normalized_pattern_type = _normalize_text(pattern_type).casefold()
    normalized_pattern = _normalize_text(pattern)

    if normalized_pattern_type not in VALID_SUGGESTION_PATTERN_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pattern_type",
        )

    if not normalized_pattern:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pattern is required",
        )

    if len(normalized_pattern) > MAX_RULE_PATTERN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pattern must be 200 characters or fewer",
        )

    return normalized_pattern_type, normalized_pattern


def _rule_match_payload_from_suggestion(pattern_type: str, pattern: str) -> dict:
    if pattern_type == "raw_category_equals":
        return {
            "match_type": "exact",
            "title_pattern": pattern,
            "raw_category_pattern": pattern,
        }

    if pattern_type == "raw_category_contains":
        return {
            "match_type": "contains",
            "title_pattern": pattern,
            "raw_category_pattern": pattern,
        }

    return {
        "match_type": "contains",
        "title_pattern": pattern,
        "raw_category_pattern": None,
    }


def _serialize_low_confidence(row):
    return {
        "transaction_id": str(row["transaction_id"]),
        "title": row["title"],
        "raw_category": row["raw_category"],
        "amount": float(row["amount"] or 0),
        "transaction_date": (
            row["transaction_date"].isoformat()
            if row["transaction_date"]
            else None
        ),
        "direction": row["direction"],
        "financial_type": row["financial_type"],
        "category": row["category"],
        "confidence_score": float(row["confidence_score"] or 0),
        "method": row["method"],
        "explanation": row["explanation"],
    }


def _serialize_rule(rule):
    return {
        "id": str(rule["id"]),
        "workspace_id": str(rule["workspace_id"]),
        "match_type": rule["match_type"],
        "title_pattern": rule["title_pattern"],
        "raw_category_pattern": rule["raw_category_pattern"],
        "direction": rule["direction"],
        "financial_type": rule["financial_type"],
        "category": rule["category"],
        "confidence_score": (
            float(rule["confidence_score"])
            if rule["confidence_score"] is not None
            else None
        ),
        "explanation": rule["explanation"],
        "priority": rule["priority"],
        "is_active": rule["is_active"],
        "created_at": rule["created_at"],
        "updated_at": rule["updated_at"],
    }


@router.get("/uncategorized/groups")
def uncategorized_groups(
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    with get_db_connection() as connection:
        return get_uncategorized_transaction_groups(
            connection,
            workspace_id=str(workspace["id"]),
            limit=limit,
        )


@router.get("/suggestions")
def classification_suggestions(
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    with get_db_connection() as connection:
        groups = get_uncategorized_transaction_groups(
            connection,
            workspace_id=str(workspace["id"]),
            limit=limit,
        )

    return build_suggestions(groups)


@router.post("/suggestions/apply")
def apply_classification_suggestion(
    payload: ApplySuggestionRequest,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    pattern_type, pattern = _validate_suggestion_pattern(
        payload.pattern_type,
        payload.pattern,
    )
    direction = _validate_direction(payload.target_direction)
    financial_type = _validate_financial_type(payload.target_financial_type)
    _validate_direction_financial_type(direction, financial_type)
    category = _normalize_text(payload.target_category)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_category is required",
        )

    confidence_score = _validate_confidence_score(payload.confidence_score, 0.90)
    rule_payload = _rule_match_payload_from_suggestion(pattern_type, pattern)
    explanation = _normalize_text(payload.reason) or f"Applied suggestion: {pattern}"
    workspace_id = str(workspace["id"])

    with get_db_connection() as connection:
        with connection.transaction():
            _rule, rule_created = upsert_classification_rule_for_pattern(
                connection,
                workspace_id=workspace_id,
                direction=direction,
                financial_type=financial_type,
                category=category,
                confidence_score=confidence_score,
                explanation=explanation,
                priority=50,
                is_active=True,
                **rule_payload,
            )
            reclassify_result = {
                "updated_classifications": 0,
                "skipped_manual": 0,
            }

            if payload.apply_to_existing:
                reclassify_result = reclassify_transactions_by_pattern(
                    connection,
                    workspace_id=workspace_id,
                    pattern_type=pattern_type,
                    pattern=pattern,
                    direction=direction,
                    financial_type=financial_type,
                    category=category,
                    confidence_score=confidence_score,
                    explanation=explanation,
                )

    return {
        "rule_created": rule_created,
        **reclassify_result,
    }


@router.post("/run")
def run_classification(
    payload: RunClassificationRequest | None = None,
    limit: int | None = Query(default=None),
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    requested_limit = limit if limit is not None else (payload.limit if payload else None)
    safe_limit = max(
        1,
        min(
            int(requested_limit or settings.AI_MAX_TRANSACTIONS_PER_RUN),
            int(settings.AI_MAX_TRANSACTIONS_PER_RUN or 500),
            500,
        ),
    )
    workspace_id = str(workspace["id"])

    with get_db_connection() as connection:
        with connection.transaction():
            job = create_sync_job(
                connection,
                workspace_id=workspace_id,
                sheet_source_id=None,
                job_type="classification",
            )
            job = mark_sync_job_running(connection, job_id=str(job["id"]))

        try:
            summary = run_rule_based_classification(
                connection,
                workspace_id=workspace_id,
                limit=safe_limit,
            )
            with connection.transaction():
                job = mark_sync_job_success(
                    connection,
                    job_id=str(job["id"]),
                    total_rows=summary["processed"],
                    inserted_rows=summary["classified"],
                    updated_rows=0,
                    skipped_rows=summary["skipped_manual"],
                    failed_rows=summary["errors"],
                )
        except Exception as exc:
            with connection.transaction():
                job = mark_sync_job_failed(
                    connection,
                    job_id=str(job["id"]),
                    error_message="Classification failed",
                )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Classification failed",
            ) from exc

    return {
        "job_id": str(job["id"]),
        "status": job["status"],
        **summary,
    }


@router.get("/summary")
def classification_summary(
    year: int | None = None,
    month: int | None = None,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    with get_db_connection() as connection:
        return get_classification_summary(
            connection,
            workspace_id=str(workspace["id"]),
            year=year,
            month=month,
        )


@router.get("/low-confidence")
def low_confidence_transactions(
    threshold: float = Query(default=0.75, ge=0, le=1),
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    with get_db_connection() as connection:
        rows = get_low_confidence_transactions(
            connection,
            workspace_id=str(workspace["id"]),
            threshold=threshold,
            limit=limit,
        )

    return {
        "threshold": threshold,
        "transactions": [_serialize_low_confidence(row) for row in rows],
    }


@router.put("/transactions/{transaction_id}/manual")
def manual_correction(
    transaction_id: str,
    payload: ManualCorrectionRequest,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    direction = _validate_direction(payload.direction)
    financial_type = _validate_financial_type(payload.financial_type)
    _validate_direction_financial_type(direction, financial_type)
    category = _normalize_text(payload.category)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="category is required",
        )

    with get_db_connection() as connection:
        with connection.transaction():
            result = manual_correct_transaction_classification(
                connection,
                workspace_id=str(workspace["id"]),
                transaction_id=transaction_id,
                direction=direction,
                financial_type=financial_type,
                category=category,
                confidence_score=_validate_confidence_score(
                    payload.confidence_score,
                    1.0,
                ),
                explanation=_normalize_text(payload.explanation)
                or "Manual correction",
            )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return {
        "status": result,
        "transaction_id": transaction_id,
        "method": "manual",
    }


@router.get("/rules")
def get_rules(
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    with get_db_connection() as connection:
        rules = list_classification_rules(
            connection,
            workspace_id=str(workspace["id"]),
        )

    return {"rules": [_serialize_rule(rule) for rule in rules]}


@router.post("/rules", status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: ClassificationRuleRequest,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    rule_payload = _validate_rule_payload(payload)

    with get_db_connection() as connection:
        with connection.transaction():
            rule = create_classification_rule(
                connection,
                workspace_id=str(workspace["id"]),
                **rule_payload,
            )

    return _serialize_rule(rule)


@router.put("/rules/{rule_id}")
def update_rule(
    rule_id: str,
    payload: ClassificationRuleRequest,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    rule_payload = _validate_rule_payload(payload)

    with get_db_connection() as connection:
        with connection.transaction():
            rule = update_classification_rule(
                connection,
                workspace_id=str(workspace["id"]),
                rule_id=rule_id,
                **rule_payload,
            )

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classification rule not found",
        )

    return _serialize_rule(rule)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: str,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    with get_db_connection() as connection:
        with connection.transaction():
            deleted = delete_classification_rule(
                connection,
                workspace_id=str(workspace["id"]),
                rule_id=rule_id,
            )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classification rule not found",
        )
