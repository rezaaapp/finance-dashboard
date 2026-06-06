from app.repositories import analytics_repository as analytics
from app.config import settings
from app.repositories.insight_settings_repository import (
    get_effective_insight_settings,
)


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


def _count_by_type(breakdown: list[dict]) -> dict:
    return {
        row["type"]: int(row.get("count") or 0)
        for row in breakdown
    }


def safe_ratio(numerator, denominator) -> float:
    numerator = float(numerator or 0)
    denominator = float(denominator or 0)
    return round(numerator / denominator, 4) if denominator > 0 else 0


def format_percentage_for_message(value) -> str:
    return f"{round(float(value or 0) * 100, 1)}%"


def get_severity_for_need(need_ratio: float, insight_settings: dict) -> str:
    if need_ratio >= insight_settings["need_danger_ratio"]:
        return "danger"

    if need_ratio >= insight_settings["need_warning_ratio"]:
        return "warning"

    return "neutral"


def get_severity_for_want(want_ratio: float, insight_settings: dict) -> str:
    if want_ratio >= insight_settings["want_danger_ratio"]:
        return "danger"

    if want_ratio >= insight_settings["want_warning_ratio"]:
        return "warning"

    return "info"


def get_severity_for_saving(
    saving_rate: float,
    income: float,
    insight_settings: dict,
) -> str:
    if saving_rate >= insight_settings["saving_good_ratio"]:
        return "positive"

    if income > 0 and saving_rate < insight_settings["saving_warning_ratio"]:
        return "warning"

    return "neutral"


def get_severity_for_uncategorized(count: int, insight_settings: dict) -> str:
    if count >= insight_settings["uncategorized_danger_count"]:
        return "danger"

    if count >= insight_settings["uncategorized_warning_count"]:
        return "warning"

    return "positive"


def get_severity_for_anomaly(multiplier: float, insight_settings: dict) -> str:
    if multiplier >= insight_settings["anomaly_danger_multiplier"]:
        return "danger"

    if multiplier >= insight_settings["anomaly_warning_multiplier"]:
        return "warning"

    return "info"


def _highlight(
    *,
    insight_type: str,
    label: str,
    message: str,
    severity: str,
    amount: float,
    ratio: float | None = None,
    count: int | None = None,
) -> dict:
    payload = {
        "type": insight_type,
        "label": label,
        "message": message,
        "severity": severity,
        "amount": float(amount or 0),
    }

    if ratio is not None:
        payload["ratio"] = ratio

    if count is not None:
        payload["count"] = count

    return payload


def generate_rule_based_insights(connection, *, workspace_id: str, year=None, month=None):
    insight_settings = get_effective_insight_settings(
        connection,
        workspace_id=workspace_id,
        default_settings=settings.get_default_insight_settings(),
    )
    breakdown = analytics.get_financial_type_breakdown(
        connection,
        workspace_id=workspace_id,
        year=year,
        month=month,
    )
    amounts = _amount_by_type(breakdown)
    counts = _count_by_type(breakdown)
    need = amounts.get("need", 0)
    want = amounts.get("want", 0)
    saving = amounts.get("saving", 0)
    income = amounts.get("income", 0)
    uncategorized = amounts.get("uncategorized", 0)
    uncategorized_count = counts.get("uncategorized", 0)
    expense = need + want + uncategorized
    need_ratio = safe_ratio(need, expense)
    want_ratio = safe_ratio(want, expense)
    saving_rate = safe_ratio(saving, income)

    metrics = {
        "need_ratio": need_ratio,
        "want_ratio": want_ratio,
        "saving_rate": saving_rate,
        "uncategorized_count": uncategorized_count,
        "settings_source": insight_settings.get("source", "default"),
    }

    if not any(amounts.values()):
        return {
            "period": _period_label(year, month),
            "summary": "Not enough data to generate insights yet.",
            "highlights": [],
            "metrics": {
                **metrics,
                "expense": 0,
                "income": 0,
                "saving": 0,
                "top_financial_type": None,
            },
        }

    expense_groups = {
        "need": need,
        "want": want,
        "uncategorized": uncategorized,
    }
    top_financial_type = max(amounts.items(), key=lambda item: item[1])[0]
    top_expense_group = max(expense_groups.items(), key=lambda item: item[1])[0]
    highlights = [
        _highlight(
            insight_type="want",
            label="Want",
            message=(
                "Want spending is "
                f"{format_percentage_for_message(want_ratio)} of total expense."
            ),
            severity=get_severity_for_want(want_ratio, insight_settings),
            amount=want,
            ratio=want_ratio,
        ),
        _highlight(
            insight_type="need",
            label="Need",
            message=(
                "Need spending is the largest expense group."
                if top_expense_group == "need"
                else (
                    "Need spending is "
                    f"{format_percentage_for_message(need_ratio)} of total expense."
                )
            ),
            severity=get_severity_for_need(need_ratio, insight_settings),
            amount=need,
            ratio=need_ratio,
        ),
        _highlight(
            insight_type="saving",
            label="Saving",
            message=(
                "Saving allocation is "
                f"{format_percentage_for_message(saving_rate)} of income."
            ),
            severity=get_severity_for_saving(
                saving_rate,
                income,
                insight_settings,
            ),
            amount=saving,
            ratio=saving_rate,
        ),
        _highlight(
            insight_type="income",
            label="Income",
            message=(
                "Income is available for this period."
                if income > 0
                else "No income is recorded for this period."
            ),
            severity="neutral" if income > 0 else "info",
            amount=income,
        ),
        _highlight(
            insight_type="uncategorized",
            label="Uncategorized",
            message=(
                "All transactions are categorized."
                if uncategorized_count == 0
                else (
                    f"There are {uncategorized_count} uncategorized "
                    "transactions that need review."
                )
            ),
            severity=get_severity_for_uncategorized(
                uncategorized_count,
                insight_settings,
            ),
            amount=uncategorized,
            count=uncategorized_count,
        ),
    ]

    top_categories = analytics.get_spending_by_category(
        connection,
        workspace_id=workspace_id,
        year=year,
        month=month,
    )

    if top_categories:
        highlights.append(
            _highlight(
                insight_type="top_category",
                label="Top Category",
                message=f"Top expense category is {top_categories[0]['Kategori']}.",
                severity="info",
                amount=float(top_categories[0]["Harga"] or 0),
            )
        )

    if expense > 0:
        summary = (
            "Want spending is "
            f"{format_percentage_for_message(want_ratio)} of total expense "
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
