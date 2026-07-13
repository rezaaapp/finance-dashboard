from psycopg.rows import dict_row

from app.repositories.analytics_repository import _classification_financial_type_expr


def _legacy_allocation_type(financial_type: str) -> str:
    if financial_type == "want":
        return "Wants"

    if financial_type == "saving":
        return "Savings"

    return "Needs"


def _fetch_current_classification(
    connection,
    *,
    workspace_id: str,
    transaction_id: str,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                method,
                status
            from transaction_classifications
            where workspace_id = %s
              and transaction_id = %s
              and is_current = true
            order by created_at desc
            limit 1
            """,
            (workspace_id, transaction_id),
        )

        return cursor.fetchone()


def upsert_transaction_classification(
    connection,
    *,
    workspace_id: str,
    transaction_id: str,
    direction: str,
    financial_type: str,
    category: str,
    confidence_score: float,
    method: str,
    explanation: str,
) -> str:
    existing = _fetch_current_classification(
        connection,
        workspace_id=workspace_id,
        transaction_id=transaction_id,
    )

    if existing and (
        existing["method"] == "manual"
        or existing["status"] == "manual_override"
    ):
        return "skipped_manual"

    allocation_type = _legacy_allocation_type(financial_type)

    if existing:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                update transaction_classifications
                set
                    direction = %s,
                    financial_type = %s,
                    category = %s,
                    confidence_score = %s,
                    method = %s,
                    explanation = %s,
                    allocation_type = %s,
                    category_normalized = %s,
                    confidence = %s,
                    reason = %s,
                    model_provider = %s,
                    model_name = %s,
                    status = 'auto',
                    updated_at = now()
                where id = %s
                """,
                (
                    direction,
                    financial_type,
                    category,
                    confidence_score,
                    method,
                    explanation,
                    allocation_type,
                    category,
                    confidence_score,
                    explanation,
                    method,
                    "none",
                    existing["id"],
                ),
            )

        return "updated"

    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into transaction_classifications (
                workspace_id,
                transaction_id,
                direction,
                financial_type,
                category,
                confidence_score,
                method,
                explanation,
                allocation_type,
                category_normalized,
                confidence,
                reason,
                model_provider,
                model_name,
                status,
                is_current
            )
            values (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                'auto', true
            )
            """,
            (
                workspace_id,
                transaction_id,
                direction,
                financial_type,
                category,
                confidence_score,
                method,
                explanation,
                allocation_type,
                category,
                confidence_score,
                explanation,
                method,
                "none",
            ),
        )

    return "inserted"


def _chunk_rows(rows: list[dict], chunk_size: int):
    for index in range(0, len(rows), chunk_size):
        yield rows[index:index + chunk_size]


def _classification_params(workspace_id: str, row: dict):
    allocation_type = _legacy_allocation_type(row["financial_type"])

    return (
        row["direction"],
        row["financial_type"],
        row["category"],
        row["confidence_score"],
        row["method"],
        row["explanation"],
        allocation_type,
        row["category"],
        row["confidence_score"],
        row["explanation"],
        row["method"],
        "none",
        workspace_id,
        row["transaction_id"],
    )


def bulk_upsert_transaction_classifications(
    connection,
    *,
    workspace_id: str,
    rows: list[dict],
    chunk_size: int = 200,
) -> dict:
    if not rows:
        return {
            "inserted": 0,
            "updated": 0,
            "skipped_manual": 0,
        }

    transaction_ids = [row["transaction_id"] for row in rows]

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                transaction_id,
                method,
                status
            from transaction_classifications
            where workspace_id = %s
              and transaction_id = any(%s)
              and is_current = true
            """,
            (workspace_id, transaction_ids),
        )
        existing_by_transaction_id = {
            row["transaction_id"]: row
            for row in cursor.fetchall()
        }

    rows_to_insert = []
    rows_to_update = []
    skipped_manual = 0

    for row in rows:
        existing = existing_by_transaction_id.get(row["transaction_id"])

        if existing and (
            existing["method"] == "manual"
            or existing["status"] == "manual_override"
        ):
            skipped_manual += 1
            continue

        if existing:
            rows_to_update.append({
                **row,
                "classification_id": existing["id"],
            })
        else:
            rows_to_insert.append(row)

    updated_count = 0
    inserted_count = 0

    with connection.cursor() as cursor:
        for chunk in _chunk_rows(rows_to_update, chunk_size):
            cursor.executemany(
                """
                update transaction_classifications
                set
                    direction = %s,
                    financial_type = %s,
                    category = %s,
                    confidence_score = %s,
                    method = %s,
                    explanation = %s,
                    allocation_type = %s,
                    category_normalized = %s,
                    confidence = %s,
                    reason = %s,
                    model_provider = %s,
                    model_name = %s,
                    status = 'auto',
                    updated_at = now()
                where workspace_id = %s
                  and transaction_id = %s
                  and is_current = true
                  and coalesce(method, '') != 'manual'
                  and status != 'manual_override'
                """,
                [
                    _classification_params(workspace_id, row)
                    for row in chunk
                ],
            )
            updated_count += cursor.rowcount or 0

        for chunk in _chunk_rows(rows_to_insert, chunk_size):
            cursor.executemany(
                """
                insert into transaction_classifications (
                    workspace_id,
                    transaction_id,
                    direction,
                    financial_type,
                    category,
                    confidence_score,
                    method,
                    explanation,
                    allocation_type,
                    category_normalized,
                    confidence,
                    reason,
                    model_provider,
                    model_name,
                    status,
                    is_current
                )
                select
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    'auto', true
                where not exists (
                    select 1
                    from transaction_classifications
                    where workspace_id = %s
                      and transaction_id = %s
                      and is_current = true
                )
                """,
                [
                    (
                        workspace_id,
                        row["transaction_id"],
                        row["direction"],
                        row["financial_type"],
                        row["category"],
                        row["confidence_score"],
                        row["method"],
                        row["explanation"],
                        _legacy_allocation_type(row["financial_type"]),
                        row["category"],
                        row["confidence_score"],
                        row["explanation"],
                        row["method"],
                        "none",
                        workspace_id,
                        row["transaction_id"],
                    )
                    for row in chunk
                ],
            )
            inserted_count += cursor.rowcount or 0

    return {
        "inserted": inserted_count,
        "updated": updated_count,
        "skipped_manual": skipped_manual,
    }


def get_uncategorized_transaction_groups(
    connection,
    *,
    workspace_id: str,
    limit: int = 100,
    sample_limit: int = 5,
) -> list[dict]:
    safe_limit = max(1, min(int(limit or 100), 500))
    safe_sample_limit = max(1, min(int(sample_limit or 5), 20))
    financial_type_expr = _classification_financial_type_expr()

    def fetch_samples(cursor, *, group_type: str, pattern: str) -> list[dict]:
        conditions = {
            "raw_category": "lower(trim(coalesce(t.raw_category, ''))) = lower(trim(%s))",
            "title_keyword": "lower(split_part(trim(coalesce(t.title, '')), ' ', 1)) = lower(trim(%s))",
            "source_fund": "lower(trim(coalesce(t.source_fund, ''))) = lower(trim(%s))",
        }
        condition = conditions.get(group_type)

        if not condition:
            return []

        cursor.execute(
            f"""
            select
                t.id,
                t.transaction_date,
                t.title,
                t.raw_category,
                t.source_fund,
                t.user_name,
                t.amount
            from transactions t
            left join transaction_classifications c
              on c.workspace_id = t.workspace_id
             and c.transaction_id = t.id
             and c.is_current = true
            where t.workspace_id = %s
              and t.transaction_date is not null
              and t.transaction_date <= current_date
              and ({financial_type_expr}) = 'uncategorized'
              and {condition}
            order by t.transaction_date desc nulls last, abs(t.amount) desc, t.created_at desc
            limit %s
            """,
            (workspace_id, pattern, safe_sample_limit),
        )

        return [
            {
                "id": str(row["id"]),
                "date": row["transaction_date"].isoformat()
                if row["transaction_date"]
                else "",
                "title": row["title"] or "-",
                "raw_category": row["raw_category"] or "-",
                "source_fund": row["source_fund"] or "-",
                "user": row["user_name"] or "-",
                "amount": float(row["amount"] or 0),
            }
            for row in cursor.fetchall()
        ]

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            f"""
            with base as (
                select
                    t.id,
                    t.raw_category,
                    t.title,
                    t.source_fund,
                    t.amount,
                    {financial_type_expr} as financial_type
                from transactions t
                left join transaction_classifications c
                  on c.workspace_id = t.workspace_id
                 and c.transaction_id = t.id
                 and c.is_current = true
                where t.workspace_id = %s
                  and t.transaction_date is not null
                  and t.transaction_date <= current_date
                  and ({financial_type_expr}) = 'uncategorized'
            ),
            grouped as (
                select
                    'raw_category' as group_type,
                    trim(raw_category) as pattern,
                    count(*) as rows,
                    coalesce(sum(amount), 0) as total_amount
                from base
                where nullif(trim(coalesce(raw_category, '')), '') is not null
                group by 1, 2
                union all
                select
                    'title_keyword' as group_type,
                    lower(split_part(trim(title), ' ', 1)) as pattern,
                    count(*) as rows,
                    coalesce(sum(amount), 0) as total_amount
                from base
                where nullif(trim(coalesce(raw_category, '')), '') is null
                  and nullif(trim(coalesce(title, '')), '') is not null
                group by 1, 2
                union all
                select
                    'source_fund' as group_type,
                    trim(source_fund) as pattern,
                    count(*) as rows,
                    coalesce(sum(amount), 0) as total_amount
                from base
                where nullif(trim(coalesce(source_fund, '')), '') is not null
                group by 1, 2
            )
            select
                group_type,
                pattern,
                rows,
                total_amount,
                least(rows, 3) as sample_count
            from grouped
            where nullif(trim(pattern), '') is not null
            order by rows desc, total_amount desc
            limit %s
            """,
            (workspace_id, safe_limit),
        )

        groups = [
            {
                "group_type": row["group_type"],
                "pattern": row["pattern"],
                "rows": int(row["rows"] or 0),
                "total_amount": float(row["total_amount"] or 0),
                "average_amount": (
                    float(row["total_amount"] or 0) / int(row["rows"] or 1)
                ),
                "sample_count": int(row["sample_count"] or 0),
            }
            for row in cursor.fetchall()
        ]

        for group in groups:
            group["samples"] = fetch_samples(
                cursor,
                group_type=group["group_type"],
                pattern=group["pattern"],
            )

        return groups


def get_matching_classification_rows(
    connection,
    *,
    workspace_id: str,
    pattern_type: str,
    pattern: str,
    limit: int = 1000,
) -> list[dict]:
    safe_limit = max(1, min(int(limit or 1000), 5000))
    normalized_pattern = str(pattern or "").strip()

    if not normalized_pattern:
        return []

    conditions = {
        "raw_category_equals": "lower(trim(coalesce(t.raw_category, ''))) = lower(trim(%s))",
        "raw_category_contains": "lower(coalesce(t.raw_category, '')) like lower(%s)",
        "title_contains": "lower(coalesce(t.title, '')) like lower(%s)",
        "source_fund_contains": "lower(coalesce(t.source_fund, '')) like lower(%s)",
    }
    condition = conditions.get(pattern_type)

    if not condition:
        return []

    match_param = normalized_pattern
    if pattern_type.endswith("_contains"):
        match_param = f"%{normalized_pattern}%"

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            f"""
            select
                t.id as transaction_id,
                c.method,
                c.status,
                coalesce(c.financial_type, 'uncategorized') as financial_type,
                coalesce(c.confidence_score, c.confidence, 0) as confidence_score
            from transactions t
            left join transaction_classifications c
              on c.workspace_id = t.workspace_id
             and c.transaction_id = t.id
             and c.is_current = true
            where t.workspace_id = %s
              and t.transaction_date is not null
              and t.transaction_date <= current_date
              and {condition}
            order by
                case
                    when coalesce(c.financial_type, 'uncategorized') = 'uncategorized'
                    then 0
                    else 1
                end,
                coalesce(c.confidence_score, c.confidence, 0) asc,
                t.transaction_date desc nulls last,
                t.created_at desc
            limit %s
            """,
            (workspace_id, match_param, safe_limit),
        )

        return cursor.fetchall()


def reclassify_transactions_by_pattern(
    connection,
    *,
    workspace_id: str,
    pattern_type: str,
    pattern: str,
    direction: str,
    financial_type: str,
    category: str,
    confidence_score: float,
    explanation: str,
    limit: int = 1000,
) -> dict:
    matching_rows = get_matching_classification_rows(
        connection,
        workspace_id=workspace_id,
        pattern_type=pattern_type,
        pattern=pattern,
        limit=limit,
    )
    classification_rows = []
    skipped_manual = 0

    for row in matching_rows:
        if row["method"] == "manual" or row["status"] == "manual_override":
            skipped_manual += 1
            continue

        financial_type_value = row["financial_type"] or "uncategorized"
        confidence = float(row["confidence_score"] or 0)

        if financial_type_value != "uncategorized" and confidence >= 0.75:
            continue

        classification_rows.append({
            "transaction_id": row["transaction_id"],
            "direction": direction,
            "financial_type": financial_type,
            "category": category,
            "confidence_score": confidence_score,
            "method": "rule",
            "explanation": explanation,
        })

    result = bulk_upsert_transaction_classifications(
        connection,
        workspace_id=workspace_id,
        rows=classification_rows,
    )

    return {
        "updated_classifications": result["inserted"] + result["updated"],
        "skipped_manual": skipped_manual + result["skipped_manual"],
    }


def manual_correct_transaction_classification(
    connection,
    *,
    workspace_id: str,
    transaction_id: str,
    direction: str,
    financial_type: str,
    category: str,
    confidence_score: float = 1.0,
    explanation: str = "Manual correction",
) -> str | None:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select id
            from transactions
            where workspace_id = %s
              and id = %s
            """,
            (workspace_id, transaction_id),
        )
        transaction = cursor.fetchone()

    if not transaction:
        return None

    existing = _fetch_current_classification(
        connection,
        workspace_id=workspace_id,
        transaction_id=transaction_id,
    )
    allocation_type = _legacy_allocation_type(financial_type)

    if existing:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                update transaction_classifications
                set
                    direction = %s,
                    financial_type = %s,
                    category = %s,
                    confidence_score = %s,
                    method = 'manual',
                    explanation = %s,
                    allocation_type = %s,
                    category_normalized = %s,
                    confidence = %s,
                    reason = %s,
                    model_provider = 'manual',
                    model_name = 'none',
                    status = 'manual_override',
                    updated_at = now()
                where id = %s
                """,
                (
                    direction,
                    financial_type,
                    category,
                    confidence_score,
                    explanation,
                    allocation_type,
                    category,
                    confidence_score,
                    explanation,
                    existing["id"],
                ),
            )

        return "updated"

    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into transaction_classifications (
                workspace_id,
                transaction_id,
                direction,
                financial_type,
                category,
                confidence_score,
                method,
                explanation,
                allocation_type,
                category_normalized,
                confidence,
                reason,
                model_provider,
                model_name,
                status,
                is_current
            )
            values (
                %s, %s, %s, %s, %s, %s, 'manual', %s, %s, %s, %s, %s,
                'manual', 'none', 'manual_override', true
            )
            """,
            (
                workspace_id,
                transaction_id,
                direction,
                financial_type,
                category,
                confidence_score,
                explanation,
                allocation_type,
                category,
                confidence_score,
                explanation,
            ),
        )

    return "inserted"


def get_unclassified_transactions(
    connection,
    *,
    workspace_id: str,
    limit: int = 500,
) -> list[dict]:
    safe_limit = max(1, min(int(limit or 500), 500))

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                t.id,
                t.title,
                t.raw_category,
                t.amount,
                t.source_fund,
                t.note,
                t.direction,
                t.raw_payload,
                t.transaction_date,
                t.created_at
            from transactions t
            where t.workspace_id = %s
              and not exists (
                select 1
                from transaction_classifications c
                where c.workspace_id = t.workspace_id
                  and c.transaction_id = t.id
                  and c.is_current = true
              )
            order by t.transaction_date desc nulls last, t.created_at desc
            limit %s
            """,
            (workspace_id, safe_limit),
        )

        return cursor.fetchall()


def get_transactions_by_ids(
    connection,
    *,
    workspace_id: str,
    transaction_ids: list[str],
) -> list[dict]:
    if not transaction_ids:
        return []

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                t.id,
                t.title,
                t.raw_category,
                t.amount,
                t.source_fund,
                t.note,
                t.direction,
                t.raw_payload,
                t.transaction_date,
                t.created_at
            from transactions t
            where t.workspace_id = %s
              and t.id = any(%s)
              and t.transaction_date is not null
              and t.transaction_date <= current_date
            order by t.transaction_date desc nulls last, t.created_at desc
            """,
            (workspace_id, transaction_ids),
        )

        return cursor.fetchall()


def get_classification_summary(
    connection,
    *,
    workspace_id: str,
    year=None,
    month=None,
) -> dict:
    transaction_filters = ["t.workspace_id = %s"]
    params = [workspace_id]

    if year:
        transaction_filters.append("extract(year from t.transaction_date)::int = %s")
        params.append(int(year))

    if month:
        transaction_filters.append("extract(month from t.transaction_date)::int = %s")
        params.append(int(month))

    where_clause = " and ".join(transaction_filters)

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            f"""
            select
                count(c.id) as classified,
                count(t.id) filter (where c.id is null) as unclassified,
                count(c.id) filter (
                    where coalesce(c.confidence_score, c.confidence, 0) < 0.75
                ) as low_confidence,
                count(c.id) filter (
                    where c.method = 'manual'
                       or c.status = 'manual_override'
                ) as manual,
                count(c.id) filter (where c.method = 'rule') as rule,
                count(c.id) filter (where c.method = 'ai') as ai
            from transactions t
            left join transaction_classifications c
              on c.workspace_id = t.workspace_id
             and c.transaction_id = t.id
             and c.is_current = true
            where {where_clause}
            """,
            params,
        )
        row = cursor.fetchone() or {}

    return {
        "classified": int(row.get("classified") or 0),
        "unclassified": int(row.get("unclassified") or 0),
        "low_confidence": int(row.get("low_confidence") or 0),
        "manual": int(row.get("manual") or 0),
        "rule": int(row.get("rule") or 0),
        "ai": int(row.get("ai") or 0),
    }


def get_low_confidence_transactions(
    connection,
    *,
    workspace_id: str,
    threshold: float = 0.75,
    limit: int = 100,
) -> list[dict]:
    safe_limit = max(1, min(int(limit or 100), 500))

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                t.id as transaction_id,
                t.title,
                t.raw_category,
                t.amount,
                t.transaction_date,
                c.direction,
                c.financial_type,
                c.category,
                coalesce(c.confidence_score, c.confidence) as confidence_score,
                c.method,
                c.explanation
            from transaction_classifications c
            join transactions t
              on t.workspace_id = c.workspace_id
             and t.id = c.transaction_id
            where c.workspace_id = %s
              and c.is_current = true
              and coalesce(c.confidence_score, c.confidence, 0) < %s
            order by coalesce(c.confidence_score, c.confidence, 0) asc,
                     t.transaction_date desc nulls last,
                     t.created_at desc
            limit %s
            """,
            (workspace_id, threshold, safe_limit),
        )

        return cursor.fetchall()
