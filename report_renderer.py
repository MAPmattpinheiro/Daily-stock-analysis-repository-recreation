"""
Report renderer -- renders analysis results using Jinja2 templates.
Falls back to plain-text dashboard if templates are unavailable.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Any

log = logging.getLogger(__name__)

TEMPLATES_DIR = Path(os.getenv("REPORT_TEMPLATES_DIR", "templates"))
ENABLED = os.getenv("REPORT_RENDERER_ENABLED", "true").lower() in ("true", "1", "yes")

SIGNAL_ICONS = {"BUY": "🟢", "WATCH": "🟡", "SELL": "🔴"}


def signal_icon(signal: str) -> str:
    return SIGNAL_ICONS.get(signal.upper(), "⚪")


def render(results: List[Any], report_type: str = "full") -> str:
    if not ENABLED:
        return None  # caller falls back to plain text

    template_map = {
        "full":   "report_full.md.j2",
        "simple": "report_simple.md.j2",
        "brief":  "report_brief.md.j2",
    }
    template_file = TEMPLATES_DIR / template_map.get(report_type, "report_full.md.j2")

    if not template_file.exists():
        log.debug(f"Template not found: {template_file}")
        return None

    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape([]),
        )
        env.globals["signal_icon"] = signal_icon
        template = env.get_template(template_file.name)
        return template.render(
            results=results,
            date=datetime.now().strftime("%Y-%m-%d"),
            report_type=report_type,
        )
    except ImportError:
        log.debug("Jinja2 not installed — skipping template render.")
        return None
    except Exception as e:
        log.warning(f"Template render failed: {e}")
        return None
