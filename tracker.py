"""
Portfolio tracker -- log trades, track positions, P&L.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import os

log = logging.getLogger(__name__)
def _portfolio_file() -> Path:
    return Path(os.getenv("DATA_DIR", "data_store")) / "portfolio.json"


@dataclass
class Trade:
    id: str
    symbol: str
    name: str
    action: str
    shares: float
    price: float
    date: str
    notes: str = ""

    @property
    def total(self) -> float:
        return round(self.shares * self.price, 2)

    def to_dict(self):
        return self.__dict__


@dataclass
class Position:
    symbol: str
    name: str
    shares: float
    avg_cost: float
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0

    def to_dict(self):
        return self.__dict__


def _load_raw() -> Dict:
    if not _portfolio_file().exists():
        return {"trades": []}
    try:
        with open(_portfolio_file()) as f:
            return json.load(f)
    except Exception:
        return {"trades": []}


def _save_raw(data: Dict):
    _portfolio_file().parent.mkdir(parents=True, exist_ok=True)
    with open(_portfolio_file(), "w") as f:
        json.dump(data, f, indent=2)


class PortfolioTracker:
    def __init__(self):
        self._data = _load_raw()

    def _save(self):
        _save_raw(self._data)

    def add_trade(self, symbol: str, name: str, action: str,
                  shares: float, price: float, notes: str = "") -> Trade:
        symbol = symbol.upper()
        action = action.upper()
        if action == "SELL":
            pos = self.get_position(symbol)
            avail = pos.shares if pos else 0
            if avail < shares:
                raise ValueError(f"Insufficient shares: have {avail}, selling {shares}")
        trade = Trade(
            id=str(uuid.uuid4())[:8],
            symbol=symbol, name=name, action=action,
            shares=shares, price=price,
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            notes=notes,
        )
        self._data.setdefault("trades", []).append(trade.to_dict())
        self._save()
        return trade

    def delete_trade(self, trade_id: str) -> bool:
        before = len(self._data.get("trades", []))
        self._data["trades"] = [t for t in self._data.get("trades", []) if t["id"] != trade_id]
        if len(self._data["trades"]) < before:
            self._save()
            return True
        return False

    def get_trades(self, symbol: Optional[str] = None) -> List[Trade]:
        trades = [Trade(**t) for t in self._data.get("trades", [])]
        if symbol:
            trades = [t for t in trades if t.symbol == symbol.upper()]
        return sorted(trades, key=lambda t: t.date, reverse=True)

    def get_position(self, symbol: str) -> Optional[Position]:
        return next((p for p in self.get_all_positions() if p.symbol == symbol.upper()), None)

    def get_all_positions(self) -> List[Position]:
        holdings: Dict[str, Dict] = {}
        for t in sorted(self._data.get("trades", []), key=lambda x: x["date"]):
            sym = t["symbol"]
            if sym not in holdings:
                holdings[sym] = {"name": t["name"], "shares": 0.0, "cost_basis": 0.0}
            if t["action"] == "BUY":
                total_cost = holdings[sym]["cost_basis"] * holdings[sym]["shares"] + t["price"] * t["shares"]
                holdings[sym]["shares"] += t["shares"]
                holdings[sym]["cost_basis"] = total_cost / holdings[sym]["shares"] if holdings[sym]["shares"] else 0
            elif t["action"] == "SELL":
                holdings[sym]["shares"] = max(0, holdings[sym]["shares"] - t["shares"])
        positions = []
        for sym, data in holdings.items():
            if data["shares"] > 0:
                positions.append(Position(
                    symbol=sym, name=data["name"],
                    shares=round(data["shares"], 4),
                    avg_cost=round(data["cost_basis"], 4),
                ))
        return positions

    def update_prices(self) -> List[Position]:
        import yfinance as yf
        positions = self.get_all_positions()
        for pos in positions:
            try:
                info = yf.Ticker(pos.symbol).info or {}
                price = info.get("currentPrice") or info.get("regularMarketPrice") or pos.avg_cost
                pos.current_price = round(float(price), 4)
                pos.market_value = round(pos.shares * pos.current_price, 2)
                pos.unrealized_pnl = round(pos.market_value - pos.shares * pos.avg_cost, 2)
                pos.unrealized_pnl_pct = round((pos.current_price - pos.avg_cost) / pos.avg_cost * 100, 2) if pos.avg_cost else 0.0
            except Exception as e:
                log.debug(f"Price update failed for {pos.symbol}: {e}")
        return positions

    def summary(self) -> Dict[str, Any]:
        positions = self.update_prices()
        total_value = sum(p.market_value for p in positions)
        total_cost  = sum(p.shares * p.avg_cost for p in positions)
        total_pnl   = round(total_value - total_cost, 2)
        return {
            "positions": [p.to_dict() for p in positions],
            "total_market_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_unrealized_pnl": total_pnl,
            "total_unrealized_pnl_pct": round(total_pnl / total_cost * 100, 2) if total_cost else 0.0,
            "position_count": len(positions),
        }
