# 📈 Daily Stock Analyzer

An AI-powered daily stock analysis tool for US equities. Every day after market close it fetches quotes, fundamentals, and news for your watchlist, runs an AI analysis, and pushes a Decision Dashboard to your notification channels.

## Features

| Module | Description |
|---|---|
| **AI Decision Dashboard** | Signal (Buy/Watch/Sell), score 0–100, entry/stop/target, risks, catalysts, checklist |
| **Fundamentals** | P/E, forward P/E, revenue growth, profit margin, EPS, dividends, analyst ratings |
| **Market Review** | S&P 500, Nasdaq, Dow, Russell 2000, VIX, all 11 sector ETFs |
| **Multi-model Fallback** | Auto-retries across Gemini → Anthropic → OpenAI if a provider fails |
| **AI Backtest** | Validates past predictions against actual next-day prices; accuracy tracking per stock |
| **Agent Chat** | Multi-turn Q&A with live market data injected automatically |
| **Web UI** | Browser dashboard, history, market review, backtest, agent chat, settings |
| **Notifications** | Email, Telegram, Discord, Slack |
| **GitHub Actions** | Free automated scheduling — no server needed |

---

## Quick Start

### Option 1: GitHub Actions (free, no server)

1. **Fork this repo** and give it a star if it helps!
2. `Settings → Secrets and variables → Actions` — add your secrets (table below)
3. `Actions` tab → enable workflows
4. `Actions → Daily Stock Analysis → Run workflow` to test

Runs automatically **Mon–Fri at 5:05 PM ET** after US market close.

#### Secrets

**Watchlist (required)**

| Secret | Example |
|---|---|
| `STOCK_LIST` | `AAPL,TSLA,NVDA,MSFT` |

**AI — add at least one**

| Secret | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI (also works with DeepSeek, Qwen, etc. via `OPENAI_BASE_URL`) |
| `OPENAI_MODEL` | e.g. `gpt-4o` |
| `OPENAI_BASE_URL` | Optional: custom base URL for OpenAI-compatible providers |
| `ANTHROPIC_API_KEY` | Anthropic Claude |
| `ANTHROPIC_MODEL` | e.g. `claude-3-5-sonnet-20241022` |
| `GEMINI_API_KEY` | Google Gemini (tried first if set) |
| `GEMINI_MODEL` | e.g. `gemini-1.5-pro` |

**Notifications — add at least one**

| Secret | Description |
|---|---|
| `EMAIL_SENDER` | Sender address |
| `EMAIL_PASSWORD` | App password (Gmail: Account → Security → App Passwords) |
| `EMAIL_RECEIVERS` | Comma-separated recipients |
| `TELEGRAM_BOT_TOKEN` | From @BotFather |
| `TELEGRAM_CHAT_ID` | Your chat or channel ID |
| `DISCORD_WEBHOOK_URL` | Discord webhook URL |
| `SLACK_BOT_TOKEN` | `xoxb-...` |
| `SLACK_CHANNEL_ID` | Channel ID |

**News (optional but recommended)**

| Secret | Description |
|---|---|
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) — best quality news |
| `BRAVE_API_KEY` | [brave.com/search/api](https://brave.com/search/api/) — fallback |

---

### Option 2: Local

```bash
git clone <your-repo-url> && cd daily-stock-analyzer
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
python main.py
```

**CLI options:**

```bash
python main.py --stocks AAPL,TSLA     # override watchlist
python main.py --dry-run              # skip notifications
python main.py --debug                # verbose logging
python main.py --market-review        # market overview only
python main.py --backtest             # validate past predictions
python main.py --webui                # Web UI + scheduled analysis
python main.py --webui-only           # Web UI only
python main.py --webui --port 9000    # custom port
```

---

## Web UI

Start the server:

```bash
python main.py --webui-only
```

Visit `http://127.0.0.1:8000`. Pages:

| Page | URL | Description |
|---|---|---|
| Dashboard | `/` | Latest analysis cards, run new analysis, send notifications |
| History | `/history` | Browse and delete past analysis records |
| Market | `/market` | Live US indices + all 11 sector ETFs |
| Backtest | `/backtest` | AI prediction accuracy vs actual price moves |
| Agent Chat | `/chat` | Ask questions about any stock with live data |
| Settings | `/settings` | Watchlist, behavior settings, API key status |

---

## Sample Output

```
🎯 2026-06-25 17:05 -- Daily Stock Decision Dashboard
Analyzed 3 stock(s)  |  🟢 Buy: 1  🟡 Watch: 1  🔴 Sell: 1

📊 Summary
  🟢 AAPL (Apple Inc.)          |  BUY   |  Score: 74  |  Bullish
  🟡 TSLA (Tesla, Inc.)         |  WATCH |  Score: 52  |  Range-bound
  🔴 NVDA (NVIDIA Corporation)  |  SELL  |  Score: 38  |  Bearish

────────────────────────────────────────────────────
🟢 AAPL -- Apple Inc.
   Price: $213.42  (+1.24% today)
   Signal: BUY  |  Score: 74/100  |  Bullish
   💡 Strong MA alignment and services momentum support a near-term buy.
   Entry: $212–$215  |  Stop: $205  |  Target: $230

   🚨 Risks:
      1. Broader market weakness could weigh on large-cap tech.
      2. iPhone demand softness in China remains a concern.

   ✨ Catalysts:
      1. Services revenue growth accelerating.
      2. AI integration driving upgrade cycle.

   ✅ Checklist:
      • MA bullish alignment: Met
      • Volume confirmation: Met
      • Not extended from MA20: Caution
      • Positive news catalyst: Met
      • Valuation reasonable: Caution

   📰 Recent News:
      • Apple Services revenue hits record high in Q2
      • Analysts raise price targets ahead of WWDC

⚠️  For informational purposes only. Not investment advice.
```

---

## Project Structure

```
.
├── main.py                          # Entry point + CLI
├── requirements.txt
├── .env.example
├── .github/workflows/
│   └── daily_analysis.yml           # GitHub Actions schedule
├── config/
│   └── settings.py                  # All configuration from env vars
├── data/
│   ├── market.py                    # Quotes + moving averages (yfinance)
│   └── news.py                      # News (Tavily / Brave / yfinance)
├── analysis/
│   ├── ai_caller.py                 # Multi-model fallback AI caller
│   └── analyzer.py                  # Prompt builder + dashboard formatter
├── fundamentals/
│   └── fetcher.py                   # P/E, revenue, earnings, dividends
├── market_review/
│   └── review.py                    # Indices + sector ETF performance
├── backtest/
│   └── validator.py                 # Prediction vs actual price validation
├── agent/
│   └── chat.py                      # Multi-turn Q&A with live data
├── notifiers/
│   └── dispatcher.py                # Email, Telegram, Discord, Slack
├── storage/
│   └── store.py                     # JSON persistence for results + settings
└── web/
    └── app.py                       # FastAPI Web UI
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your values.

| Variable | Description | Default |
|---|---|---|
| `STOCK_LIST` | Watchlist symbols | — |
| `REPORT_TYPE` | `full` / `simple` / `brief` | `full` |
| `NEWS_MAX_AGE_DAYS` | Max age of news articles | `3` |
| `BIAS_THRESHOLD` | % deviation from MA20 for extended-price warning | `5.0` |

---

## Disclaimer

For informational and educational purposes only. AI-generated analysis does not constitute investment advice. Always do your own research before making investment decisions.
