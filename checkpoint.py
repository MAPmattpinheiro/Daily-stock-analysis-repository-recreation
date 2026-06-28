"""
Checkpoint / resume -- tracks which symbols have been analyzed in the current run.
If a run fails midway, re-running skips already-completed symbols.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)
def _checkpoint_file() -> Path:
    return Path(os.getenv("DATA_DIR", "data_store")) / "checkpoint.json"



def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _load() -> dict:
    if not _checkpoint_file().exists():
        return {}
    try:
        with open(_checkpoint_file()) as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict):
    _checkpoint_file().parent.mkdir(parents=True, exist_ok=True)
    with open(_checkpoint_file(), "w") as f:
        json.dump(data, f, indent=2)


def mark_done(symbol: str):
    data = _load()
    today = _today()
    data.setdefault(today, [])
    if symbol not in data[today]:
        data[today].append(symbol)
    _save(data)
    log.debug(f"Checkpoint: {symbol} marked done for {today}")


def is_done(symbol: str) -> bool:
    data = _load()
    return symbol in data.get(_today(), [])


def clear_today():
    data = _load()
    data.pop(_today(), None)
    _save(data)


def filter_remaining(symbols: list) -> list:
    """Return only symbols not yet completed today."""
    remaining = [s for s in symbols if not is_done(s)]
    skipped   = [s for s in symbols if is_done(s)]
    if skipped:
        log.info(f"Checkpoint: skipping already-done symbols: {skipped}")
    return remaining
