from app.repositories import analytics_repository as analytics


def _period_label(year=None, month=None) -> str:
    if year and month:
        return f"{int(year):04d}-{int(month):02d}"

    if year:
        return str(year)

    return "all"


def _amount_by_type(breakdown: list[dict]) -> dict:
    return {
        row["type"]: float(row.get("amount") or 0)
        for row in breakdown
    }


def generate_rule_based_insights(connection, *, workspace_id: str, year=None, month=None):
    breakdown = analytics.get_financial_type_breakdown(
        connection,
        workspace_id=workspace_id,
        year=year,
        month=month,
    )
    amounts = _amount_by_type(breakdown)
    need = amounts.get("need", 0)
    want = amounts.get("want", 0)
    saving = amounts.get("saving", 0)
    income = amounts.get("income", 0)
    uncategorized = amounts.get("uncategorized", 0)
    expense = need + want + uncategorized
    need_ratio = round(need / expense, 4) if expense > 0 else 0
    want_ratio = round(want / expense, 4) if expense > 0 else 0
    saving_rate = round(saving / income, 4) if income > 0 else 0

    metrics = {
        "need_ratio": need_ratio,
        "want_ratio": want_ratio,
        "saving_rate": saving_rate,
    }

    if not any(amounts.values()):
        return {
            "period": _period_label(year, month),
            "summary": "Not enough data to generate insights yet.",
            "highlights": [],
            "metrics": metrics,
        }

    expense_groups = {
        "need": need,
        "want": want,
        "uncategorized": uncategorized,
    }
    top_financial_type = max(amounts.items(), key=lambda item: item[1])[0]
    top_expense_group = max(expense_groups.items(), key=lambda item: item[1])[0]
    highlights = []

    if expense > 0:
        highlights.append(
            f"{top_expense_group.title()} spending is the largest expense group."
        )

    if income > 0:
        highlights.append(
            f"Saving allocation is {round(saving_rate * 100, 1)}% of income."
        )

    top_categories = analytics.get_spending_by_category(
        connection,
        workspace_id=workspace_id,
        year=year,
        month=month,
    )

    if top_categories:
        highlights.append(
            f"Top expense category is {top_categories[0]['Kategori']}."
        )

    if uncategorized > 0:
        highlights.append(
            "Some expense transactions are still uncategorized."
        )

    if expense > 0:
        summary = (
            f"Want spending is {round(want_ratio * 100, 1)}% of total expense "
            "this period."
        )
    elif income > 0 or saving > 0:
        summary = "Income and saving activity is available for this period."
    else:
        summary = "Not enough data to generate insights yet."

    return {
        "period": _period_label(year, month),
        "summary": summary,
        "highlights": highlights,
        "metrics": {
            **metrics,
            "expense": expense,
            "income": income,
            "saving": saving,
            "top_financial_type": top_financial_type,
        },
    }
