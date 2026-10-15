# app/memory/timeparse.py
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DEFAULT_TZ = "Africa/Lagos"
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}


@dataclass(frozen=True)
class TimeWindow:
    since: datetime | None   # inclusive, UTC
    until: datetime | None   # exclusive, UTC
    label: str


def safe_zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or DEFAULT_TZ)
    except Exception:
        return ZoneInfo(DEFAULT_TZ)


def _start_of_day(d: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(d, time.min, tzinfo=tz).astimezone(timezone.utc)


def _month_bounds(year: int, month: int, tz: ZoneInfo) -> tuple[datetime, datetime]:
    ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
    return _start_of_day(date(year, month, 1), tz), _start_of_day(date(ny, nm, 1), tz)


_N_AGO = re.compile(r"\b(?:past|last|previous)\s+(\d{1,3})\s+(day|week|month)s?\b")
_MONTH_NAME = re.compile(r"\b(?:in|during|back in|from)\s+(" + "|".join(MONTHS) + r")\b")


def parse_time_window(question: str, *, now: datetime,
                      tz_name: str | None = None) -> TimeWindow | None:
    """Deterministic: the backend computes dates, never the model."""
    tz = safe_zone(tz_name)
    q = (question or "").lower()
    today = now.astimezone(tz).date()

    m = _N_AGO.search(q)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        days = n * {"day": 1, "week": 7, "month": 30}[unit]
        return TimeWindow(now - timedelta(days=days), None,
                          f"the past {n} {unit}{'s' if n != 1 else ''}")

    if re.search(r"\byesterday\b", q):
        return TimeWindow(_start_of_day(today - timedelta(days=1), tz),
                          _start_of_day(today, tz), "yesterday")

    week_start = today - timedelta(days=today.weekday())      # Monday
    if re.search(r"\blast week\b", q):                         # previous calendar week
        prev = week_start - timedelta(days=7)
        return TimeWindow(_start_of_day(prev, tz), _start_of_day(week_start, tz), "last week")
    if re.search(r"\bthis week\b", q):
        return TimeWindow(_start_of_day(week_start, tz), None, "this week")

    if re.search(r"\blast month\b", q):
        y, mo = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
        since, until = _month_bounds(y, mo, tz)
        return TimeWindow(since, until, "last month")
    if re.search(r"\bthis month\b", q):
        since, _ = _month_bounds(today.year, today.month, tz)
        return TimeWindow(since, None, "this month")

    mn = _MONTH_NAME.search(q)
    if mn:
        mo = MONTHS[mn.group(1)]
        y = today.year if mo <= today.month else today.year - 1
        since, until = _month_bounds(y, mo, tz)
        return TimeWindow(since, until, mn.group(1).capitalize())

    if re.search(r"\b(recently|lately)\b", q):
        return TimeWindow(now - timedelta(days=14), None, "the last two weeks")
    return None