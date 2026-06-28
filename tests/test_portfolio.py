"""Tests for portfolio tracker."""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["DATA_DIR"] = tempfile.mkdtemp()

import pytest
from portfolio.tracker import PortfolioTracker

def make_tracker():
    t = PortfolioTracker()
    t._data = {"trades": []}
    return t

def test_add_buy():
    t = make_tracker()
    trade = t.add_trade("AAPL", "Apple", "BUY", 10, 200.0)
    assert trade.symbol == "AAPL"
    assert trade.total == 2000.0

def test_position_after_buy():
    t = make_tracker()
    t.add_trade("AAPL", "Apple", "BUY", 10, 200.0)
    pos = t.get_position("AAPL")
    assert pos is not None
    assert pos.shares == 10

def test_sell_reduces_position():
    t = make_tracker()
    t.add_trade("AAPL", "Apple", "BUY", 10, 200.0)
    t.add_trade("AAPL", "Apple", "SELL", 4, 210.0)
    pos = t.get_position("AAPL")
    assert pos.shares == 6

def test_oversell_raises():
    t = make_tracker()
    t.add_trade("AAPL", "Apple", "BUY", 5, 200.0)
    with pytest.raises(ValueError):
        t.add_trade("AAPL", "Apple", "SELL", 10, 210.0)

def test_delete_trade():
    t = make_tracker()
    trade = t.add_trade("TSLA", "Tesla", "BUY", 5, 250.0)
    assert t.delete_trade(trade.id) is True
    assert t.delete_trade("nonexistent") is False

def test_avg_cost_calculation():
    t = make_tracker()
    t.add_trade("NVDA", "NVIDIA", "BUY", 10, 100.0)
    t.add_trade("NVDA", "NVIDIA", "BUY", 10, 200.0)
    pos = t.get_position("NVDA")
    assert pos.avg_cost == 150.0
