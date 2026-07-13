from decimal import Decimal

from app.repositories import inquiry_repository
from app.services.transaction_normalizer import normalize_search_text


MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 100
PREVIEW_LIMIT = 10
DEFAULT_DETAIL_LIMIT = 25
MAX_DETAIL_LIMIT = 25


def validate_query(query: str) -> tuple[str, str]:
    raw_query = str(query or "").strip()

    if not raw_query:
        raise ValueError("Query is required")

    if len(raw_query) < MIN_QUERY_LENGTH:
        raise ValueError("Query must be at least 2 characters")

    if len(raw_query) > MAX_QUERY_LENGTH:
        raise ValueError("Query must be 100 characters or fewer")

    return raw_query, normalize_search_text(raw_query)


def validate_period(year=None, month=None):
    if month is not None and not year:
        raise ValueError("Year is required when month is provided")

    if month is not None and (int(month) < 1 or int(month) > 12):
        raise ValueError("Month must be between 1 and 12")


def clamp_detail_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_DETAIL_LIMIT

    return max(1, min(int(limit), MAX_DETAIL_LIMIT))


def normalize_offset(offset: int | None) -> int:
    if offset is None:
        return 0

    return max(0, int(offset))


def _as_float(value) -> float:
    if isinstance(value, Decimal):
        return float(value)

    return float(value or 0)


def _format_idr(value) -> str:
    amount = int(round(_as_float(value)))

    return f"Rp{amount:,}".replace(",", ".")


def _date_to_iso(value) -> str:
    return value.isoformat() if value else ""


def serialize_transaction(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "transaction_date": row["transaction_date"].isoformat()
        if row["transaction_date"] else "",
        "transaction_name": row["title"],
        "category": row["category"] or "-",
        "financial_type": row.get("financial_type") or "uncategorized",
        "amount": _as_float(row["amount"]),
        "source_dana": row["source_fund"] or "-",
        **({"note": row["note"]} if "note" in row else {}),
    }


def build_insights(summary: dict, metrics: dict) -> list[dict]:
    total_transactions = int(summary["total_transactions"] or 0)

    if total_transactions == 0:
        return []

    insights = []
    largest_transaction = metrics.get("largest_transaction")
    top_category = metrics.get("top_category")
    top_source_fund = metrics.get("top_source_fund")

    if largest_transaction:
        insights.append({
            "type": "largest_transaction",
            "title": "Transaksi terbesar",
            "message": (
                "Transaksi terbesar untuk pencarian ini adalah "
                f"{_format_idr(largest_transaction['amount'])}"
                f" dari {largest_transaction['title']}."
            ),
            "value": _as_float(largest_transaction["amount"]),
        })

    if top_category and top_category["category"] != "-":
        insights.append({
            "type": "top_category",
            "title": "Kategori dominan",
            "message": (
                "Sebagian besar transaksi terkait kategori "
                f"{top_category['category']}."
            ),
            "value": top_category["category"],
        })

    if top_source_fund and top_source_fund["source_fund"] != "-":
        insights.append({
            "type": "top_source_fund",
            "title": "Sumber dana utama",
            "message": (
                "Sumber dana yang paling sering muncul adalah "
                f"{top_source_fund['source_fund']}."
            ),
            "value": top_source_fund["source_fund"],
        })

    if summary.get("first_transaction_date") and summary.get("last_transaction_date"):
        insights.append({
            "type": "date_range",
            "title": "Rentang transaksi",
            "message": (
                "Transaksi yang cocok berada pada rentang "
                f"{summary['first_transaction_date'].isoformat()} sampai "
                f"{summary['last_transaction_date'].isoformat()}."
            ),
            "value": {
                "first_transaction_date": _date_to_iso(summary["first_transaction_date"]),
                "last_transaction_date": _date_to_iso(summary["last_transaction_date"]),
            },
        })

    return insights


def search_transactions(connection, *, workspace_id: str, query: str, year=None, month=None) -> dict:
    display_query, normalized_query = validate_query(query)
    validate_period(year, month)
    summary = inquiry_repository.get_keyword_summary(
        connection,
        workspace_id=workspace_id,
        query_normalized=normalized_query,
        year=year,
        month=month,
    )
    preview_rows = inquiry_repository.get_keyword_preview(
        connection,
        workspace_id=workspace_id,
        query_normalized=normalized_query,
        year=year,
        month=month,
    )
    metrics = inquiry_repository.get_keyword_insight_metrics(
        connection,
        workspace_id=workspace_id,
        query_normalized=normalized_query,
        year=year,
        month=month,
    )
    total_transactions = int(summary["total_transactions"] or 0)
    total_amount = _as_float(summary["total_amount"])
    answer = (
        (
            f'Ditemukan {total_transactions} transaksi terkait "{display_query}" '
            f'dengan total {_format_idr(total_amount)}.'
        )
        if total_transactions > 0
        else f'Tidak ditemukan transaksi terkait "{display_query}".'
    )
    insights = build_insights(summary, metrics)

    return {
        "query": display_query,
        "intent": "keyword_search",
        "answer": answer,
        "summary": {
            "total_transactions": total_transactions,
            "total_amount": total_amount,
            "average_amount": _as_float(summary["average_amount"]),
            "min_amount": _as_float(summary["min_amount"]),
            "max_amount": _as_float(summary["max_amount"]),
            "first_transaction_date": _date_to_iso(summary["first_transaction_date"]),
            "last_transaction_date": _date_to_iso(summary["last_transaction_date"]),
        },
        "insights": insights,
        "preview": [serialize_transaction(row) for row in preview_rows[:PREVIEW_LIMIT]],
        "detail_available": total_transactions > PREVIEW_LIMIT,
    }


def get_transaction_detail(
    connection,
    *,
    workspace_id: str,
    query: str,
    year=None,
    month=None,
    limit=None,
    offset=None,
) -> dict:
    display_query, normalized_query = validate_query(query)
    validate_period(year, month)
    detail_limit = clamp_detail_limit(limit)
    detail_offset = normalize_offset(offset)
    detail = inquiry_repository.get_keyword_detail(
        connection,
        workspace_id=workspace_id,
        query_normalized=normalized_query,
        year=year,
        month=month,
        limit=detail_limit,
        offset=detail_offset,
    )
    transactions = [serialize_transaction(row) for row in detail["rows"]]
    total_transactions = int(detail["total"] or 0)

    return {
        "query": display_query,
        "intent": "keyword_search",
        "limit": detail_limit,
        "offset": detail_offset,
        "count": len(transactions),
        "has_more": detail_offset + len(transactions) < total_transactions,
        "total_transactions": total_transactions,
        "items": transactions,
        "transactions": transactions,
    }
