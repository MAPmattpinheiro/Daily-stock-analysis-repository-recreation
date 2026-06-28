"""
Markdown-to-image converter.
Converts a Markdown string to a PNG image using wkhtmltoimage (if installed)
or a pure-Python fallback. Used by notification channels that support images.
"""

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

def _enabled_channels():
    return [c.strip() for c in os.getenv("MARKDOWN_TO_IMAGE_CHANNELS", "").split(",") if c.strip()]
MAX_CHARS = int(os.getenv("MARKDOWN_TO_IMAGE_MAX_CHARS", "15000"))


def channel_wants_image(channel: str) -> bool:
    return channel.lower() in _enabled_channels()


def _md_to_html(markdown_text: str) -> str:
    css = """
    body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f1117;
           color: #e2e8f0; padding: 2rem; max-width: 800px; margin: 0 auto; }
    h1, h2, h3 { color: #a5b4fc; }
    code { background: #1e2130; padding: 2px 6px; border-radius: 4px; }
    pre  { background: #1e2130; padding: 1rem; border-radius: 8px; overflow-x: auto; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #2a2d3a; padding: 8px 12px; text-align: left; }
    th { background: #1a1d27; }
    hr { border-color: #2a2d3a; }
    .green { color: #22c55e; } .red { color: #ef4444; } .yellow { color: #eab308; }
    """
    try:
        import markdown
        body = markdown.markdown(markdown_text, extensions=["tables", "fenced_code"])
    except ImportError:
        # Basic fallback: wrap in <pre>
        body = f"<pre>{markdown_text}</pre>"
    return f"<!DOCTYPE html><html><head><style>{css}</style></head><body>{body}</body></html>"


def convert_to_image(markdown_text: str) -> Optional[bytes]:
    """Convert markdown text to PNG bytes. Returns None if conversion fails."""
    if len(markdown_text) > MAX_CHARS:
        log.debug(f"Text too long ({len(markdown_text)} chars), skipping image conversion.")
        return None

    html = _md_to_html(markdown_text)

    # Try wkhtmltoimage
    try:
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
            f.write(html)
            html_path = f.name
        out_path = html_path.replace(".html", ".png")
        result = subprocess.run(
            ["wkhtmltoimage", "--quiet", "--width", "900", html_path, out_path],
            capture_output=True, timeout=30,
        )
        if result.returncode == 0 and Path(out_path).exists():
            with open(out_path, "rb") as f:
                data = f.read()
            os.unlink(html_path)
            os.unlink(out_path)
            return data
        os.unlink(html_path)
    except FileNotFoundError:
        log.debug("wkhtmltoimage not found.")
    except Exception as e:
        log.debug(f"wkhtmltoimage failed: {e}")

    return None
