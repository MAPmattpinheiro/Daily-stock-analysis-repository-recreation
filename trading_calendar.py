"""
Trading calendar — determines if today is a US market trading day.
Skips weekends and major US market holidays.
"""

from datetime import date, datetime
from typing import Optional
import os

def _us_holidays(year: int) -> set:
    """Return a set of US market holiday dates for the given year."""
    from datetime import date
    holidays = set()

    # New Year's Day (or observed)
    ny = date(year, 1, 1)
    if ny.weekday() == 6: ny = date(year, 1, 2)   # Sun -> Mon
    if ny.weekday() == 5: ny = date(year, 12, 31)  # Sat -> prev Fri
    holidays.add(ny)

    # MLK Day - 3rd Monday of January
    d = date(year, 1, 1)
    mondays = [date(year, 1, i) for i in range(1, 32) if date(year, 1, i).weekday() == 0]
    if len(mondays) >= 3: holidays.add(mondays[2])

    # Presidents Day - 3rd Monday of February
    mondays = [date(year, 2, i) for i in range(1, 29) if date(year, 2, i).weekday() == 0]
    if len(mondays) >= 3: holidays.add(mondays[2])

    # Good Friday (Easter - 2 days) - approximate via algorithm
    a = year % 19
    b, c = divmod(year, 100)
    d2, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d2 - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    easter = date(year, month, day)
    from datetime import timedelta
    good_friday = easter - timedelta(days=2)
    holidays.add(good_friday)

    # Memorial Day - last Monday of May
    mondays = [date(year, 5, i) for i in range(1, 32) if date(year, 5, i).weekday() == 0]
    if mondays: holidays.add(mondays[-1])

    # Juneteenth - June 19 (or observed)
    jt = date(year, 6, 19)
    if jt.weekday() == 5: jt = date(year, 6, 18)
    if jt.weekday() == 6: jt = date(year, 6, 20)
    if year >= 2022: holidays.add(jt)

    # Independence Day - July 4 (or observed)
    ind = date(year, 7, 4)
    if ind.weekday() == 5: ind = date(year, 7, 3)
    if ind.weekday() == 6: ind = date(year, 7, 5)
    holidays.add(ind)

    # Labor Day - 1st Monday of September
    mondays = [date(year, 9, i) for i in range(1, 31) if date(year, 9, i).weekday() == 0]
    if mondays: holidays.add(mondays[0])

    # Thanksgiving - 4th Thursday of November
    thursdays = [date(year, 11, i) for i in range(1, 31) if date(year, 11, i).weekday() == 3]
    if len(thursdays) >= 4: holidays.add(thursdays[3])

    # Christmas - Dec 25 (or observed)
    xmas = date(year, 12, 25)
    if xmas.weekday() == 5: xmas = date(year, 12, 24)
    if xmas.weekday() == 6: xmas = date(year, 12, 26)
    holidays.add(xmas)

    return holidays


def is_us_trading_day(d: Optional[date] = None) -> bool:
    """Return True if the given date (default today) is a US trading day."""
    if d is None:
        d = date.today()
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    return d not in _us_holidays(d.year)


def should_run() -> bool:
    """
    Check if analysis should run today.
    Respects TRADING_DAY_CHECK_ENABLED env var (default true).
    """
    enabled = os.getenv("TRADING_DAY_CHECK_ENABLED", "true").lower()
    if enabled in ("false", "0", "no"):
        return True
    return is_us_trading_day()
