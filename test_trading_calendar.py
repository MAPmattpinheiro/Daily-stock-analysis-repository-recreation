"""Tests for trading_calendar module."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import date
from trading_calendar import is_us_trading_day, _us_holidays

def test_weekends_not_trading():
    assert not is_us_trading_day(date(2026, 6, 27))  # Saturday
    assert not is_us_trading_day(date(2026, 6, 28))  # Sunday

def test_weekday_is_trading():
    assert is_us_trading_day(date(2026, 6, 26))  # Friday

def test_new_years_not_trading():
    assert not is_us_trading_day(date(2026, 1, 1))

def test_christmas_not_trading():
    assert not is_us_trading_day(date(2026, 12, 25))

def test_holidays_count():
    holidays = _us_holidays(2026)
    assert 8 <= len(holidays) <= 12  # NYSE has ~9 holidays per year

def test_july_4_not_trading():
    holidays = _us_holidays(2026)
    assert date(2026, 7, 4) in holidays or date(2026, 7, 3) in holidays or date(2026, 7, 6) in holidays
