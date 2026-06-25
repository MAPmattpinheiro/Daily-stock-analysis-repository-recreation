"""
Market Review — daily overview of US market indices, breadth, and sector performance.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import datetime

import yfinance as yf

log = logging.getLogger(__name__)

# Major indices
INDICES = [
    ("S&P 500",      "^GSPC"),
    ("Nasdaq",       "^IXIC"),
    ("Dow Jones",    "^DJI"),
    ("Russell 2000", "^RUT"),
    ("VIX",          "^VIX"),
]

# Sector ETFs (SPDR)
SECTOR_ETFS = [
    ("Technology",        "XLK"),
    ("Healthcare",        "XLV"),
    ("Financials",        "XLF"),
    ("Consumer Discret.", "XLY"),
    ("Consumer Staples",  "XLP"),
    ("Energy",            "XLE"),
    ("Industrials",       "XLI"),
    ("Materials",         "XLB"),
    ("Real Estate",       "XLRE"),
    ("Utilities",         "XLU"),
    ("Communication",     "XLC"),
]


@dataclass
class IndexData:
    name: str
    symbol: str
    price: float
    change_pct: float


@dataclass
class SectorData:
    name: str
    symbol: str
    change_pct: float


@dataclass
class MarketReview:
    date: str
    indices: List[IndexData] = field(default_factory=list)
    sectors: List[SectorData] = field(default_factory=list)
    market_sentiment: str = "Neutral"   # Bullish | Bearish | Neutral
    vix: Optional[float] = None
    top_sectors: List[str] = field(default_factory=list)
    bottom_sectors: List[str] = field(default_factory=list)
    summary: str = ""

    def to_text(self) -> str:
        lines = [
            f"🎯 {self.date} — US Market Review",
            "",
            "📊 Major Indices",
        ]
        for idx in self.indices:
            if idx.symbol == "^VIX":
                lines.append(f"  {'📉' if idx.price > 20 else '📈'} {idx.name}: {idx.price:.2f}  (fear gauge {'HIGH' if idx.price > 25 else 'ELEVATED' if idx.price > 20 else 'LOW'})")
            else:
                arrow = "🟢" if idx.change_pct >= 0 else "🔴"
                lines.append(f"  {arrow} {idx.name}: {idx.price:,.2f}  ({idx.change_pct:+.2f}%)")

        if self.sectors:
            lines += ["", "🔥 Sector Performance"]
            sorted_sectors = sorted(self.sectors, key=lambda s: s.change_pct, reverse=True)
            for s in sorted_sectors:
                arrow = "🟢" if s.change_pct >= 0 else "🔴"
                lines.append(f"  {arrow} {s.name:<22} {s.change_pct:+.2f}%")

            if self.top_sectors:
                lines.append(f"\n  Leading:  {', '.join(self.top_sectors[:3])}")
            if self.bottom_sectors:
                lines.append(f"  Lagging:  {', '.join(self.bottom_sectors[:3])}")

        lines += [
            "",
            f"🧭 Overall Sentiment: {self.market_sentiment}",
        ]
        if self.vix:
            lines.append(f"   VIX: {self.vix:.2f}")
        if self.summary:
            lines += ["", f"📝 {self.summary}"]

        return "\n".join(lines)

    def to_dict(self):
        return {
            "date":             self.date,
            "market_sentiment": self.market_sentiment,
            "vix":              self.vix,
            "top_sectors":      self.top_sectors,
            "bottom_sectors":   self.bottom_sectors,
            "summary":          self.summary,
            "indices":  [i.__dict__ for i in self.indices],
            "sectors":  [s.__dict__ for s in self.sectors],
        }


def _fetch_change(symbol: str) -> Tuple[float, float]:
    """Returns (price, change_pct)."""
    try:
        ticker = yf.Ticker(symbol)
        info   = ticker.info or {}
        price  = info.get("regularMarketPrice") or info.get("currentPrice") or 0.0
        prev   = info.get("regularMarketPreviousClose") or info.get("previousClose") or price
        pct    = round(((price - prev) / prev) * 100, 2) if prev else 0.0
        return round(float(price), 2), pct
    except Exception as e:
        log.debug(f"Could not fetch {symbol}: {e}")
        return 0.0, 0.0


def _determine_sentiment(indices: List[IndexData], vix: Optional[float]) -> str:
    advancing = sum(1 for i in indices if i.symbol != "^VIX" and i.change_pct > 0)
    total     = sum(1 for i in indices if i.symbol != "^VIX")
    if vix and vix > 25:
        return "Bearish (High Fear)"
    if advancing >= total * 0.75:
        return "Bullish"
    if advancing <= total * 0.25:
        return "Bearish"
    return "Neutral"


def fetch_market_review() -> MarketReview:
    log.info("Fetching market review...")
    date_str = datetime.now().strftime("%Y-%m-%d")
    review   = MarketReview(date=date_str)

    # Indices
    for name, symbol in INDICES:
        price, pct = _fetch_change(symbol)
        idx = IndexData(name=name, symbol=symbol, price=price, change_pct=pct)
        review.indices.append(idx)
        if symbol == "^VIX":
            review.vix = price

    # Sectors
    for name, symbol in SECTOR_ETFS:
        _, pct = _fetch_change(symbol)
        review.sectors.append(SectorData(name=name, symbol=symbol, change_pct=pct))

    # Sort sectors
    sorted_sectors = sorted(review.sectors, key=lambda s: s.change_pct, reverse=True)
    review.top_sectors    = [s.name for s in sorted_sectors[:3]]
    review.bottom_sectors = [s.name for s in sorted_sectors[-3:]]

    review.market_sentiment = _determine_sentiment(review.indices, review.vix)

    # Brief summary
    sp500 = next((i for i in review.indices if i.symbol == "^GSPC"), None)
    if sp500:
        direction = "gained" if sp500.change_pct >= 0 else "fell"
        review.summary = (
            f"S&P 500 {direction} {abs(sp500.change_pct):.2f}% today. "
            f"Leading sectors: {', '.join(review.top_sectors[:2])}. "
            f"Lagging: {', '.join(review.bottom_sectors[:2])}."
        )

    return review
