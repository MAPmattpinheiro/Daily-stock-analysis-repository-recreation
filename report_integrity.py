"""
Report integrity -- validates AI JSON output has all required fields.
Retries if missing, or fills placeholders so the pipeline never hard-fails.
"""

import json
import logging
import re
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

REQUIRED_FIELDS = ["signal", "score", "outlook", "conclusion",
                   "entry", "stop_loss", "target", "risk_alerts",
                   "catalysts", "checklist"]

PLACEHOLDERS = {
    "signal":      "WATCH",
    "score":       50,
    "outlook":     "Range-bound",
    "conclusion":  "Insufficient data for a firm conclusion at this time.",
    "entry":       None,
    "stop_loss":   None,
    "target":      None,
    "risk_alerts": ["Unable to determine risks — please review manually."],
    "catalysts":   ["Unable to determine catalysts — please review manually."],
    "checklist":   [
        "MA bullish alignment: Not Met",
        "Volume confirmation: Not Met",
        "Not extended from MA20: Not Met",
        "Positive news catalyst: Not Met",
        "Valuation reasonable: Not Met",
    ],
}


def _parse_json(raw: str) -> Optional[Dict]:
    text = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try extracting first {...} block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return None


def _missing_fields(data: Dict) -> list:
    return [f for f in REQUIRED_FIELDS if f not in data]


def validate_and_fix(raw: str, prompt: str, settings,
                     max_retries: int = 1) -> Dict[str, Any]:
    """
    Parse AI JSON response, validate required fields, retry if needed,
    fill placeholders for anything still missing.
    """
    from analysis.ai_caller import call_ai

    data = _parse_json(raw)

    if data is None:
        log.warning("AI response could not be parsed as JSON.")
        data = {}

    missing = _missing_fields(data)
    if missing and max_retries > 0:
        log.warning(f"Missing fields {missing} — retrying AI call...")
        try:
            retry_raw = call_ai(prompt, settings)
            retry_data = _parse_json(retry_raw)
            if retry_data:
                still_missing = _missing_fields(retry_data)
                if len(still_missing) < len(missing):
                    log.info(f"Retry improved result. Still missing: {still_missing}")
                    data = retry_data
                    missing = still_missing
        except Exception as e:
            log.warning(f"Retry failed: {e}")

    # Fill any remaining missing fields with placeholders
    for field in missing:
        data[field] = PLACEHOLDERS[field]
        log.debug(f"Placeholder used for: {field}")

    return data
