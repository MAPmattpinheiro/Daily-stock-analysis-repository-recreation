"""Tests for checkpoint/resume module."""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["DATA_DIR"] = tempfile.mkdtemp()

from checkpoint import mark_done, is_done, filter_remaining, clear_today

def test_mark_and_check():
    clear_today()
    assert not is_done("AAPL")
    mark_done("AAPL")
    assert is_done("AAPL")
    assert not is_done("TSLA")

def test_filter_remaining():
    clear_today()
    mark_done("AAPL")
    remaining = filter_remaining(["AAPL", "TSLA", "NVDA"])
    assert "AAPL" not in remaining
    assert "TSLA" in remaining
    assert "NVDA" in remaining

def test_clear_today():
    mark_done("MSFT")
    clear_today()
    assert not is_done("MSFT")
