from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class PeriodMode(StrEnum):
    YEAR_MONTH = "year_month"
    DATE_RANGE = "date_range"
    PRESET = "preset"
    ALL_TIME = "all_time"
    DEFAULT = "default"


class PeriodPreset(StrEnum):
    LAST_7_DAYS = "last_7_days"
    LAST_1_MONTH = "last_1_month"
    LAST_3_MONTHS = "last_3_months"
    LAST_6_MONTHS = "last_6_months"
    LAST_YEAR = "last_year"
    ALL_TIME = "all_time"


@dataclass(frozen=True)
class ResolvedPeriod:
    mode: PeriodMode
    year: int | None = None
    month: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    end_exclusive: date | None = None
    preset: str | None = None

    @property
    def has_date_bounds(self) -> bool:
        return self.start_date is not None and self.end_exclusive is not None

    @property
    def is_all_time(self) -> bool:
        return self.mode == PeriodMode.ALL_TIME


def _parse_int(value, *, field_name: str) -> int | None:
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc


def _parse_date(value, *, field_name: str) -> date | None:
    if value in (None, ""):
        return None

    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format") from exc


def _month_bounds(year: int, month: int | None = None) -> tuple[date, date]:
    selected_month = month or 1
    period_start = date(year, selected_month, 1)

    if month:
        if month == 12:
            return period_start, date(year + 1, 1, 1)

        return period_start, date(year, month + 1, 1)

    return period_start, date(year + 1, 1, 1)


def _shift_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    month_lengths = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                     31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(value.day, month_lengths[month - 1])

    return date(year, month, day)


def _preset_bounds(preset: str, *, anchor_date: date) -> tuple[date, date] | None:
    end_exclusive = anchor_date + timedelta(days=1)

    if preset == PeriodPreset.LAST_7_DAYS:
        return anchor_date - timedelta(days=6), end_exclusive

    if preset == PeriodPreset.LAST_1_MONTH:
        return _shift_months(anchor_date, -1) + timedelta(days=1), end_exclusive

    if preset == PeriodPreset.LAST_3_MONTHS:
        return _shift_months(anchor_date, -3) + timedelta(days=1), end_exclusive

    if preset == PeriodPreset.LAST_6_MONTHS:
        return _shift_months(anchor_date, -6) + timedelta(days=1), end_exclusive

    if preset == PeriodPreset.LAST_YEAR:
        return _shift_months(anchor_date, -12) + timedelta(days=1), end_exclusive

    return None


def resolve_period(
    *,
    year=None,
    month=None,
    start_date=None,
    end_date=None,
    period_mode: str | None = None,
    preset: str | None = None,
    anchor_date: date | None = None,
) -> ResolvedPeriod:
    parsed_year = _parse_int(year, field_name="year")
    parsed_month = _parse_int(month, field_name="month")
    parsed_start_date = _parse_date(start_date, field_name="start_date")
    parsed_end_date = _parse_date(end_date, field_name="end_date")
    normalized_mode = str(period_mode or "").strip().lower()
    normalized_preset = str(preset or "").strip().lower() or None
    effective_preset = (
        normalized_preset
        or (normalized_mode if normalized_mode in {item.value for item in PeriodPreset} else None)
    )

    if parsed_month is not None and (parsed_month < 1 or parsed_month > 12):
        raise ValueError("Month must be between 1 and 12")

    if (parsed_start_date is None) != (parsed_end_date is None):
        raise ValueError("start_date and end_date must be provided together")

    if parsed_start_date and parsed_end_date:
        if parsed_start_date > parsed_end_date:
            raise ValueError("start_date must be before or equal to end_date")

        return ResolvedPeriod(
            mode=PeriodMode.DATE_RANGE,
            year=parsed_year,
            month=parsed_month,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            end_exclusive=parsed_end_date + timedelta(days=1),
            preset=normalized_preset,
        )

    if normalized_mode == PeriodMode.ALL_TIME or effective_preset == PeriodPreset.ALL_TIME:
        return ResolvedPeriod(
            mode=PeriodMode.ALL_TIME,
            year=parsed_year,
            month=parsed_month,
            preset=effective_preset or PeriodPreset.ALL_TIME,
        )

    if effective_preset:
        bounds = _preset_bounds(effective_preset, anchor_date=anchor_date or date.today())

        if bounds:
            period_start, end_exclusive = bounds
            return ResolvedPeriod(
                mode=PeriodMode.PRESET,
                year=parsed_year,
                month=parsed_month,
                start_date=period_start,
                end_date=end_exclusive - timedelta(days=1),
                end_exclusive=end_exclusive,
                preset=effective_preset,
            )

    if parsed_year is not None:
        period_start, end_exclusive = _month_bounds(parsed_year, parsed_month)

        return ResolvedPeriod(
            mode=PeriodMode.YEAR_MONTH,
            year=parsed_year,
            month=parsed_month,
            start_date=period_start,
            end_date=end_exclusive - timedelta(days=1),
            end_exclusive=end_exclusive,
            preset=effective_preset,
        )

    if parsed_month is not None:
        return ResolvedPeriod(
            mode=PeriodMode.DEFAULT,
            month=parsed_month,
            preset=effective_preset,
        )

    return ResolvedPeriod(
        mode=PeriodMode.DEFAULT,
        preset=effective_preset,
    )
