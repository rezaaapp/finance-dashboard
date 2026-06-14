from collections import defaultdict
from datetime import date
from math import ceil, sqrt

from psycopg.errors import UndefinedTable
from psycopg.rows import dict_row

from app.repositories.budget_repository import (
    get_budgets_by_period,
)


FINANCIAL_TYPES = ("need", "want", "saving", "income", "uncategorized")


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


def _classification_financial_type_expr():
    return """
        case
            when c.financial_type in (
                'need', 'want', 'saving', 'income', 'uncategorized'
            ) then c.financial_type
            when c.direction = 'income' then 'income'
            when c.direction = 'saving_transfer' then 'saving'
            when c.direction = 'expense' then 'uncategorized'
            when t.direction = 'income' then 'income'
            when t.direction = 'saving_transfer' then 'saving'
            when t.direction = 'expense' then 'uncategorized'
            else 'uncategorized'
        end
    """


def _classification_category_expr():
    return """
        coalesce(
            nullif(c.category, ''),
            nullif(c.category_normalized, ''),
            nullif(t.raw_payload->>'_category_normalized', ''),
            nullif(t.raw_category, ''),
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


def get_previous_period(year: int, month: int) -> tuple[int, int]:
    if int(month) == 1:
        return int(year) - 1, 12

    return int(year), int(month) - 1


def _trend_payload(current_value: float, previous_value: float) -> dict:
    current_value = float(current_value or 0)
    previous_value = float(previous_value or 0)
    difference = current_value - previous_value

    if previous_value > 0:
        percentage_change = round((difference / previous_value) * 100, 2)
        if percentage_change > 0:
            trend_direction = "up"
        elif percentage_change < 0:
            trend_direction = "down"
        else:
            trend_direction = "flat"

        return {
            "previous_value": previous_value,
            "difference": difference,
            "percentage_change": percentage_change,
            "trend_direction": trend_direction,
            "comparison_label": "vs last month",
        }

    if current_value == 0:
        return {
            "previous_value": previous_value,
            "difference": difference,
            "percentage_change": 0,
            "trend_direction": "flat",
            "comparison_label": "vs last month",
        }

    return {
        "previous_value": previous_value,
        "difference": difference,
        "percentage_change": None,
        "trend_direction": "unavailable",
        "comparison_label": "no previous data",
    }


def _empty_summary_totals():
    return {
        "income": 0.0,
        "saving": 0.0,
        "expense": 0.0,
        "transaction_count": 0,
    }


def _fetch_summary_totals(connection, *, workspace_id: str, year: int, month=None):
    month_clause = ""
    params = [workspace_id, int(year)]

    if month:
        month_clause = "and extract(month from t.transaction_date)::int = %s"
        params.append(int(month))

    financial_type_expr = _classification_financial_type_expr()
    rows = _fetch_all(
        connection,
        f"""
        select
            coalesce(sum(amount) filter (
                where financial_type = 'income'
            ), 0) as total_income,
            coalesce(sum(amount) filter (
                where financial_type = 'saving'
            ), 0) as total_saving,
            coalesce(sum(amount) filter (
                where financial_type in ('need', 'want', 'uncategorized')
            ), 0) as total_expense,
            count(*) as transaction_count
        from (
            select
                t.id,
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
              and extract(year from t.transaction_date)::int = %s
              {month_clause}
        ) period_transactions
        """,
        params,
    )

    if not rows:
        return _empty_summary_totals()

    row = rows[0]
    return {
        "income": float(row["total_income"] or 0),
        "saving": float(row["total_saving"] or 0),
        "expense": float(row["total_expense"] or 0),
        "transaction_count": int(row["transaction_count"] or 0),
    }


def _saving_rate_trend_payload(current_rate: float, previous_rate: float) -> dict:
    current_rate = float(current_rate or 0)
    previous_rate = float(previous_rate or 0)
    difference = round(current_rate - previous_rate, 2)

    if previous_rate > 0:
        if difference > 0:
            trend_direction = "up"
        elif difference < 0:
            trend_direction = "down"
        else:
            trend_direction = "flat"

        return {
            "previous_value": previous_rate,
            "difference": difference,
            "percentage_change": difference,
            "trend_direction": trend_direction,
            "comparison_label": "vs last period",
        }

    if current_rate == 0:
        return {
            "previous_value": previous_rate,
            "difference": difference,
            "percentage_change": 0,
            "trend_direction": "flat",
            "comparison_label": "vs last period",
        }

    return {
        "previous_value": previous_rate,
        "difference": difference,
        "percentage_change": None,
        "trend_direction": "unavailable",
        "comparison_label": "no previous data",
    }


def _personal_period_totals(
    connection,
    *,
    workspace_id: str,
    year=None,
    month=None,
) -> dict:
    clauses = [
        "t.workspace_id = %s",
        "t.transaction_date is not null",
        "t.transaction_date <= current_date",
    ]
    params = [workspace_id]

    if year:
        clauses.append("extract(year from t.transaction_date)::int = %s")
        params.append(int(year))

    if month:
        clauses.append("extract(month from t.transaction_date)::int = %s")
        params.append(int(month))

    financial_type_expr = _classification_financial_type_expr()
    rows = _fetch_all(
        connection,
        f"""
        select
            name,
            coalesce(sum(amount) filter (
                where financial_type = 'income'
            ), 0) as income,
            coalesce(sum(amount) filter (
                where financial_type = 'saving'
            ), 0) as saving,
            coalesce(sum(amount) filter (
                where financial_type in ('need', 'want', 'uncategorized')
            ), 0) as spending
        from (
            select
                coalesce(nullif(t.raw_payload->>'Nama', ''), 'Unknown') as name,
                t.amount,
                {financial_type_expr} as financial_type
            from transactions t
            left join transaction_classifications c
              on c.workspace_id = t.workspace_id
             and c.transaction_id = t.id
             and c.is_current = true
            where {" and ".join(clauses)}
        ) period_transactions
        group by name
        """,
        params,
    )
    totals = defaultdict(lambda: {"income": 0.0, "spending": 0.0, "saving": 0.0})

    for row in rows:
        user = row["name"] or "Unknown"
        income = float(row["income"] or 0)
        saving = float(row["saving"] or 0)
        spending = float(row["spending"] or 0)

        totals[user]["income"] += income
        totals[user]["saving"] += saving
        totals[user]["spending"] += spending
        totals["all"]["income"] += income
        totals["all"]["saving"] += saving
        totals["all"]["spending"] += spending

    return dict(totals)


def _personal_comparison_period(year=None, month=None) -> dict:
    if year and month:
        previous_year, previous_month = get_previous_period(int(year), int(month))

        return {
            "current_year": int(year),
            "current_month": int(month),
            "previous_year": previous_year,
            "previous_month": previous_month,
            "label": "vs last month",
        }

    if year:
        return {
            "current_year": int(year),
            "current_month": None,
            "previous_year": int(year) - 1,
            "previous_month": None,
            "label": "vs previous year",
        }

    return {
        "current_year": None,
        "current_month": None,
        "previous_year": None,
        "previous_month": None,
        "label": "no previous data",
    }


def _build_personal_kpi(current_values: dict, previous_values: dict) -> dict:
    current_values = current_values or {}
    previous_values = previous_values or {}
    income = float(current_values.get("income") or 0)
    spending = float(current_values.get("spending") or 0)
    saving = float(current_values.get("saving") or 0)
    previous_income = float(previous_values.get("income") or 0)
    previous_spending = float(previous_values.get("spending") or 0)
    previous_saving = float(previous_values.get("saving") or 0)
    saving_rate = round(saving / income * 100, 2) if income > 0 else 0
    previous_saving_rate = (
        round(previous_saving / previous_income * 100, 2)
        if previous_income > 0 else 0
    )
    income_trend = _trend_payload(income, previous_income)
    spending_trend = _trend_payload(spending, previous_spending)
    saving_trend = _trend_payload(saving, previous_saving)
    saving_rate_trend = _saving_rate_trend_payload(
        saving_rate,
        previous_saving_rate,
    )

    return {
        "income": income,
        "spending": spending,
        "saving": saving,
        "saving_rate": saving_rate,
        "income_previous": income_trend["previous_value"],
        "income_change_pct": income_trend["percentage_change"],
        "income_trend": income_trend["trend_direction"],
        "income_comparison_label": income_trend["comparison_label"],
        "spending_previous": spending_trend["previous_value"],
        "spending_change_pct": spending_trend["percentage_change"],
        "spending_trend": spending_trend["trend_direction"],
        "spending_comparison_label": spending_trend["comparison_label"],
        "saving_previous": saving_trend["previous_value"],
        "saving_change_pct": saving_trend["percentage_change"],
        "saving_trend": saving_trend["trend_direction"],
        "saving_comparison_label": saving_trend["comparison_label"],
        "saving_rate_previous": saving_rate_trend["previous_value"],
        "saving_rate_change_pct": saving_rate_trend["percentage_change"],
        "saving_rate_trend": saving_rate_trend["trend_direction"],
        "saving_rate_comparison_label": saving_rate_trend["comparison_label"],
    }


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
    if year:
        current_year = int(year)
        current_month = int(month) if month else None
        if current_month:
            previous_year, previous_month = get_previous_period(
                current_year,
                current_month,
            )
            comparison_label = "vs last month"
        else:
            previous_year = current_year - 1
            previous_month = None
            comparison_label = "vs previous year"

        current_totals = _fetch_summary_totals(
            connection,
            workspace_id=workspace_id,
            year=current_year,
            month=current_month,
        )
        previous_totals = _fetch_summary_totals(
            connection,
            workspace_id=workspace_id,
            year=previous_year,
            month=previous_month,
        )
        total_income = current_totals["income"]
        total_expense = current_totals["expense"]
        total_saving = current_totals["saving"]
        expense_trend = _trend_payload(
            total_expense,
            previous_totals["expense"],
        )
        saving_trend = _trend_payload(
            total_saving,
            previous_totals["saving"],
        )
        income_trend = _trend_payload(
            total_income,
            previous_totals["income"],
        )

        return {
            "total_pengeluaran": total_expense,
            "total_saving": total_saving,
            "total_income": total_income,
            "trend_pengeluaran": expense_trend["percentage_change"],
            "trend_saving": saving_trend["percentage_change"],
            "trend_income": income_trend["percentage_change"],
            "total_expenses": total_expense,
            "total_expenses_previous": expense_trend["previous_value"],
            "total_expenses_difference": expense_trend["difference"],
            "total_expenses_change_pct": expense_trend["percentage_change"],
            "total_expenses_trend": expense_trend["trend_direction"],
            "total_saving_previous": saving_trend["previous_value"],
            "total_saving_difference": saving_trend["difference"],
            "total_saving_change_pct": saving_trend["percentage_change"],
            "total_saving_trend": saving_trend["trend_direction"],
            "total_income_previous": income_trend["previous_value"],
            "total_income_difference": income_trend["difference"],
            "total_income_change_pct": income_trend["percentage_change"],
            "total_income_trend": income_trend["trend_direction"],
            "saving_ratio": round(total_saving / total_expense * 100, 2)
            if total_expense > 0 else 0,
            "surplus": float(total_income - total_expense - total_saving),
            "transaction_count": current_totals["transaction_count"],
            "net_cashflow": float(total_income - total_expense - total_saving),
            "comparison": {
                "current_year": current_year,
                "current_month": current_month,
                "previous_year": previous_year,
                "previous_month": previous_month,
                "label": comparison_label,
                "total_expenses_label": (
                    expense_trend["comparison_label"]
                    if expense_trend["trend_direction"] == "unavailable"
                    else comparison_label
                ),
                "total_saving_label": (
                    saving_trend["comparison_label"]
                    if saving_trend["trend_direction"] == "unavailable"
                    else comparison_label
                ),
                "total_income_label": (
                    income_trend["comparison_label"]
                    if income_trend["trend_direction"] == "unavailable"
                    else comparison_label
                ),
            },
            "data_source": {
                "year": str(year or ""),
                "name": "Supabase Transactions",
            },
        }

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


def get_budget_spending_by_category(
    connection,
    *,
    workspace_id: str,
    year: int,
    month: int,
):
    financial_type_expr = _classification_financial_type_expr()
    category_expr = _classification_category_expr()
    rows = _fetch_all(
        connection,
        f"""
        select
            category,
            coalesce(sum(amount), 0) as total,
            count(*) as row_count
        from (
            select
                t.amount,
                {category_expr} as category,
                {financial_type_expr} as financial_type
            from transactions t
            left join transaction_classifications c
              on c.workspace_id = t.workspace_id
             and c.transaction_id = t.id
             and c.is_current = true
            where t.workspace_id = %s
              and t.transaction_date is not null
              and t.transaction_date <= current_date
              and extract(year from t.transaction_date)::int = %s
              and extract(month from t.transaction_date)::int = %s
        ) budget_transactions
        where financial_type in ('need', 'want', 'uncategorized')
        group by 1
        order by total desc
        """,
        (workspace_id, int(year), int(month)),
    )

    return [
        {
            "Kategori": row["category"],
            "Harga": float(row["total"] or 0),
            "count": int(row["row_count"] or 0),
        }
        for row in rows
    ]


def get_available_budget_categories(connection, *, workspace_id: str) -> list[str]:
    financial_type_expr = _classification_financial_type_expr()
    rows = _fetch_all(
        connection,
        f"""
        select category
        from (
            select
                trim(t.raw_category) as category,
                {financial_type_expr} as financial_type
            from transactions t
            left join transaction_classifications c
              on c.workspace_id = t.workspace_id
             and c.transaction_id = t.id
             and c.is_current = true
            where t.workspace_id = %s
              and nullif(trim(coalesce(t.raw_category, '')), '') is not null
        ) available_transactions
        where financial_type in ('need', 'want', 'uncategorized')
        group by category
        order by lower(category), category
        """,
        (workspace_id,),
    )
    categories_by_key = {}

    for row in rows:
        category = str(row["category"] or "").strip()

        if not category:
            continue

        categories_by_key.setdefault(category.casefold(), category)

    return sorted(categories_by_key.values(), key=lambda value: value.casefold())


def _previous_month_periods(year: int, month: int, count: int = 3) -> list[dict]:
    periods = []
    current_year = int(year)
    current_month = int(month)

    for _index in range(count):
        current_month -= 1

        if current_month < 1:
            current_month = 12
            current_year -= 1

        periods.append({
            "year": current_year,
            "month": current_month,
            "label": f"{current_year:04d}-{current_month:02d}",
        })

    return periods


def _round_up_to_nearest(value: float, increment: int = 50000) -> float:
    value = float(value or 0)

    if value <= 0:
        return 0

    return float(ceil(value / increment) * increment)


def get_budget_history_by_category(
    connection,
    *,
    workspace_id: str,
    periods: list[dict],
):
    if not periods:
        return {}

    period_values = [
        (period["year"], period["month"], period["label"])
        for period in periods
    ]
    financial_type_expr = _classification_financial_type_expr()
    category_expr = _classification_category_expr()
    rows = _fetch_all(
        connection,
        f"""
        with selected_periods(year, month, period_label) as (
            values {", ".join(["(%s, %s, %s)"] * len(period_values))}
        ),
        budget_transactions as (
            select
                {category_expr} as category,
                sp.period_label,
                t.amount,
                {financial_type_expr} as financial_type
            from transactions t
            join selected_periods sp
              on extract(year from t.transaction_date)::int = sp.year
             and extract(month from t.transaction_date)::int = sp.month
            left join transaction_classifications c
              on c.workspace_id = t.workspace_id
             and c.transaction_id = t.id
             and c.is_current = true
            where t.workspace_id = %s
              and t.transaction_date is not null
              and t.transaction_date <= current_date
        )
        select
            category,
            period_label,
            coalesce(sum(amount), 0) as total
        from budget_transactions
        where financial_type in ('need', 'want', 'uncategorized')
        group by 1, 2
        order by 1, 2
        """,
        (
            *[
                value
                for period in period_values
                for value in period
            ],
            workspace_id,
        ),
    )
    history_by_category = defaultdict(list)

    for row in rows:
        total = float(row["total"] or 0)

        if total <= 0:
            continue

        history_by_category[row["category"]].append({
            "period": row["period_label"],
            "total": total,
        })

    return dict(history_by_category)


def get_financial_type_breakdown(connection, *, workspace_id: str, year=None, month=None):
    clauses = [
        "t.workspace_id = %s",
        "t.transaction_date is not null",
        "t.transaction_date <= current_date",
    ]
    params = [workspace_id]

    if year:
        clauses.append("extract(year from t.transaction_date)::int = %s")
        params.append(int(year))

    if month:
        clauses.append("extract(month from t.transaction_date)::int = %s")
        params.append(int(month))

    financial_type_expr = _classification_financial_type_expr()
    rows = _fetch_all(
        connection,
        f"""
        select
            {financial_type_expr} as financial_type,
            coalesce(sum(t.amount), 0) as amount,
            count(t.id) as row_count
        from transactions t
        left join transaction_classifications c
          on c.workspace_id = t.workspace_id
         and c.transaction_id = t.id
         and c.is_current = true
        where {" and ".join(clauses)}
        group by 1
        """,
        params,
    )
    totals = {
        financial_type: {"amount": 0.0, "count": 0}
        for financial_type in FINANCIAL_TYPES
    }

    for row in rows:
        financial_type = row["financial_type"] or "uncategorized"

        if financial_type not in totals:
            financial_type = "uncategorized"

        totals[financial_type]["amount"] += float(row["amount"] or 0)
        totals[financial_type]["count"] += int(row["row_count"] or 0)

    return [
        {
            "type": financial_type,
            "amount": totals[financial_type]["amount"],
            "count": totals[financial_type]["count"],
        }
        for financial_type in FINANCIAL_TYPES
    ]


def get_monthly_financial_type_breakdown(connection, *, workspace_id: str, year: int):
    selected_year = int(year)
    today = date.today()

    if selected_year > today.year:
        return []

    max_month = today.month if selected_year == today.year else 12
    financial_type_expr = _classification_financial_type_expr()
    rows = _fetch_all(
        connection,
        f"""
        select
            extract(month from t.transaction_date)::int as month,
            {financial_type_expr} as financial_type,
            coalesce(sum(t.amount), 0) as amount
        from transactions t
        left join transaction_classifications c
          on c.workspace_id = t.workspace_id
         and c.transaction_id = t.id
         and c.is_current = true
        where t.workspace_id = %s
          and t.transaction_date is not null
          and t.transaction_date <= current_date
          and extract(year from t.transaction_date)::int = %s
        group by 1, 2
        order by 1, 2
        """,
        (workspace_id, selected_year),
    )
    month_rows = {
        month: {
            "month": month,
            "need": 0.0,
            "want": 0.0,
            "saving": 0.0,
            "income": 0.0,
            "uncategorized": 0.0,
        }
        for month in range(1, max_month + 1)
    }

    for row in rows:
        month = int(row["month"] or 0)
        financial_type = row["financial_type"] or "uncategorized"

        if month not in month_rows:
            continue

        if financial_type not in FINANCIAL_TYPES:
            financial_type = "uncategorized"

        month_rows[month][financial_type] += float(row["amount"] or 0)

    return [month_rows[month] for month in sorted(month_rows)]


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
    comparison_period = _personal_comparison_period(year, month)
    current_totals = _personal_period_totals(
        connection,
        workspace_id=workspace_id,
        year=year,
        month=month,
    )
    previous_totals = (
        _personal_period_totals(
            connection,
            workspace_id=workspace_id,
            year=comparison_period["previous_year"],
            month=comparison_period["previous_month"],
        )
        if comparison_period["previous_year"]
        else {}
    )
    users = sorted({
        *[
            row["user"]
            for row in transactions
            if row["user"] and row["user"] != "-"
        ],
        *[
            user
            for user in current_totals.keys()
            if user != "all"
        ],
    })
    users_payload = [{"label": "All Data", "value": "all"}] + [
        {"label": user, "value": user}
        for user in users
    ]
    kpi_keys = {"all", *users}
    kpis = {
        user_key: _build_personal_kpi(
            current_totals.get(user_key, {}),
            previous_totals.get(user_key, {}),
        )
        for user_key in kpi_keys
    }

    return {
        "users": users_payload,
        "kpis": kpis,
        "comparison_period": comparison_period,
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


def get_anomalies(
    connection,
    *,
    workspace_id: str,
    year=None,
    month=None,
    insight_settings: dict | None = None,
):
    anomaly_warning_multiplier = float(
        (insight_settings or {}).get("anomaly_warning_multiplier", 2.0)
    )
    anomaly_danger_multiplier = float(
        (insight_settings or {}).get("anomaly_danger_multiplier", 3.0)
    )
    clauses = [
        "t.workspace_id = %s",
        "t.transaction_date is not null",
        "t.transaction_date <= current_date",
    ]
    params = [workspace_id]

    if year:
        clauses.append("extract(year from t.transaction_date)::int = %s")
        params.append(int(year))

    if month:
        clauses.append("extract(month from t.transaction_date)::int = %s")
        params.append(int(month))

    financial_type_expr = _classification_financial_type_expr()
    category_expr = _classification_category_expr()
    rows = _fetch_all(
        connection,
        f"""
        with base as (
            select
                t.id as transaction_id,
                t.transaction_date,
                t.title,
                {category_expr} as category,
                t.amount,
                {financial_type_expr} as financial_type
            from transactions t
            left join transaction_classifications c
              on c.workspace_id = t.workspace_id
             and c.transaction_id = t.id
             and c.is_current = true
            where {" and ".join(clauses)}
        ),
        scored as (
            select
                transaction_id,
                transaction_date,
                title,
                category,
                amount,
                financial_type,
                avg(amount) over (partition by category) as avg_amount,
                stddev_pop(amount) over (partition by category) as stddev_amount
            from base
            where financial_type in ('need', 'want', 'uncategorized')
        )
        select
            transaction_id,
            transaction_date,
            title,
            category,
            amount,
            avg_amount,
            stddev_amount
        from scored
        order by amount desc
        """,
        params,
    )
    anomalies = []

    for row in rows:
        avg_amount = float(row["avg_amount"] or 0)
        stddev_amount = float(row["stddev_amount"] or 0)
        amount = float(row["amount"] or 0)
        threshold = avg_amount + (2 * stddev_amount)
        ratio = amount / avg_amount if avg_amount > 0 else 0
        is_statistical_anomaly = stddev_amount > 0 and amount > threshold
        is_ratio_anomaly = (
            stddev_amount <= 0
            and avg_amount > 0
            and ratio >= anomaly_warning_multiplier
        )

        if is_statistical_anomaly or is_ratio_anomaly:
            severity = (
                "danger"
                if ratio >= anomaly_danger_multiplier
                else "warning"
            )
            anomalies.append({
                "transaction_id": str(row["transaction_id"]),
                "title": row["title"],
                "category": row["category"],
                "amount": amount,
                "severity": severity,
                "explanation": (
                    f"This transaction is {ratio:.1f}x higher than your "
                    f"average {row['category']} spending."
                ),
                "Waktu Transaksi": row["transaction_date"].isoformat()
                if row["transaction_date"] else "",
                "Kategori": row["category"],
                "Nama Transaksi": row["title"],
                "Harga": amount,
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


def _budget_alert_for_usage(category: str, usage_rate: float, spending: float, budget: float):
    if usage_rate >= 100:
        severity = "danger"
        message = f"{category} sudah melewati anggaran bulan ini."
    elif usage_rate >= 90:
        severity = "warning"
        message = f"{category} sudah memakai {round(usage_rate)}% anggaran."
    elif usage_rate >= 80:
        severity = "info"
        message = f"{category} mendekati batas anggaran."
    else:
        return None

    return {
        "severity": severity,
        "category": category,
        "message": message,
        "usage_rate": round(usage_rate, 2),
        "current_spending": round(spending, 2),
        "budget": round(budget, 2),
    }


def _budget_recommendation_payload(category: str, history_rows: list[dict]) -> dict:
    history_totals = [float(row["total"] or 0) for row in history_rows]
    historical_average = (
        sum(history_totals) / len(history_totals)
        if history_totals
        else 0
    )
    recommended_budget = _round_up_to_nearest(historical_average * 1.1)

    return {
        "category": category,
        "historical_average": round(historical_average, 2),
        "recommended_budget": round(recommended_budget, 2),
        "history_months_count": len(history_rows),
        "history_periods": [row["period"] for row in history_rows],
    }


def _history_rows_for_category(
    history_by_category: dict,
    history_by_key: dict,
    category: str,
) -> list[dict]:
    return (
        history_by_category.get(category)
        or history_by_key.get(category.strip().casefold())
        or []
    )


def get_budget_forecast(connection, *, workspace_id: str, year=None, month=None):
    available_categories = get_available_budget_categories(
        connection,
        workspace_id=workspace_id,
    )

    if not year or not month:
        return {
            "method": "monthly_budget",
            "period_required": True,
            "alerts": [],
            "categories": [],
            "forecast": [],
            "available_categories": available_categories,
            "category_recommendations": {},
            "ignored_categories": [],
            "summary": {
                "total_budget": 0,
                "total_forecast": 0,
                "current_spending": 0,
                "remaining_budget": 0,
                "budgeted_category_count": 0,
                "unbudgeted_category_count": 0,
                "over_budget_category_count": 0,
                "alert_count": 0,
            },
        }

    selected_year = int(year)
    selected_month = int(month)
    history_periods = _previous_month_periods(selected_year, selected_month)
    budgets = get_budgets_by_period(
        connection,
        workspace_id=workspace_id,
        year=selected_year,
        month=selected_month,
    )
    spending_rows = get_budget_spending_by_category(
        connection,
        workspace_id=workspace_id,
        year=selected_year,
        month=selected_month,
    )
    history_by_category = get_budget_history_by_category(
        connection,
        workspace_id=workspace_id,
        periods=history_periods,
    )
    history_by_key = {
        category.strip().casefold(): rows
        for category, rows in history_by_category.items()
    }
    spending_by_category = {
        row["Kategori"]: float(row["Harga"] or 0)
        for row in spending_rows
    }
    budget_by_category = {
        budget["category"]: budget
        for budget in budgets
    }
    category_names = sorted(
        {*budget_by_category.keys(), *spending_by_category.keys()},
        key=lambda value: value.lower(),
    )
    categories = []
    alerts = []
    recommendation_category_names = sorted(
        {
            *available_categories,
            *budget_by_category.keys(),
            *spending_by_category.keys(),
            *history_by_category.keys(),
        },
        key=lambda value: value.casefold(),
    )
    category_recommendations = {
        category: _budget_recommendation_payload(
            category,
            _history_rows_for_category(
                history_by_category,
                history_by_key,
                category,
            ),
        )
        for category in recommendation_category_names
        if str(category or "").strip()
    }

    for category in category_names:
        budget = budget_by_category.get(category)
        budget_amount = float(budget["amount"] if budget else 0)
        current_spending = float(spending_by_category.get(category, 0))
        remaining_budget = budget_amount - current_spending
        recommendation = category_recommendations.get(category) or (
            _budget_recommendation_payload(
                category,
                _history_rows_for_category(
                    history_by_category,
                    history_by_key,
                    category,
                ),
            )
        )
        usage_rate = (
            current_spending / budget_amount * 100
            if budget_amount > 0
            else 0
        )
        is_budgeted = bool(budget)
        budget_status = "budgeted" if is_budgeted else "unbudgeted"
        alert = (
            _budget_alert_for_usage(
                category,
                usage_rate,
                current_spending,
                budget_amount,
            )
            if budget_amount > 0
            else None
        )

        if alert:
            alerts.append(alert)

        categories.append({
            "id": budget["id"] if budget else None,
            "budget_id": budget["id"] if budget else None,
            "category": category,
            "budget": round(budget_amount, 2),
            "forecast_budget": round(budget_amount, 2),
            "spent": round(current_spending, 2),
            "current_spending": round(current_spending, 2),
            "remaining_budget": round(remaining_budget, 2),
            "remaining": round(remaining_budget, 2),
            "usage_rate": round(usage_rate, 2),
            "usage_percentage": round(usage_rate, 2),
            "status": alert["severity"] if alert else "neutral",
            "budget_status": budget_status,
            "is_budgeted": is_budgeted,
            "severity": alert["severity"] if alert else "neutral",
            "historical_average": recommendation["historical_average"],
            "recommended_budget": recommendation["recommended_budget"],
            "history_months_count": recommendation["history_months_count"],
            "history_periods": recommendation["history_periods"],
        })

    categories.sort(
        key=lambda item: (
            not item["is_budgeted"],
            -float(item["current_spending"] or 0),
            item["category"].lower(),
        )
    )
    total_budget = sum(item["budget"] for item in categories)
    current_spending = sum(item["current_spending"] for item in categories)

    return {
        "method": "monthly_budget",
        "period": f"{selected_year:04d}-{selected_month:02d}",
        "period_required": False,
        "alerts": alerts,
        "categories": categories,
        "forecast": categories,
        "available_categories": available_categories,
        "category_recommendations": category_recommendations,
        "ignored_categories": [],
        "summary": {
            "total_budget": round(total_budget, 2),
            "total_forecast": round(total_budget, 2),
            "current_spending": round(current_spending, 2),
            "remaining_budget": round(total_budget - current_spending, 2),
            "budgeted_category_count": sum(
                1 for item in categories if item["is_budgeted"]
            ),
            "unbudgeted_category_count": sum(
                1 for item in categories if not item["is_budgeted"]
            ),
            "over_budget_category_count": sum(
                1
                for item in categories
                if item["is_budgeted"]
                and item["budget"] > 0
                and item["usage_percentage"] >= 100
            ),
            "alert_count": len(alerts),
        },
    }
