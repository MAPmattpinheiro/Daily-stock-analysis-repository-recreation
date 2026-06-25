"""
Storage — persists analysis results, backtest records, and settings to disk (JSON).
All data lives in a `data/` directory next to the project root.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).parent.parent / "data_store"))


def _ensure(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def _results_dir() -> Path:
    p = DATA_DIR / "results"
    _ensure(p)
    return p


def _backtest_dir() -> Path:
    p = DATA_DIR / "backtest"
    _ensure(p)
    return p


def _settings_file() -> Path:
    _ensure(DATA_DIR)
    return DATA_DIR / "settings.json"


# ── Analysis results ──────────────────────────────────────────────────────────

def save_result(result_dict: Dict[str, Any]):
    """Save a single stock analysis result keyed by symbol + date."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    symbol   = result_dict.get("symbol", "UNKNOWN").upper()
    path     = _results_dir() / f"{date_str}_{symbol}.json"
    with open(path, "w") as f:
        json.dump({**result_dict, "saved_at": datetime.now().isoformat()}, f, indent=2)
    log.debug(f"Saved result: {path.name}")


def load_results(date_str: Optional[str] = None, symbol: Optional[str] = None) -> List[Dict]:
    """Load results, optionally filtered by date (YYYY-MM-DD) and/or symbol."""
    results = []
    for path in sorted(_results_dir().glob("*.json"), reverse=True):
        name = path.stem  # e.g. 2026-06-25_AAPL
        if date_str and not name.startswith(date_str):
            continue
        if symbol and not name.endswith(symbol.upper()):
            continue
        try:
            with open(path) as f:
                results.append(json.load(f))
        except Exception as e:
            log.warning(f"Could not read {path}: {e}")
    return results


def load_latest_results() -> List[Dict]:
    """Load all results from the most recent analysis date."""
    files = sorted(_results_dir().glob("*.json"), reverse=True)
    if not files:
        return []
    latest_date = files[0].stem[:10]
    return load_results(date_str=latest_date)


def list_history_dates() -> List[str]:
    """Return sorted list of unique dates that have saved results."""
    dates = set()
    for path in _results_dir().glob("*.json"):
        dates.add(path.stem[:10])
    return sorted(dates, reverse=True)


def delete_result(date_str: str, symbol: str) -> bool:
    path = _results_dir() / f"{date_str}_{symbol.upper()}.json"
    if path.exists():
        path.unlink()
        return True
    return False


# ── Backtest records ──────────────────────────────────────────────────────────

def save_backtest(record: Dict[str, Any]):
    """Save a backtest comparison record."""
    date_str = record.get("analysis_date", datetime.now().strftime("%Y-%m-%d"))
    symbol   = record.get("symbol", "UNKNOWN").upper()
    path     = _backtest_dir() / f"{date_str}_{symbol}.json"
    with open(path, "w") as f:
        json.dump(record, f, indent=2)
    log.debug(f"Saved backtest: {path.name}")


def load_backtest(symbol: Optional[str] = None) -> List[Dict]:
    results = []
    for path in sorted(_backtest_dir().glob("*.json"), reverse=True):
        if symbol and symbol.upper() not in path.stem:
            continue
        try:
            with open(path) as f:
                results.append(json.load(f))
        except Exception as e:
            log.warning(f"Could not read {path}: {e}")
    return results


# ── Settings persistence ──────────────────────────────────────────────────────

def save_settings(data: Dict[str, Any]):
    with open(_settings_file(), "w") as f:
        json.dump(data, f, indent=2)


def load_settings() -> Dict[str, Any]:
    path = _settings_file()
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}
