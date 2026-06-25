"""
AI caller with multi-model fallback.
Tries providers in priority order: Gemini → Anthropic → OpenAI.
If the primary fails, it automatically retries with the next available provider.
"""

import logging
import time
from typing import Optional

from config.settings import Settings

log = logging.getLogger(__name__)


def _call_openai(prompt: str, settings: Settings) -> str:
    from openai import OpenAI
    kwargs = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    client = OpenAI(**kwargs)
    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1000,
    )
    return resp.choices[0].message.content.strip()


def _call_anthropic(prompt: str, settings: Settings) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    resp = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


def _call_gemini(prompt: str, settings: Settings) -> str:
    import google.generativeai as genai
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    resp = model.generate_content(prompt)
    return resp.text.strip()


# Provider registry — ordered by priority
_PROVIDERS = [
    ("gemini",    lambda s: bool(s.gemini_api_key),    _call_gemini),
    ("anthropic", lambda s: bool(s.anthropic_api_key), _call_anthropic),
    ("openai",    lambda s: bool(s.openai_api_key),    _call_openai),
]


def call_ai(prompt: str, settings: Settings, retries: int = 1) -> str:
    """
    Call AI with automatic fallback across all configured providers.
    Tries Gemini first, then Anthropic, then OpenAI.
    Each provider gets `retries` attempts before moving to the next.
    """
    available = [(name, fn) for name, check, fn in _PROVIDERS if check(settings)]

    if not available:
        raise RuntimeError(
            "No AI provider configured. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY."
        )

    last_error: Optional[Exception] = None

    for name, fn in available:
        for attempt in range(1, retries + 2):  # at least 1 attempt
            try:
                log.debug(f"Calling {name} (attempt {attempt})...")
                result = fn(prompt, settings)
                if attempt > 1 or name != available[0][0]:
                    log.info(f"AI call succeeded via {name} (attempt {attempt})")
                return result
            except Exception as e:
                last_error = e
                log.warning(f"AI provider '{name}' attempt {attempt} failed: {e}")
                if attempt <= retries:
                    time.sleep(2 ** attempt)  # exponential backoff

        log.warning(f"All attempts exhausted for '{name}', trying next provider...")

    raise RuntimeError(f"All AI providers failed. Last error: {last_error}")
