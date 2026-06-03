import logging
from time import perf_counter

from app.config import settings
from app.repositories.classification_rule_repository import (
    get_active_classification_rules,
)
from app.repositories.classification_repository import (
    bulk_upsert_transaction_classifications,
    get_transactions_by_ids,
    get_unclassified_transactions,
)
from app.services.rule_based_classifier import classify_transaction


logger = logging.getLogger(__name__)


def _duration_ms(start_time: float) -> int:
    return round((perf_counter() - start_time) * 1000)


def _safe_limit(limit: int) -> int:
    requested_limit = int(limit or settings.AI_MAX_TRANSACTIONS_PER_RUN)
    configured_limit = int(settings.AI_MAX_TRANSACTIONS_PER_RUN or 500)

    return max(1, min(requested_limit, configured_limit, 500))


def run_rule_based_classification(
    connection,
    *,
    workspace_id: str,
    limit: int = 500,
) -> dict:
    run_start = perf_counter()
    safe_limit = _safe_limit(limit)
    summary = {
        "processed": 0,
        "classified": 0,
        "low_confidence": 0,
        "skipped_manual": 0,
        "errors": 0,
        "limit": safe_limit,
        "duration_ms": 0,
    }

    logger.info(
        "classification_run_started workspace_id=%s limit=%s",
        workspace_id,
        safe_limit,
    )
    step_start = perf_counter()
    transactions = get_unclassified_transactions(
        connection,
        workspace_id=workspace_id,
        limit=safe_limit,
    )
    logger.info(
        "unclassified_loaded workspace_id=%s count=%s duration_ms=%s",
        workspace_id,
        len(transactions),
        _duration_ms(step_start),
    )

    step_start = perf_counter()
    user_rules = get_active_classification_rules(
        connection,
        workspace_id=workspace_id,
    )
    logger.info(
        "rules_loaded workspace_id=%s count=%s duration_ms=%s",
        workspace_id,
        len(user_rules),
        _duration_ms(step_start),
    )

    step_start = perf_counter()
    classification_rows = []
    for transaction in transactions:
        summary["processed"] += 1

        try:
            classification = classify_transaction(transaction, user_rules=user_rules)
            classification_rows.append({
                "transaction_id": transaction["id"],
                "direction": classification["direction"],
                "financial_type": classification["financial_type"],
                "category": classification["category"],
                "confidence_score": classification["confidence_score"],
                "method": classification["method"],
                "explanation": classification["explanation"],
            })

            if classification["confidence_score"] < settings.AI_CONFIDENCE_THRESHOLD:
                summary["low_confidence"] += 1

        except Exception:
            summary["errors"] += 1

    logger.info(
        "classified_in_memory workspace_id=%s count=%s duration_ms=%s",
        workspace_id,
        len(classification_rows),
        _duration_ms(step_start),
    )

    step_start = perf_counter()
    with connection.transaction():
        upsert_result = bulk_upsert_transaction_classifications(
            connection,
            workspace_id=workspace_id,
            rows=classification_rows,
        )

    summary["classified"] = upsert_result["inserted"] + upsert_result["updated"]
    summary["skipped_manual"] = upsert_result["skipped_manual"]
    logger.info(
        "classifications_upserted workspace_id=%s count=%s duration_ms=%s",
        workspace_id,
        summary["classified"],
        _duration_ms(step_start),
    )

    summary["duration_ms"] = _duration_ms(run_start)
    logger.info(
        "classification_run_finished workspace_id=%s duration_ms=%s",
        workspace_id,
        summary["duration_ms"],
    )

    return summary


def classify_transactions_by_ids(
    connection,
    *,
    workspace_id: str,
    transaction_ids: list[str],
    force_rule_reclassify: bool = False,
) -> dict:
    run_start = perf_counter()
    unique_transaction_ids = list(dict.fromkeys([
        str(transaction_id)
        for transaction_id in transaction_ids or []
        if transaction_id
    ]))
    safe_limit = int(settings.AI_MAX_TRANSACTIONS_PER_RUN or 500)
    unique_transaction_ids = unique_transaction_ids[:max(1, min(safe_limit, 1000))]
    summary = {
        "processed": 0,
        "classified": 0,
        "updated": 0,
        "low_confidence": 0,
        "skipped_manual": 0,
        "errors": 0,
        "duration_ms": 0,
    }

    if not unique_transaction_ids:
        return summary

    logger.info(
        "sync_classification_started workspace_id=%s count=%s",
        workspace_id,
        len(unique_transaction_ids),
    )
    transactions = get_transactions_by_ids(
        connection,
        workspace_id=workspace_id,
        transaction_ids=unique_transaction_ids,
    )
    user_rules = get_active_classification_rules(
        connection,
        workspace_id=workspace_id,
    )
    classification_rows = []

    for transaction in transactions:
        summary["processed"] += 1

        try:
            classification = classify_transaction(transaction, user_rules=user_rules)
            classification_rows.append({
                "transaction_id": transaction["id"],
                "direction": classification["direction"],
                "financial_type": classification["financial_type"],
                "category": classification["category"],
                "confidence_score": classification["confidence_score"],
                "method": classification["method"],
                "explanation": classification["explanation"],
            })

            if classification["confidence_score"] < settings.AI_CONFIDENCE_THRESHOLD:
                summary["low_confidence"] += 1

        except Exception:
            summary["errors"] += 1

    with connection.transaction():
        upsert_result = bulk_upsert_transaction_classifications(
            connection,
            workspace_id=workspace_id,
            rows=classification_rows,
        )

    summary["classified"] = upsert_result["inserted"] + upsert_result["updated"]
    summary["updated"] = upsert_result["updated"]
    summary["skipped_manual"] = upsert_result["skipped_manual"]
    summary["duration_ms"] = _duration_ms(run_start)
    logger.info(
        "sync_classification_finished workspace_id=%s processed=%s duration_ms=%s",
        workspace_id,
        summary["processed"],
        summary["duration_ms"],
    )

    return summary
