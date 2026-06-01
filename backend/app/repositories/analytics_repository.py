from collections import defaultdict
from math import sqrt

from psycopg.errors import UndefinedTable
from psycopg.rows import dict_row


def _month_expr():
    return "to_char(transaction_date, 'YYYY-MM')"


def _category_expr():
    return "lower(trim(coalesce(raw_payload->>'_category_normalized', raw_category, '')))"


def _raw_category_expr():
    return "lower(trim(coalesce(raw_category, '')))"


def _category_label_expr():
    return """
        coalesce(
            nullif(raw_payload->>'_category_normalized', ''),
            nullif(raw_category, ''),
            'Uncategorized'
        )
    """


def _category_in(categories):
    category_expr = _raw_category_expr()
    values = ", ".join(f"'{category}'" for category in categories)

    return f"{category_expr} in ({values})"


def _explicit_expense_condition():
    return _category_in((
        "tagihan non rutin",
        "tagihan tahunan",
        "gift",
        "transportasi non rutin",
    ))


def _income_condition():
    return (
        f"not ({_explicit_expense_condition()}) and "
        "("
        "direction = 'income' or "
        f"{_category_in(('income', 'gaji', 'salary', 'bonus', 'pendapatan', 'pemasukan'))}"
        ")"
    )


def _saving_condition():
    return (
        f"not ({_explicit_expense_condition()}) and "
        "("
        "direction = 'saving_transfer' or "
        f"{_category_in(('saving', 'tabungan', 'investasi', 'reksadana', 'saham', 'emas', 'deposito', 'dana darurat', 'rumah', 'pendidikan', 'mobil', 'umroh'))}"
        ")"
    )


def _expense_condition():
    return (
        f"(({_explicit_expense_condition()}) or direction = 'expense') "
        f"and not ({_income_condition()}) "
        f"and not ({_saving_condition()})"
    )


def _direction_condition(direction):
    if direction == "income":
        return f"({_income_condition()})"

    if direction == "saving_transfer":
        return f"({_saving_condition()})"

    if direction == "expense":
        return f"({_expense_condition()})"

    return "direction = %s"


def _filters(year=None, month=None, direction=None, name=None):
    clauses = [
        "workspace_id = %s",
        "transaction_date is not null",
        "transaction_date <= current_date",
    ]
    params = []

    if year:
        clauses.append("extract(year from transaction_date)::int = %s")
        params.append(int(year))

    if month:
        clauses.append("extract(month from transaction_date)::int = %s")
        params.append(int(month))

    if direction:
        clauses.append(_direction_condition(direction))
        if direction not in {"income", "saving_transfer", "expense"}:
            params.append(direction)

    if name:
        clauses.append("coalesce(raw_payload->>'Nama', '') = %s")
        params.append(name)

    return " and ".join(clauses), params


def _fetch_all(connection, query, params):
    try:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    except UndefinedTable:
        return []


def get_available_years(connection, *, workspace_id: str):
    rows = _fetch_all(
        connection,
        """
        select distinct extract(year from transaction_date)::int as year
        from transactions
        where workspace_id = %s
          and transaction_date is not null
          and transaction_date <= current_date
        order by year desc
        """,
        (workspace_id,),
    )

    return [row["year"] for row in rows if row["year"] is not None]


def get_summary(connection, *, workspace_id: str, year=None, month=None):
    where_clause, params = _filters(year, month)
    rows = _fetch_all(
        connection,
        f"""
        select
            coalesce(
                sum(amount) filter (where {_income_condition()}),
                0
            ) as total_income,
            coalesce(
                sum(amount) filter (where {_saving_condition()}),
                0
            ) as total_saving,
            coalesce(
                sum(amount) filter (where {_expense_condition()}),
                0
            ) as total_expense,
            count(*) as transaction_count
        from transactions
        where {where_clause}
        """,
        (workspace_id, *params),
    )
    summary = rows[0] if rows else {}
    total_income = float(summary.get("total_income") or 0)
    total_expense = float(summary.get("total_expense") or 0)
    total_saving = float(summary.get("total_saving") or 0)
    transaction_count = int(summary.get("transaction_count") or 0)

    return {
        "total_pengeluaran": total_expense,
        "total_saving": total_saving,
        "total_income": total_income,
        "trend_pengeluaran": 0,
        "trend_saving": 0,
        "trend_income": 0,
        "saving_ratio": round(total_saving / total_expense * 100, 2)
        if total_expense > 0 else 0,
        "surplus": float(total_income - total_expense - total_saving),
        "transaction_count": transaction_count,
        "net_cashflow": float(total_income - total_expense - total_saving),
        "data_source": {
            "year": str(year or ""),
            "name": "Supabase Transactions",
        },
    }


def get_monthly_totals(connection, *, workspace_id: str, year=None, month=None, direction="expense"):
    where_clause, params = _filters(year, month, direction)
    rows = _fetch_all(
        connection,
        f"""
        select
            {_month_expr()} as bulan,
            coalesce(sum(amount), 0) as total
        from transactions
        where {where_clause}
        group by 1
        order by 1
        """,
        (workspace_id, *params),
    )

    return [
        {
            "bulan": row["bulan"],
            "total": float(row["total"] or 0),
        }
        for row in rows
    ]


def get_spending_by_category(connection, *, workspace_id: str, year=None, month=None):
    where_clause, params = _filters(year, month, "expense")
    rows = _fetch_all(
        connection,
        f"""
        select
            {_category_label_expr()} as category,
            coalesce(sum(amount), 0) as total,
            count(*) as row_count
        from transactions
        where {where_clause}
        group by 1
        order by total desc
        """,
        (workspace_id, *params),
    )

    return [
        {
            "Kategori": row["category"],
            "Harga": float(row["total"] or 0),
            "count": int(row["row_count"] or 0),
        }
        for row in rows
    ]


def get_top_spending(connection, *, workspace_id: str, year=None, month=None, limit=10):
    where_clause, params = _filters(year, month, "expense")
    rows = _fetch_all(
        connection,
        f"""
        select
            transaction_date,
            title,
            {_category_label_expr()} as category,
            coalesce(raw_payload->>'Nama', '') as name,
            coalesce(source_fund, '') as source_fund,
            coalesce(note, '') as note,
            amount
        from transactions
        where {where_clause}
        order by amount desc
        limit %s
        """,
        (workspace_id, *params, limit),
    )

    return [
        {
            "nama_transaksi": row["title"],
            "kategori": row["category"],
            "harga": float(row["amount"] or 0),
            "nama": row["name"] or "-",
            "bulan": row["transaction_date"].strftime("%Y-%m")
            if row["transaction_date"] else "",
            "date": row["transaction_date"].isoformat()
            if row["transaction_date"] else "",
            "source_fund": row["source_fund"] or "-",
            "note": row["note"] or "",
        }
        for row in rows
    ]


def get_transactions(connection, *, workspace_id: str, year=None, month=None, name=None):
    where_clause, params = _filters(year, month, None, name)
    rows = _fetch_all(
        connection,
        f"""
        select
            transaction_date,
            title,
            {_category_label_expr()} as category,
            coalesce(raw_payload->>'Nama', '') as name,
            amount
        from transactions
        where {where_clause}
        order by transaction_date desc, created_at desc
        limit 500
        """,
        (workspace_id, *params),
    )

    return [
        {
            "date": row["transaction_date"].isoformat()
            if row["transaction_date"] else "",
            "category": row["category"],
            "item_name": row["title"],
            "user": row["name"] or "-",
            "amount": float(row["amount"] or 0),
        }
        for row in rows
    ]


def get_category_trends(connection, *, workspace_id: str, year=None, month=None, name=None):
    where_clause, params = _filters(year, month, "expense", name)
    rows = _fetch_all(
        connection,
        f"""
        select
            {_category_label_expr()} as category,
            {_month_expr()} as bulan,
            coalesce(sum(amount), 0) as total
        from transactions
        where {where_clause}
        group by 1, 2
        order by 2, 1
        """,
        (workspace_id, *params),
    )
    months = sorted({row["bulan"] for row in rows})
    categories = sorted({row["category"] for row in rows})
    totals = {
        (row["category"], row["bulan"]): float(row["total"] or 0)
        for row in rows
    }

    return {
        "months": months,
        "categories": [
            {
                "kategori": category,
                "total": sum(totals.get((category, bulan), 0) for bulan in months),
                "average": round(
                    sum(totals.get((category, bulan), 0) for bulan in months)
                    / len(months),
                    2,
                ) if months else 0,
                "values": [
                    {
                        "bulan": bulan,
                        "total": totals.get((category, bulan), 0),
                    }
                    for bulan in months
                ],
            }
            for category in categories
        ],
    }


def get_category_heatmap(connection, *, workspace_id: str, year=None, month=None, name=None):
    trends = get_category_trends(
        connection,
        workspace_id=workspace_id,
        year=year,
        month=month,
        name=name,
    )
    rows = []
    max_total = 0

    for category in trends["categories"]:
        month_values = []
        for value in category["values"]:
            total = value["total"]
            max_total = max(max_total, total)
            month_values.append({
                "bulan": value["bulan"],
                "total": total,
                "intensity": 0,
            })

        rows.append({
            "kategori": category["kategori"],
            "total": category["total"],
            "total_amount": category["total"],
            "months": month_values,
        })

    rows.sort(key=lambda row: (-float(row["total"] or 0), row["kategori"].lower()))

    for row in rows:
        for value in row["months"]:
            value["intensity"] = round(value["total"] / max_total, 4) if max_total else 0

    return {
        "months": trends["months"],
        "categories": [row["kategori"] for row in rows],
        "max_total": max_total,
        "rows": rows,
    }


def get_grocery_vs_food(connection, *, workspace_id: str, year=None, month=None, name=None):
    where_clause, params = _filters(year, month, "expense", name)
    rows = _fetch_all(
        connection,
        f"""
        select
            {_month_expr()} as bulan,
            {_category_expr()} as category,
            coalesce(sum(amount), 0) as total
        from transactions
        where {where_clause}
        group by 1, 2
        order by 1
        """,
        (workspace_id, *params),
    )
    month_map = defaultdict(lambda: {"Grocery": 0, "Makanan": 0})

    for row in rows:
        category = row["category"]
        total = float(row["total"] or 0)

        if any(keyword in category for keyword in ("grocery", "groceries", "belanja bulanan")):
            month_map[row["bulan"]]["Grocery"] += total
        elif any(keyword in category for keyword in ("food", "makanan", "jajan", "resto", "restaurant")):
            month_map[row["bulan"]]["Makanan"] += total

    return [
        {
            "bulan": bulan,
            "Grocery": totals["Grocery"],
            "Makanan": totals["Makanan"],
        }
        for bulan, totals in sorted(month_map.items())
        if totals["Grocery"] or totals["Makanan"]
    ]


def _aggregate_source(
    connection,
    *,
    workspace_id: str,
    year=None,
    month=None,
    name=None,
    direction="expense",
):
    where_clause, params = _filters(year, month, direction, name)
    rows = _fetch_all(
        connection,
        f"""
        select
            coalesce(nullif(source_fund, ''), 'Lainnya') as source,
            coalesce(sum(amount), 0) as total
        from transactions
        where {where_clause}
        group by 1
        order by total desc
        """,
        (workspace_id, *params),
    )

    return [
        {"source": row["source"], "total": float(row["total"] or 0)}
        for row in rows
    ]


def get_source_dana_analytics(connection, *, workspace_id: str, year=None, month=None, name=None):
    return {
        "income_sources": _aggregate_source(
            connection,
            workspace_id=workspace_id,
            year=year,
            month=month,
            name=name,
            direction="income",
        ),
        "saving_sources": _aggregate_source(
            connection,
            workspace_id=workspace_id,
            year=year,
            month=month,
            name=name,
            direction="saving_transfer",
        ),
        "spending_sources": _aggregate_source(
            connection,
            workspace_id=workspace_id,
            year=year,
            month=month,
            name=name,
            direction="expense",
        ),
    }


def get_monthly_allocation(connection, *, workspace_id: str, year=None, month=None, name=None):
    spending = get_monthly_totals(
        connection,
        workspace_id=workspace_id,
        year=year,
        month=month,
        direction="expense",
    )

    return [
        {
            "month": row["bulan"],
            "Needs": row["total"],
            "Wants": 0,
            "Savings": 0,
        }
        for row in spending
    ]


def _get_personal_monthly_comparison(connection, *, workspace_id: str, year=None, month=None):
    where_clause, params = _filters(year, month, "expense")
    rows = _fetch_all(
        connection,
        f"""
        select
            {_month_expr()} as month,
            coalesce(nullif(raw_payload->>'Nama', ''), 'Unknown') as name,
            coalesce(sum(amount), 0) as total
        from transactions
        where {where_clause}
        group by 1, 2
        order by 1, 2
        """,
        (workspace_id, *params),
    )
    comparison_by_month = defaultdict(dict)

    for row in rows:
        comparison_by_month[row["month"]]["month"] = row["month"]
        comparison_by_month[row["month"]][row["name"]] = float(row["total"] or 0)

    return [
        comparison_by_month[month]
        for month in sorted(comparison_by_month)
    ]


def _get_personal_top_categories(connection, *, workspace_id: str, year=None, month=None):
    where_clause, params = _filters(year, month, "expense")
    rows = _fetch_all(
        connection,
        f"""
        select
            coalesce(nullif(raw_payload->>'Nama', ''), 'Unknown') as name,
            {_category_label_expr()} as category,
            coalesce(sum(amount), 0) as total
        from transactions
        where {where_clause}
        group by 1, 2
        order by 1, total desc
        """,
        (workspace_id, *params),
    )
    categories_by_user = defaultdict(list)

    for row in rows:
        user_categories = categories_by_user[row["name"]]

        if len(user_categories) < 5:
            user_categories.append({
                "category": row["category"],
                "total": float(row["total"] or 0),
            })

    return dict(categories_by_user)


def get_personal_analytics(connection, *, workspace_id: str, year=None, month=None):
    transactions = get_transactions(
        connection,
        workspace_id=workspace_id,
        year=year,
        month=month,
    )
    where_clause, params = _filters(year, month)
    rows = _fetch_all(
        connection,
        f"""
        select
            coalesce(nullif(raw_payload->>'Nama', ''), 'Unknown') as name,
            coalesce(
                sum(amount) filter (where {_income_condition()}),
                0
            ) as income,
            coalesce(
                sum(amount) filter (where {_saving_condition()}),
                0
            ) as saving,
            coalesce(
                sum(amount) filter (where {_expense_condition()}),
                0
            ) as spending
        from transactions
        where {where_clause}
        group by 1
        """,
        (workspace_id, *params),
    )

    users = sorted({row["user"] for row in transactions if row["user"] and row["user"] != "-"})
    users_payload = [{"label": "All Data", "value": "all"}] + [
        {"label": user, "value": user}
        for user in users
    ]
    totals_by_user = defaultdict(lambda: {"income": 0, "spending": 0, "saving": 0})

    for row in rows:
        user = row["name"] or "Unknown"
        income = float(row["income"] or 0)
        saving = float(row["saving"] or 0)
        spending = float(row["spending"] or 0)

        totals_by_user[user]["income"] += income
        totals_by_user[user]["saving"] += saving
        totals_by_user[user]["spending"] += spending
        totals_by_user["all"]["income"] += income
        totals_by_user["all"]["saving"] += saving
        totals_by_user["all"]["spending"] += spending

    kpis = {}
    for user_key, values in totals_by_user.items():
        income = values["income"]
        saving = values["saving"]
        kpis[user_key] = {
            **values,
            "saving_rate": round(saving / income * 100, 2) if income > 0 else 0,
        }

    return {
        "users": users_payload,
        "kpis": kpis or {
            "all": {
                "income": 0,
                "spending": 0,
                "saving": 0,
                "saving_rate": 0,
            },
        },
        "comparison": _get_personal_monthly_comparison(
            connection,
            workspace_id=workspace_id,
            year=year,
            month=month,
        ),
        "top_categories": {
            "all": [
                {
                    "category": row["Kategori"],
                    "total": row["Harga"],
                }
                for row in get_spending_by_category(
                    connection,
                    workspace_id=workspace_id,
                    year=year,
                    month=month,
                )[:5]
            ],
            **_get_personal_top_categories(
                connection,
                workspace_id=workspace_id,
                year=year,
                month=month,
            ),
        },
    }


def get_anomalies(connection, *, workspace_id: str, year=None, month=None):
    where_clause, params = _filters(year, month, "expense")
    rows = _fetch_all(
        connection,
        f"""
        select
            transaction_date,
            title,
            {_category_label_expr()} as category,
            coalesce(raw_payload->>'Nama', '') as name,
            amount,
            avg(amount) over (partition by {_category_label_expr()}) as avg_amount,
            stddev_pop(amount) over (partition by {_category_label_expr()}) as stddev_amount
        from transactions
        where {where_clause}
        order by amount desc
        """,
        (workspace_id, *params),
    )
    anomalies = []

    for row in rows:
        avg_amount = float(row["avg_amount"] or 0)
        stddev_amount = float(row["stddev_amount"] or 0)
        amount = float(row["amount"] or 0)
        threshold = avg_amount + (2 * stddev_amount)

        if stddev_amount > 0 and amount > threshold:
            anomalies.append({
                "Waktu Transaksi": row["transaction_date"].isoformat()
                if row["transaction_date"] else "",
                "Kategori": row["category"],
                "Harga": amount,
                "Nama": row["name"] or "-",
                "Nama Transaksi": row["title"],
            })

    return anomalies[:20]


def get_latest_insight(connection, *, workspace_id: str, year=None, month=None):
    spending = get_monthly_totals(
        connection,
        workspace_id=workspace_id,
        year=year,
        month=month,
        direction="expense",
    )

    if not spending:
        return {
            "bulan": None,
            "spending": 0,
            "saving": 0,
            "income": 0,
            "saving_ratio": 0,
            "status": "NO_DATA",
        }

    latest = spending[-1]
    latest_year, latest_month = latest["bulan"].split("-")
    latest_summary = get_summary(
        connection,
        workspace_id=workspace_id,
        year=int(latest_year),
        month=int(latest_month),
    )

    return {
        "bulan": latest["bulan"],
        "spending": latest_summary["total_pengeluaran"],
        "saving": latest_summary["total_saving"],
        "income": latest_summary["total_income"],
        "saving_ratio": latest_summary["saving_ratio"],
        "status": "HEALTHY" if latest_summary["saving_ratio"] >= 30 else "WARNING",
    }


def get_budget_forecast(connection, *, workspace_id: str, year=None, month=None):
    current_spending = get_spending_by_category(
        connection,
        workspace_id=workspace_id,
        year=year,
        month=month,
    )
    forecast = [
        {
            "category": row["Kategori"],
            "forecast_budget": 0,
            "current_spending": row["Harga"],
            "usage_rate": 0,
        }
        for row in current_spending[:8]
    ]

    return {
        "method": "actual_spending",
        "alerts": [],
        "forecast": forecast,
        "summary": {
            "total_forecast": 0,
            "current_spending": round(sum(item["current_spending"] for item in forecast), 2),
            "alert_count": 0,
        },
    }
