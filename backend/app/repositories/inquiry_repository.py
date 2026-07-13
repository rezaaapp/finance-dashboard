from psycopg.rows import dict_row

from app.repositories.analytics_repository import (
    _classification_category_expr,
    _classification_financial_type_expr,
)


def _escape_like(value: str) -> str:
    return (
        value
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _period_filter(year=None, month=None):
    clauses = []
    params = []

    if year and month:
        clauses.append("t.transaction_date >= make_date(%s, %s, 1)")
        clauses.append("t.transaction_date < make_date(%s, %s, 1) + interval '1 month'")
        params.extend([year, month, year, month])
    elif year:
        clauses.append("t.transaction_date >= make_date(%s, 1, 1)")
        clauses.append("t.transaction_date < make_date(%s, 1, 1) + interval '1 year'")
        params.extend([year, year])

    return clauses, params


def _search_params(*, workspace_id: str, query_normalized: str, year=None, month=None):
    clauses = [
        "t.workspace_id = %s",
        "t.search_text_normalized like %s escape '\\'",
    ]
    params = [
        workspace_id,
        f"%{_escape_like(query_normalized)}%",
    ]
    period_clauses, period_params = _period_filter(year, month)

    return " and ".join([*clauses, *period_clauses]), [*params, *period_params]


def _classification_join():
    return """
        left join transaction_classifications c
          on c.workspace_id = t.workspace_id
         and c.transaction_id = t.id
         and c.is_current = true
    """


def get_keyword_summary(connection, *, workspace_id: str, query_normalized: str, year=None, month=None):
    where_clause, params = _search_params(
        workspace_id=workspace_id,
        query_normalized=query_normalized,
        year=year,
        month=month,
    )

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            f"""
            select
                count(*)::int as total_transactions,
                coalesce(sum(amount), 0) as total_amount,
                coalesce(avg(amount), 0) as average_amount,
                coalesce(min(amount), 0) as min_amount,
                coalesce(max(amount), 0) as max_amount,
                min(transaction_date) as first_transaction_date,
                max(transaction_date) as last_transaction_date
            from transactions t
            where {where_clause}
            """,
            params,
        )

        return cursor.fetchone()


def get_keyword_insight_metrics(connection, *, workspace_id: str, query_normalized: str, year=None, month=None):
    where_clause, params = _search_params(
        workspace_id=workspace_id,
        query_normalized=query_normalized,
        year=year,
        month=month,
    )

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            f"""
            select
                {_classification_category_expr()} as category,
                count(*)::int as transaction_count,
                coalesce(sum(t.amount), 0) as total_amount
            from transactions t
            {_classification_join()}
            where {where_clause}
            group by 1
            order by transaction_count desc, total_amount desc
            limit 1
            """,
            params,
        )
        top_category = cursor.fetchone()

        cursor.execute(
            f"""
            select
                coalesce(nullif(t.source_fund, ''), '-') as source_fund,
                count(*)::int as transaction_count,
                coalesce(sum(t.amount), 0) as total_amount
            from transactions t
            where {where_clause}
            group by 1
            order by transaction_count desc, total_amount desc
            limit 1
            """,
            params,
        )
        top_source_fund = cursor.fetchone()

        cursor.execute(
            f"""
            select
                t.id,
                t.transaction_date,
                t.title,
                {_classification_category_expr()} as category,
                {_classification_financial_type_expr()} as financial_type,
                t.amount,
                coalesce(t.source_fund, '') as source_fund
            from transactions t
            {_classification_join()}
            where {where_clause}
            order by t.amount desc, t.transaction_date desc, t.created_at desc
            limit 1
            """,
            params,
        )
        largest_transaction = cursor.fetchone()

    return {
        "top_category": top_category,
        "top_source_fund": top_source_fund,
        "largest_transaction": largest_transaction,
    }


def get_keyword_preview(connection, *, workspace_id: str, query_normalized: str, year=None, month=None):
    where_clause, params = _search_params(
        workspace_id=workspace_id,
        query_normalized=query_normalized,
        year=year,
        month=month,
    )

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            f"""
            select
                t.id,
                t.transaction_date,
                t.title,
                {_classification_category_expr()} as category,
                {_classification_financial_type_expr()} as financial_type,
                t.amount,
                coalesce(t.source_fund, '') as source_fund
            from transactions t
            {_classification_join()}
            where {where_clause}
            order by t.transaction_date desc, t.created_at desc
            limit 10
            """,
            params,
        )

        return cursor.fetchall()


def get_keyword_detail(
    connection,
    *,
    workspace_id: str,
    query_normalized: str,
    year=None,
    month=None,
    limit=25,
    offset=0,
):
    where_clause, params = _search_params(
        workspace_id=workspace_id,
        query_normalized=query_normalized,
        year=year,
        month=month,
    )

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            f"""
            select
                t.id,
                t.transaction_date,
                t.title,
                {_classification_category_expr()} as category,
                {_classification_financial_type_expr()} as financial_type,
                t.amount,
                coalesce(t.source_fund, '') as source_fund,
                coalesce(t.note, '') as note
            from transactions t
            {_classification_join()}
            where {where_clause}
            order by t.transaction_date desc, t.created_at desc
            limit %s offset %s
            """,
            [*params, limit, offset],
        )

        rows = cursor.fetchall()

        cursor.execute(
            f"""
            select count(*)::int as total_transactions
            from transactions t
            where {where_clause}
            """,
            params,
        )

        total = cursor.fetchone()["total_transactions"]

    return {
        "rows": rows,
        "total": total,
    }
