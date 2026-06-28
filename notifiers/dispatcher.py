"""
Notification dispatcher — sends the dashboard to all configured channels
"""

import logging
import asyncio
from typing import List

from config.settings import Settings
from analysis.analyzer import StockResult

log = logging.getLogger(__name__)


# ── Email ─────────────────────────────────────────────────────────────────────

async def send_email(dashboard: str, settings: Settings):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    if not all([settings.email_sender, settings.email_password, settings.email_receivers]):
        log.warning("Email: incomplete configuration, skipping.")
        return

    subject = f"📈 Daily Stock Dashboard — {__import__('datetime').datetime.now().strftime('%Y-%m-%d')}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = settings.email_sender
    msg["To"]      = ", ".join(settings.email_receivers)
    msg.attach(MIMEText(dashboard, "plain"))

    try:
        with smtplib.SMTP(settings.email_smtp_host, settings.email_smtp_port) as server:
            server.starttls()
            server.login(settings.email_sender, settings.email_password)
            server.sendmail(settings.email_sender, settings.email_receivers, msg.as_string())
        log.info(f"Email sent to {settings.email_receivers}")
    except Exception as e:
        log.error(f"Email failed: {e}")


# ── Telegram ──────────────────────────────────────────────────────────────────

async def send_telegram(dashboard: str, settings: Settings):
    if not all([settings.telegram_bot_token, settings.telegram_chat_id]):
        log.warning("Telegram: incomplete configuration, skipping.")
        return

    import httpx
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    # Telegram has a 4096-char limit per message; split if needed
    chunks = [dashboard[i:i+4000] for i in range(0, len(dashboard), 4000)]
    try:
        async with httpx.AsyncClient() as client:
            for chunk in chunks:
                resp = await client.post(url, json={
                    "chat_id": settings.telegram_chat_id,
                    "text": chunk,
                    "parse_mode": "Markdown",
                }, timeout=15)
                resp.raise_for_status()
        log.info("Telegram message sent.")
    except Exception as e:
        log.error(f"Telegram failed: {e}")


# ── Discord ───────────────────────────────────────────────────────────────────

async def send_discord(dashboard: str, settings: Settings):
    if not settings.discord_webhook_url:
        log.warning("Discord: no webhook URL configured, skipping.")
        return

    import httpx
    # Discord embed limit is 4096 chars; split into multiple messages if needed
    chunks = [dashboard[i:i+1990] for i in range(0, len(dashboard), 1990)]
    try:
        async with httpx.AsyncClient() as client:
            for chunk in chunks:
                resp = await client.post(settings.discord_webhook_url, json={"content": f"```\n{chunk}\n```"}, timeout=15)
                resp.raise_for_status()
        log.info("Discord message sent.")
    except Exception as e:
        log.error(f"Discord failed: {e}")


# ── Slack ─────────────────────────────────────────────────────────────────────

async def send_slack(dashboard: str, settings: Settings):
    if not all([settings.slack_bot_token, settings.slack_channel_id]):
        log.warning("Slack: incomplete configuration, skipping.")
        return

    import httpx
    headers = {
        "Authorization": f"Bearer {settings.slack_bot_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "channel": settings.slack_channel_id,
        "text": dashboard,
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post("https://slack.com/api/chat.postMessage", json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                log.error(f"Slack API error: {data.get('error')}")
            else:
                log.info("Slack message sent.")
    except Exception as e:
        log.error(f"Slack failed: {e}")


# ── Dispatcher ────────────────────────────────────────────────────────────────

class NotificationDispatcher:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send(self, dashboard: str, results: List[StockResult]):
        tasks = []

        if self.settings.email_sender:
            tasks.append(send_email(dashboard, self.settings))
        if self.settings.telegram_bot_token:
            tasks.append(send_telegram(dashboard, self.settings))
        if self.settings.discord_webhook_url:
            tasks.append(send_discord(dashboard, self.settings))
        if self.settings.slack_bot_token:
            tasks.append(send_slack(dashboard, self.settings))

        if not tasks:
            log.warning("No notification channels configured. Report printed to console only.")
            return

        await asyncio.gather(*tasks, return_exceptions=True)
