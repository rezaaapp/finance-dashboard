from psycopg.rows import dict_row


def _serialize_budget(row) -> dict:
    return {
        "id": str(row["id"]),
        "workspace_id": str(row["workspace_id"]),
        "year": int(row["year"]),
        "month": int(row["month"]),
        "category": row["category"],
        "amount": float(row["amount"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _serialize_ignored_category(row) -> dict:
    return {
        "id": str(row["id"]),
        "workspace_id": str(row["workspace_id"]),
        "year": int(row["year"]),
        "month": int(row["month"]),
        "category": row["category"],
        "created_at": row["created_at"],
    }


def _normalize_category(category: str) -> str:
    normalized_category = str(category or "").strip()

    if not normalized_category:
        raise ValueError("category is required")

    return normalized_category


def _normalize_amount(amount: float) -> float:
    normalized_amount = float(amount or 0)

    if normalized_amount < 0:
        raise ValueError("amount must be greater than or equal to 0")

    return normalized_amount


def get_budgets_by_period(
    connection,
    *,
    workspace_id: str,
    year: int,
    month: int,
) -> list[dict]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                workspace_id,
                year,
                month,
                category,
                amount,
                created_at,
                updated_at
            from budgets
            where workspace_id = %s
              and year = %s
              and month = %s
            order by lower(category)
            """,
            (workspace_id, int(year), int(month)),
        )

        return [_serialize_budget(row) for row in cursor.fetchall()]


def get_budget_by_id(connection, *, workspace_id: str, budget_id: str) -> dict | None:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                workspace_id,
                year,
                month,
                category,
                amount,
                created_at,
                updated_at
            from budgets
            where workspace_id = %s
              and id = %s
            """,
            (workspace_id, budget_id),
        )
        row = cursor.fetchone()

    return _serialize_budget(row) if row else None


def upsert_budget_category(
    connection,
    *,
    workspace_id: str,
    year: int,
    month: int,
    category: str,
    amount: float,
) -> dict:
    normalized_category = _normalize_category(category)
    normalized_amount = _normalize_amount(amount)

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into budgets (
                workspace_id,
                year,
                month,
                category,
                amount
            )
            values (%s, %s, %s, %s, %s)
            on conflict (workspace_id, year, month, category)
            do update set
                amount = excluded.amount,
                updated_at = now()
            returning
                id,
                workspace_id,
                year,
                month,
                category,
                amount,
                created_at,
                updated_at
            """,
            (
                workspace_id,
                int(year),
                int(month),
                normalized_category,
                normalized_amount,
            ),
        )
        row = cursor.fetchone()

    return _serialize_budget(row)


def update_budget_category(
    connection,
    *,
    workspace_id: str,
    budget_id: str,
    category: str,
    amount: float,
) -> dict | None:
    normalized_category = _normalize_category(category)
    normalized_amount = _normalize_amount(amount)

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update budgets
            set
                category = %s,
                amount = %s,
                updated_at = now()
            where workspace_id = %s
              and id = %s
            returning
                id,
                workspace_id,
                year,
                month,
                category,
                amount,
                created_at,
                updated_at
            """,
            (
                normalized_category,
                normalized_amount,
                workspace_id,
                budget_id,
            ),
        )
        row = cursor.fetchone()

    return _serialize_budget(row) if row else None


def delete_budget_category(
    connection,
    *,
    workspace_id: str,
    budget_id: str,
) -> dict | None:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            delete from budgets
            where workspace_id = %s
              and id = %s
            returning
                id,
                workspace_id,
                year,
                month,
                category,
                amount,
                created_at,
                updated_at
            """,
            (workspace_id, budget_id),
        )
        row = cursor.fetchone()

    return _serialize_budget(row) if row else None


def delete_budgets_by_period(
    connection,
    *,
    workspace_id: str,
    year: int,
    month: int,
) -> int:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            delete from budgets
            where workspace_id = %s
              and year = %s
              and month = %s
            returning id
            """,
            (workspace_id, int(year), int(month)),
        )

        return len(cursor.fetchall())


def get_ignored_categories_by_period(
    connection,
    *,
    workspace_id: str,
    year: int,
    month: int,
) -> list[dict]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                workspace_id,
                year,
                month,
                category,
                created_at
            from budget_category_ignores
            where workspace_id = %s
              and year = %s
              and month = %s
            order by lower(category)
            """,
            (workspace_id, int(year), int(month)),
        )

        return [_serialize_ignored_category(row) for row in cursor.fetchall()]


def add_ignored_category(
    connection,
    *,
    workspace_id: str,
    year: int,
    month: int,
    category: str,
) -> dict:
    normalized_category = _normalize_category(category)

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into budget_category_ignores (
                workspace_id,
                year,
                month,
                category
            )
            values (%s, %s, %s, %s)
            on conflict (workspace_id, year, month, category)
            do update set
                category = excluded.category
            returning
                id,
                workspace_id,
                year,
                month,
                category,
                created_at
            """,
            (
                workspace_id,
                int(year),
                int(month),
                normalized_category,
            ),
        )
        row = cursor.fetchone()

    return _serialize_ignored_category(row)


def remove_ignored_category(
    connection,
    *,
    workspace_id: str,
    ignored_id: str,
) -> dict | None:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            delete from budget_category_ignores
            where workspace_id = %s
              and id = %s
            returning
                id,
                workspace_id,
                year,
                month,
                category,
                created_at
            """,
            (workspace_id, ignored_id),
        )
        row = cursor.fetchone()

    return _serialize_ignored_category(row) if row else None
