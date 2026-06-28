"""
Stock Analyzer -- fetches data, calls AI with fallback, returns structured results.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

from config.settings import Settings
from data.market import fetch_quote, Quote
from data.news import fetch_news, NewsItem
from fundamentals.fetcher import fetch_fundamentals, Fundamentals
from analysis.ai_caller import call_ai

log = logging.getLogger(__name__)


@dataclass
class StockResult:
    symbol: str
    name: str
    price: float
    change_pct: float
    signal: str           # BUY | WATCH | SELL
    score: int            # 0-100
    outlook: str          # Bullish | Bearish | Range-bound
    conclusion: str
    entry: Optional[str]
    stop_loss: Optional[str]
    target: Optional[str]
    risk_alerts: List[str] = field(default_factory=list)
    catalysts: List[str] = field(default_factory=list)
    checklist: List[str] = field(default_factory=list)
    news_headlines: List[str] = field(default_factory=list)
    sector: Optional[str] = None
    industry: Optional[str] = None
    raw_report: str = ""

    def to_dict(self):
        return self.__dict__


def _build_prompt(quote: Quote, news: List[NewsItem], fund: Fundamentals, settings: Settings) -> str:
    ma_lines = []
    for label, val in [("MA5", quote.ma5), ("MA10", quote.ma10), ("MA20", quote.ma20), ("MA50", quote.ma50)]:
        if val:
            ma_lines.append(f"  {label}: {val}")

    news_lines = [f"  - [{n.source}] {n.title}: {n.snippet[:150]}" for n in news[:5]]
    deviation_warning = ""
    if abs(quote.deviation_pct) > settings.bias_threshold:
        deviation_warning = (
            f"\n  WARNING: Price is {quote.deviation_pct:+.1f}% from MA20 -- "
            f"{'extended above, caution chasing highs' if quote.deviation_pct > 0 else 'extended below MA20'}."
        )

    return f"""You are a professional US equity analyst. Analyze the following stock and return a structured decision report.

## Market Data: {quote.symbol} ({quote.name})
- Price: ${quote.price}  |  Change: {quote.change_pct:+.2f}%
- 52-Week Range: ${quote.week_52_low} - ${quote.week_52_high}
- Volume: {quote.volume:,}  (Avg: {quote.avg_volume:,})
- Market Cap: {'${:,.0f}'.format(quote.market_cap) if quote.market_cap else 'N/A'}
- Sector: {quote.sector or 'N/A'}  |  Industry: {quote.industry or 'N/A'}

## Moving Averages
{chr(10).join(ma_lines) if ma_lines else '  Insufficient history'}
- Bullish Alignment (MA5>MA10>MA20): {'Yes' if quote.ma_bullish_alignment else 'No'}
- Deviation from MA20: {quote.deviation_pct:+.1f}%{deviation_warning}

{fund.to_prompt_text()}

## Recent News
{chr(10).join(news_lines) if news_lines else '  No recent news available'}

---
Return ONLY a JSON object (no markdown, no extra text):
{{
  "signal": "BUY" | "WATCH" | "SELL",
  "score": <integer 0-100>,
  "outlook": "Bullish" | "Bearish" | "Range-bound",
  "conclusion": "<one sentence key thesis>",
  "entry": "<price range or null>",
  "stop_loss": "<price or null>",
  "target": "<price range or null>",
  "risk_alerts": ["<risk 1>", "<risk 2>"],
  "catalysts": ["<catalyst 1>", "<catalyst 2>"],
  "checklist": [
    "MA bullish alignment: Met | Caution | Not Met",
    "Volume confirmation: Met | Caution | Not Met",
    "Not extended from MA20: Met | Caution | Not Met",
    "Positive news catalyst: Met | Caution | Not Met",
    "Valuation reasonable: Met | Caution | Not Met"
  ]
}}
Be concise and data-driven. Do not invent facts not in the data above.
"""


def _parse(raw: str, quote: Quote, news: List[NewsItem]) -> StockResult:
    text = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        log.warning(f"Could not parse AI JSON for {quote.symbol}.")
        data = {}

    return StockResult(
        symbol     = quote.symbol,
        name       = quote.name,
        price      = quote.price,
        change_pct = quote.change_pct,
        signal     = data.get("signal", "WATCH"),
        score      = int(data.get("score", 50)),
        outlook    = data.get("outlook", "Range-bound"),
        conclusion = data.get("conclusion", "Insufficient data for a firm conclusion."),
        entry      = data.get("entry"),
        stop_loss  = data.get("stop_loss"),
        target     = data.get("target"),
        risk_alerts    = data.get("risk_alerts", []),
        catalysts      = data.get("catalysts", []),
        checklist      = data.get("checklist", []),
        news_headlines = [n.title for n in news[:3]],
        sector         = quote.sector,
        industry       = quote.industry,
        raw_report     = raw,
    )


class StockAnalyzer:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def analyze(self, symbol: str) -> StockResult:
        quote  = fetch_quote(symbol)
        news   = fetch_news(symbol, quote.name, self.settings)
        fund   = fetch_fundamentals(symbol)
        prompt = _build_prompt(quote, news, fund, self.settings)
        raw    = call_ai(prompt, self.settings)
        return _parse(raw, quote, news)

    def build_dashboard(self, results: List[StockResult]) -> str:
        now   = datetime.now().strftime("%Y-%m-%d %H:%M")
        icons = {"BUY": "🟢", "WATCH": "🟡", "SELL": "🔴"}
        buys  = sum(1 for r in results if r.signal == "BUY")
        watch = sum(1 for r in results if r.signal == "WATCH")
        sells = sum(1 for r in results if r.signal == "SELL")

        lines = [
            f"🎯 {now} -- Daily Stock Decision Dashboard",
            f"Analyzed {len(results)} stock(s)  |  🟢 Buy: {buys}  🟡 Watch: {watch}  🔴 Sell: {sells}",
            "",
            "📊 Summary",
        ]
        for r in results:
            icon = icons.get(r.signal, "⚪")
            lines.append(f"  {icon} {r.symbol} ({r.name})  |  {r.signal}  |  Score: {r.score}  |  {r.outlook}")

        lines.append("")

        for r in results:
            icon = icons.get(r.signal, "⚪")
            lines += [
                "─" * 52,
                f"{icon} {r.symbol} -- {r.name}",
                f"   Price: ${r.price}  ({r.change_pct:+.2f}% today)",
                f"   Signal: {r.signal}  |  Score: {r.score}/100  |  {r.outlook}",
                f"   💡 {r.conclusion}",
            ]
            if r.entry:
                lines.append(f"   Entry: {r.entry}  |  Stop: {r.stop_loss}  |  Target: {r.target}")
            if r.risk_alerts:
                lines.append("   🚨 Risks:")
                for i, risk in enumerate(r.risk_alerts, 1):
                    lines.append(f"      {i}. {risk}")
            if r.catalysts:
                lines.append("   ✨ Catalysts:")
                for i, cat in enumerate(r.catalysts, 1):
                    lines.append(f"      {i}. {cat}")
            if r.checklist:
                lines.append("   ✅ Checklist:")
                for item in r.checklist:
                    lines.append(f"      • {item}")
            if r.news_headlines:
                lines.append("   📰 Recent News:")
                for h in r.news_headlines:
                    lines.append(f"      • {h}")
            lines.append("")

        lines.append("⚠️  For informational purposes only. Not investment advice.")
        return "\n".join(lines)
