"""
Agent Q&A -- multi-turn conversational stock analysis.
Maintains conversation history and enriches answers with live market data.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

from config.settings import Settings
from analysis.ai_caller import call_ai
from data.market import fetch_quote
from data.news import fetch_news
from fundamentals.fetcher import fetch_fundamentals

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert US equity analyst and trading strategist.
You have access to real-time market data injected into each user message.
Answer questions clearly and concisely. When asked about a specific stock, use the data provided.
Always note that your analysis is for informational purposes only, not investment advice.
Keep responses focused and under 400 words unless a detailed breakdown is explicitly requested."""

SKIP_WORDS = {
    "I", "A", "AN", "THE", "IN", "ON", "AT", "BY", "OR", "AND", "FOR",
    "IS", "IT", "BE", "DO", "TO", "UP", "MY", "WE", "US", "ME", "GO",
    "SO", "IF", "AS", "VS", "AI", "ETF", "USA", "USD", "GDP", "CEO",
    "IPO", "PE", "EV", "MA", "BUY", "SELL",
}


@dataclass
class Message:
    role: str       # "user" | "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Session:
    session_id: str
    messages: List[Message] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "messages": [m.__dict__ for m in self.messages],
        }


_sessions: Dict[str, Session] = {}


def get_or_create_session(session_id: str) -> Session:
    if session_id not in _sessions:
        _sessions[session_id] = Session(session_id=session_id)
    return _sessions[session_id]


def list_sessions() -> List[Dict]:
    return [
        {
            "session_id": s.session_id,
            "created_at": s.created_at,
            "message_count": len(s.messages),
        }
        for s in _sessions.values()
    ]


def delete_session(session_id: str) -> bool:
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False


def _extract_symbols(text: str) -> List[str]:
    tokens = re.findall(r'\b[A-Z]{1,5}\b', text)
    return [t for t in set(tokens) if t not in SKIP_WORDS and len(t) >= 2]


def _fetch_context(symbols: List[str], settings: Settings) -> str:
    symbols = symbols[:3]
    parts = []
    for sym in symbols:
        try:
            quote = fetch_quote(sym)
            news  = fetch_news(sym, quote.name, settings)
            fund  = fetch_fundamentals(sym)
            headlines = "\n".join(f"  - {n.title}" for n in news[:3]) or "  No recent news."
            parts.append(
                f"--- Live Data: {sym} ({quote.name}) ---\n"
                f"Price: ${quote.price}  Change: {quote.change_pct:+.2f}%\n"
                f"MA5: {quote.ma5}  MA10: {quote.ma10}  MA20: {quote.ma20}  MA50: {quote.ma50}\n"
                f"Bullish MA alignment: {quote.ma_bullish_alignment}\n"
                f"P/E: {fund.pe_ratio or 'N/A'}  Forward P/E: {fund.forward_pe or 'N/A'}\n"
                f"Revenue Growth: {fund.revenue_growth_yoy or 'N/A'}%\n"
                f"Analyst Rating: {fund.analyst_recommendation or 'N/A'}  "
                f"Target: ${fund.analyst_target_price or 'N/A'}\n"
                f"Recent News:\n{headlines}\n"
            )
        except Exception as e:
            log.debug(f"Context fetch failed for {sym}: {e}")
    return "\n".join(parts)


def _build_prompt(session: Session, user_message: str, context: str) -> str:
    history = ""
    for msg in session.messages[-10:]:
        role = "User" if msg.role == "user" else "Assistant"
        history += f"\n{role}: {msg.content}\n"

    ctx_block = f"\n[Live Market Data]\n{context}\n" if context else ""

    return (
        f"{SYSTEM_PROMPT}\n"
        f"{ctx_block}\n"
        f"[Conversation History]\n"
        f"{history}\n"
        f"User: {user_message}\n"
        f"Assistant:"
    )


def chat(session_id: str, user_message: str, settings: Settings) -> str:
    session = get_or_create_session(session_id)
    symbols = _extract_symbols(user_message)
    context = _fetch_context(symbols, settings) if symbols else ""
    prompt  = _build_prompt(session, user_message, context)

    try:
        reply = call_ai(prompt, settings)
    except Exception as e:
        reply = f"Sorry, I encountered an error: {e}"

    session.messages.append(Message(role="user",      content=user_message))
    session.messages.append(Message(role="assistant", content=reply))

    return reply
