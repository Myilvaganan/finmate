"""Reusable period math: every MoM/YoY comparison and month/day enumeration in the analytics
module should go through here so "previous period" always means the same thing everywhere."""
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional, Tuple

from dateutil.relativedelta import relativedelta


@dataclass
class Comparison:
    current: float
    previous: float
    change: float
    change_percent: Optional[float]  # None when previous is 0 -- "New"/"Not available", never inf
    trend: str  # up | down | flat


def compare(current: float, previous: float) -> Comparison:
    change = round(current - previous, 2)
    if previous == 0:
        change_percent = None
    else:
        change_percent = round((current - previous) / abs(previous) * 100, 2)
    trend = "flat"
    if change > 0:
        trend = "up"
    elif change < 0:
        trend = "down"
    return Comparison(current=round(current, 2), previous=round(previous, 2), change=change,
                       change_percent=change_percent, trend=trend)


def previous_equivalent_period(start: date, end: date) -> Tuple[date, date]:
    """The immediately preceding period of the same length (e.g. 01-31 Aug -> 01-31 Jul)."""
    length = (end - start).days
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=length)
    return prev_start, prev_end


def previous_year_period(start: date, end: date) -> Tuple[date, date]:
    """Same calendar dates, one year earlier -- for YoY comparisons. relativedelta handles leap
    years correctly (29 Feb -> 28 Feb on a non-leap target year)."""
    return start - relativedelta(years=1), end - relativedelta(years=1)


def month_key(d: date) -> str:
    return d.strftime("%Y-%m")


def month_start(d: date) -> date:
    return d.replace(day=1)


def enumerate_months(start: date, end: date) -> List[date]:
    """Every month start between start and end, inclusive -- used to zero-fill series so months
    with no transactions still appear (spec: never omit zero-value periods)."""
    months = []
    cursor = month_start(start)
    last = month_start(end)
    while cursor <= last:
        months.append(cursor)
        cursor = cursor + relativedelta(months=1)
    return months


def enumerate_days(start: date, end: date) -> List[date]:
    days = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def choose_granularity(start: date, end: date) -> str:
    """Auto-pick a sensible bucket size for a date-range-driven chart: daily for <=1 month,
    weekly for <=6 months, monthly beyond that. Callers may still let the user override."""
    days = (end - start).days
    if days <= 31:
        return "daily"
    if days <= 186:
        return "weekly"
    return "monthly"
