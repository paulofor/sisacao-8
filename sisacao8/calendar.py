"""Trading-day helpers shared by Sisacao-8 services."""

from __future__ import annotations

import datetime as dt
from typing import Iterable, Set

DateLike = dt.date | dt.datetime | str


def _normalize_date(value: DateLike) -> dt.date:
    """Return ``value`` converted to :class:`datetime.date`."""

    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.datetime.strptime(str(value), "%Y-%m-%d").date()


def normalize_holidays(values: Iterable[DateLike] | None) -> Set[dt.date]:
    """Return a set of normalized holiday dates."""

    normalized: Set[dt.date] = set()
    if not values:
        return normalized
    for item in values:
        try:
            normalized.add(_normalize_date(item))
        except ValueError:
            continue
    return normalized


def is_trading_day(date_value: dt.date, holidays: Iterable[DateLike] | None = None) -> bool:
    """Return ``True`` when ``date_value`` is a weekday and not in ``holidays``."""

    if date_value.weekday() >= 5:
        return False
    holiday_set = normalize_holidays(holidays)
    return date_value not in holiday_set


def previous_trading_day(
    date_value: dt.date,
    holidays: Iterable[DateLike] | None = None,
) -> dt.date:
    """Return the previous business day before ``date_value``."""

    holiday_set = normalize_holidays(holidays)
    candidate = date_value
    while True:
        candidate -= dt.timedelta(days=1)
        if is_trading_day(candidate, holiday_set):
            return candidate


def next_trading_day(
    date_value: dt.date,
    holidays: Iterable[DateLike] | None = None,
) -> dt.date:
    """Return the next business day after ``date_value``."""

    holiday_set = normalize_holidays(holidays)
    candidate = date_value
    while True:
        candidate += dt.timedelta(days=1)
        if is_trading_day(candidate, holiday_set):
            return candidate


def add_trading_days(
    date_value: dt.date,
    delta: int,
    holidays: Iterable[DateLike] | None = None,
) -> dt.date:
    """Advance ``date_value`` by ``delta`` trading sessions (positive or negative)."""

    if delta == 0:
        return date_value if is_trading_day(date_value, holidays) else next_trading_day(date_value, holidays)
    holiday_set = normalize_holidays(holidays)
    step = 1 if delta > 0 else -1
    remaining = abs(delta)
    candidate = date_value
    while remaining > 0:
        candidate += dt.timedelta(days=step)
        if is_trading_day(candidate, holiday_set):
            remaining -= 1
    return candidate
