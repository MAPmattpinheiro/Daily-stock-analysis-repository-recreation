"""
Backtest — validates past AI predictions against actual next-day price moves.
For each saved analysis, fetches the actual closing price the following day
and compares direction (Bullish/Bearish/Range-bound) to what actually happened.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

import yfinance as yf

from storage.store import load_results, save_backtest, load_backtest

log = logging.getLogger(__name__)


@dataclass
class BacktestRecord:
    symbol: str
    analysis_date: str
    predicted_signal: str       # BUY | WATCH | SELL
    predicted_outlook: str      # Bullish | Bearish | Range-bound
    predicted_target: Optional[str]
    price_at_analysis: float
    price_next_day: Optional[float]
    actual_change_pct: Optional[float]
    direction_correct: Optional[bool]   # did prediction direction match?
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


def _next_trading_day_price(symbol: str, analysis_date_str: str) -> Optional[float]:
    """Fetch the closing price for the next trading day after analysis_date."""
    try:
        start = datetime.strptime(analysis_date_str, "%Y-%m-%d") + timedelta(days=1)
        end   = start + timedelta(days=7)  # fetch a week to catch weekends/holidays
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
        if hist.empty:
            return None
        return round(float(hist["Close"].iloc[0]), 4)
    except Exception as e:
        log.debug(f"Could not fetch next-day price for {symbol} after {analysis_date_str}: {e}")
        return None


def _direction_correct(signal: str, outlook: str, actual_change_pct: float) -> bool:
    """Returns True if predicted direction matched actual price movement."""
    if signal == "BUY" or outlook == "Bullish":
        return actual_change_pct > 0
    if signal == "SELL" or outlook == "Bearish":
        return actual_change_pct < 0
    # WATCH / Range-bound: consider correct if within ±1%
    return abs(actual_change_pct) <= 1.0


def run_backtest(days_back: int = 30, symbol: Optional[str] = None) -> List[BacktestRecord]:
    """
    Load saved analysis results and validate them against next-day actual prices.
    Returns a list of BacktestRecord objects.
    """
    results = load_results(symbol=symbol)
    records = []

    cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    for r in results:
        date_str = r.get("saved_at", "")[:10]
        if date_str < cutoff:
            continue

        sym            = r.get("symbol", "")
        price_analysis = r.get("price", 0.0)
        signal         = r.get("signal", "WATCH")
        outlook        = r.get("outlook", "Range-bound")
        target         = r.get("target")

        next_price = _next_trading_day_price(sym, date_str)

        if next_price and price_analysis:
            actual_change = round(((next_price - price_analysis) / price_analysis) * 100, 2)
            correct       = _direction_correct(signal, outlook, actual_change)
        else:
            actual_change = None
            correct       = None

        record = BacktestRecord(
            symbol             = sym,
            analysis_date      = date_str,
            predicted_signal   = signal,
            predicted_outlook  = outlook,
            predicted_target   = target,
            price_at_analysis  = price_analysis,
            price_next_day     = next_price,
            actual_change_pct  = actual_change,
            direction_correct  = correct,
            note               = "1-day window validation",
        )
        records.append(record)
        save_backtest(record.to_dict())

    return records


def backtest_summary(records: List[BacktestRecord]) -> str:
    """Format a human-readable backtest summary."""
    if not records:
        return "No backtest records available."

    validated  = [r for r in records if r.direction_correct is not None]
    correct    = [r for r in validated if r.direction_correct]
    accuracy   = round(len(correct) / len(validated) * 100, 1) if validated else 0

    lines = [
        "📊 AI Backtest Summary (1-Day Window)",
        f"  Records analyzed: {len(records)}",
        f"  Validated:        {len(validated)}",
        f"  Correct direction: {len(correct)} / {len(validated)}",
        f"  Accuracy:         {accuracy}%",
        "",
        "  Per-stock breakdown:",
    ]

    by_symbol: Dict[str, List[BacktestRecord]] = {}
    for r in validated:
        by_symbol.setdefault(r.symbol, []).append(r)

    for sym, recs in sorted(by_symbol.items()):
        sym_correct  = sum(1 for r in recs if r.direction_correct)
        sym_accuracy = round(sym_correct / len(recs) * 100, 1)
        lines.append(f"    {sym:<8} {sym_correct}/{len(recs)} correct  ({sym_accuracy}%)")

    return "\n".join(lines)
