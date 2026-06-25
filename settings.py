"""
Settings — loads configuration from environment variables or .env file
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class Settings:
    # --- Watchlist ---
    stock_list: List[str] = field(default_factory=list)

    # --- AI ---
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    openai_base_url: Optional[str] = None   # for OpenAI-compatible providers
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-pro"

    # --- Notifications ---
    # Email
    email_sender: Optional[str] = None
    email_password: Optional[str] = None
    email_receivers: List[str] = field(default_factory=list)
    email_smtp_host: str = "smtp.gmail.com"
    email_smtp_port: int = 587

    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # Discord
    discord_webhook_url: Optional[str] = None

    # Slack
    slack_bot_token: Optional[str] = None
    slack_channel_id: Optional[str] = None

    # --- News ---
    tavily_api_key: Optional[str] = None
    brave_api_key: Optional[str] = None

    # --- Behavior ---
    report_type: str = "full"          # full | simple | brief
    news_max_age_days: int = 3
    bias_threshold: float = 5.0        # % deviation threshold for "no chasing highs" warning

    def __post_init__(self):
        raw = os.getenv("STOCK_LIST", "")
        self.stock_list = [s.strip().upper() for s in raw.split(",") if s.strip()]

        self.openai_api_key   = os.getenv("OPENAI_API_KEY")
        self.openai_model     = os.getenv("OPENAI_MODEL", self.openai_model)
        self.openai_base_url  = os.getenv("OPENAI_BASE_URL")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.anthropic_model  = os.getenv("ANTHROPIC_MODEL", self.anthropic_model)
        self.gemini_api_key   = os.getenv("GEMINI_API_KEY")
        self.gemini_model     = os.getenv("GEMINI_MODEL", self.gemini_model)

        self.email_sender    = os.getenv("EMAIL_SENDER")
        self.email_password  = os.getenv("EMAIL_PASSWORD")
        receivers = os.getenv("EMAIL_RECEIVERS", "")
        self.email_receivers = [r.strip() for r in receivers.split(",") if r.strip()]
        self.email_smtp_host = os.getenv("EMAIL_SMTP_HOST", self.email_smtp_host)
        self.email_smtp_port = int(os.getenv("EMAIL_SMTP_PORT", self.email_smtp_port))

        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id   = os.getenv("TELEGRAM_CHAT_ID")

        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

        self.slack_bot_token  = os.getenv("SLACK_BOT_TOKEN")
        self.slack_channel_id = os.getenv("SLACK_CHANNEL_ID")

        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.brave_api_key  = os.getenv("BRAVE_API_KEY")

        self.report_type      = os.getenv("REPORT_TYPE", self.report_type)
        self.news_max_age_days = int(os.getenv("NEWS_MAX_AGE_DAYS", self.news_max_age_days))
        self.bias_threshold   = float(os.getenv("BIAS_THRESHOLD", self.bias_threshold))

    def active_ai_provider(self) -> str:
        if self.gemini_api_key:
            return "gemini"
        if self.anthropic_api_key:
            return "anthropic"
        if self.openai_api_key:
            return "openai"
        raise RuntimeError(
            "No AI provider configured. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY."
        )
