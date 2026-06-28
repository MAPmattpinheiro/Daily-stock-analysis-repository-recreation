"""
Fundamentals — fetches valuation, growth, earnings, and dividend data via yfinance.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

import yfinance as yf

log = logging.getLogger(__name__)


@dataclass
class Fundamentals:
    symbol: str

    # Valuation
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    price_to_book: Optional[float] = None
    price_to_sales: Optional[float] = None
    enterprise_to_ebitda: Optional[float] = None

    # Growth & Profitability
    revenue_ttm: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None       # %
    earnings_growth_yoy: Optional[float] = None      # %
    profit_margin: Optional[float] = None            # %
    return_on_equity: Optional[float] = None         # %
    debt_to_equity: Optional[float] = None

    # Earnings
    eps_ttm: Optional[float] = None
    eps_forward: Optional[float] = None
    next_earnings_date: Optional[str] = None

    # Dividends
    dividend_yield: Optional[float] = None           # %
    dividend_per_share: Optional[float] = None
    payout_ratio: Optional[float] = None             # %

    # Analyst
    analyst_target_price: Optional[float] = None
    analyst_recommendation: Optional[str] = None
    number_of_analysts: Optional[int] = None

    # Summary text for AI prompt
    def to_prompt_text(self) -> str:
        lines = ["## Fundamental Data"]

        def add(label, val, fmt="{}", suffix=""):
            if val is not None:
                try:
                    lines.append(f"  {label}: {fmt.format(val)}{suffix}")
                except Exception:
                    pass

        add("P/E (TTM)",           self.pe_ratio,              "{:.1f}x")
        add("Forward P/E",         self.forward_pe,            "{:.1f}x")
        add("Price/Book",          self.price_to_book,         "{:.2f}x")
        add("Price/Sales",         self.price_to_sales,        "{:.2f}x")
        add("EV/EBITDA",           self.enterprise_to_ebitda,  "{:.1f}x")
        add("Revenue (TTM)",       self.revenue_ttm,           "${:,.0f}")
        add("Revenue Growth YoY",  self.revenue_growth_yoy,    "{:+.1f}", "%")
        add("Earnings Growth YoY", self.earnings_growth_yoy,   "{:+.1f}", "%")
        add("Profit Margin",       self.profit_margin,         "{:.1f}", "%")
        add("Return on Equity",    self.return_on_equity,      "{:.1f}", "%")
        add("Debt/Equity",         self.debt_to_equity,        "{:.2f}x")
        add("EPS (TTM)",           self.eps_ttm,               "${:.2f}")
        add("EPS (Forward)",       self.eps_forward,           "${:.2f}")
        add("Next Earnings",       self.next_earnings_date)
        add("Dividend Yield",      self.dividend_yield,        "{:.2f}", "%")
        add("Dividend/Share",      self.dividend_per_share,    "${:.2f}")
        add("Payout Ratio",        self.payout_ratio,          "{:.1f}", "%")
        add("Analyst Target",      self.analyst_target_price,  "${:.2f}")
        add("Analyst Rating",      self.analyst_recommendation)
        add("# Analysts",          self.number_of_analysts)

        return "\n".join(lines) if len(lines) > 1 else "  No fundamental data available."

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


def _pct(val) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        return round(f * 100, 2) if abs(f) < 10 else round(f, 2)
    except Exception:
        return None


def fetch_fundamentals(symbol: str) -> Fundamentals:
    result = Fundamentals(symbol=symbol.upper())
    try:
        ticker = yf.Ticker(symbol)
        info   = ticker.info or {}

        result.pe_ratio              = info.get("trailingPE")
        result.forward_pe            = info.get("forwardPE")
        result.price_to_book         = info.get("priceToBook")
        result.price_to_sales        = info.get("priceToSalesTrailing12Months")
        result.enterprise_to_ebitda  = info.get("enterpriseToEbitda")

        result.revenue_ttm           = info.get("totalRevenue")
        result.revenue_growth_yoy    = _pct(info.get("revenueGrowth"))
        result.earnings_growth_yoy   = _pct(info.get("earningsGrowth"))
        result.profit_margin         = _pct(info.get("profitMargins"))
        result.return_on_equity      = _pct(info.get("returnOnEquity"))
        result.debt_to_equity        = info.get("debtToEquity")

        result.eps_ttm               = info.get("trailingEps")
        result.eps_forward           = info.get("forwardEps")

        # Next earnings date
        try:
            cal = ticker.calendar
            if cal is not None and not cal.empty:
                ed = cal.get("Earnings Date")
                if ed is not None and len(ed) > 0:
                    result.next_earnings_date = str(ed.iloc[0].date())
        except Exception:
            pass

        result.dividend_yield        = _pct(info.get("dividendYield"))
        result.dividend_per_share    = info.get("dividendRate")
        result.payout_ratio          = _pct(info.get("payoutRatio"))

        result.analyst_target_price  = info.get("targetMeanPrice")
        result.analyst_recommendation = info.get("recommendationKey", "").replace("_", " ").title() or None
        result.number_of_analysts    = info.get("numberOfAnalystOpinions")

    except Exception as e:
        log.warning(f"Fundamentals fetch failed for {symbol}: {e}")

    return result
