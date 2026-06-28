"""
Web UI -- FastAPI server with dashboard, history, backtest, agent chat, and settings.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config.settings import Settings
from analysis.analyzer import StockAnalyzer
from market_review.review import fetch_market_review
from backtest.validator import run_backtest, backtest_summary
from agent.chat import chat, list_sessions, delete_session
from storage.store import (
    load_latest_results, load_results, list_history_dates,
    delete_result, load_backtest, save_settings, load_settings,
)
from notifiers.dispatcher import NotificationDispatcher

log = logging.getLogger(__name__)

app = FastAPI(title="Daily Stock Analyzer", version="1.0.0")

# Mount static files if directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# ── HTML UI ───────────────────────────────────────────────────────────────────

def _html_page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Stock Analyzer</title>
<style>
  :root {{
    --bg: #0f1117; --surface: #1a1d27; --border: #2a2d3a;
    --text: #e2e8f0; --muted: #8892a4; --accent: #6366f1;
    --green: #22c55e; --red: #ef4444; --yellow: #eab308;
    --font: 'Inter', system-ui, sans-serif;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: var(--font); min-height: 100vh; }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}

  /* Nav */
  nav {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 2rem;
         display: flex; align-items: center; gap: 2rem; height: 56px; position: sticky; top: 0; z-index: 100; }}
  nav .brand {{ font-weight: 700; font-size: 1.1rem; color: var(--text); }}
  nav a {{ color: var(--muted); font-size: 0.9rem; padding: 0.3rem 0.6rem; border-radius: 6px; }}
  nav a:hover, nav a.active {{ color: var(--text); background: var(--border); text-decoration: none; }}

  /* Layout */
  .container {{ max-width: 1100px; margin: 0 auto; padding: 2rem; }}
  h1 {{ font-size: 1.6rem; margin-bottom: 1.5rem; }}
  h2 {{ font-size: 1.15rem; margin-bottom: 1rem; color: var(--muted); font-weight: 600; }}

  /* Cards */
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }}
  .card-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }}

  /* Stock card */
  .stock-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
                 padding: 1.2rem; transition: border-color .2s; }}
  .stock-card:hover {{ border-color: var(--accent); }}
  .stock-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: .8rem; }}
  .stock-symbol {{ font-size: 1.2rem; font-weight: 700; }}
  .stock-name {{ font-size: 0.8rem; color: var(--muted); margin-top: 2px; }}
  .badge {{ padding: .25rem .7rem; border-radius: 20px; font-size: .75rem; font-weight: 700; }}
  .badge-buy   {{ background: rgba(34,197,94,.15);  color: var(--green); }}
  .badge-watch {{ background: rgba(234,179,8,.15);  color: var(--yellow); }}
  .badge-sell  {{ background: rgba(239,68,68,.15);  color: var(--red); }}
  .price-row {{ display: flex; align-items: baseline; gap: .5rem; margin-bottom: .6rem; }}
  .price {{ font-size: 1.3rem; font-weight: 600; }}
  .change.up   {{ color: var(--green); font-size: .9rem; }}
  .change.down {{ color: var(--red);   font-size: .9rem; }}
  .conclusion {{ font-size: .85rem; color: var(--muted); line-height: 1.5; margin-bottom: .8rem; }}
  .score-bar {{ height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }}
  .score-fill {{ height: 100%; border-radius: 2px; background: var(--accent); }}
  .score-label {{ font-size: .75rem; color: var(--muted); margin-top: 4px; }}

  /* Forms */
  .form-row {{ display: flex; gap: .8rem; margin-bottom: 1rem; flex-wrap: wrap; }}
  input, select, textarea {{
    background: var(--bg); border: 1px solid var(--border); color: var(--text);
    padding: .6rem 1rem; border-radius: 8px; font-size: .9rem; font-family: var(--font);
    outline: none; width: 100%;
  }}
  input:focus, select:focus, textarea:focus {{ border-color: var(--accent); }}
  .form-row input, .form-row select {{ flex: 1; min-width: 160px; }}
  button {{
    background: var(--accent); color: #fff; border: none; padding: .6rem 1.4rem;
    border-radius: 8px; font-size: .9rem; font-weight: 600; cursor: pointer;
    transition: opacity .2s; white-space: nowrap;
  }}
  button:hover {{ opacity: .85; }}
  button.secondary {{ background: var(--border); color: var(--text); }}
  button.danger    {{ background: #7f1d1d; color: #fca5a5; }}

  /* Table */
  table {{ width: 100%; border-collapse: collapse; font-size: .88rem; }}
  th {{ text-align: left; padding: .6rem 1rem; color: var(--muted); font-weight: 600;
        border-bottom: 1px solid var(--border); }}
  td {{ padding: .7rem 1rem; border-bottom: 1px solid var(--border); }}
  tr:hover td {{ background: rgba(255,255,255,.02); }}

  /* Chat */
  .chat-box {{ display: flex; flex-direction: column; height: 500px; }}
  .messages {{ flex: 1; overflow-y: auto; padding: 1rem; display: flex; flex-direction: column; gap: .8rem; }}
  .msg {{ max-width: 80%; padding: .8rem 1rem; border-radius: 12px; font-size: .9rem; line-height: 1.5; white-space: pre-wrap; }}
  .msg.user      {{ background: var(--accent); color: #fff; align-self: flex-end; border-bottom-right-radius: 4px; }}
  .msg.assistant {{ background: var(--surface); border: 1px solid var(--border); align-self: flex-start; border-bottom-left-radius: 4px; }}
  .chat-input    {{ display: flex; gap: .6rem; padding: 1rem; border-top: 1px solid var(--border); }}
  .chat-input input {{ flex: 1; }}

  /* Alerts */
  .alert {{ padding: .8rem 1.2rem; border-radius: 8px; margin-bottom: 1rem; font-size: .9rem; }}
  .alert-info    {{ background: rgba(99,102,241,.15); border: 1px solid rgba(99,102,241,.3); }}
  .alert-success {{ background: rgba(34,197,94,.12);  border: 1px solid rgba(34,197,94,.3); }}
  .alert-error   {{ background: rgba(239,68,68,.12);  border: 1px solid rgba(239,68,68,.3); }}

  /* Misc */
  .muted  {{ color: var(--muted); font-size: .85rem; }}
  .mt1    {{ margin-top: .5rem; }}
  .mt2    {{ margin-top: 1rem; }}
  .flex   {{ display: flex; gap: .6rem; align-items: center; }}
  .tag    {{ background: var(--border); color: var(--muted); padding: .2rem .6rem; border-radius: 20px; font-size: .75rem; }}
  pre     {{ background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
             padding: 1rem; overflow-x: auto; font-size: .82rem; white-space: pre-wrap; }}
  #toast  {{ position: fixed; bottom: 1.5rem; right: 1.5rem; background: var(--surface);
             border: 1px solid var(--border); border-radius: 10px; padding: .8rem 1.4rem;
             font-size: .9rem; z-index: 999; display: none; box-shadow: 0 4px 20px rgba(0,0,0,.4); }}
</style>
</head>
<body>
<nav>
  <span class="brand">📈 Stock Analyzer</span>
  <a href="/">Dashboard</a>
  <a href="/history">History</a>
  <a href="/market">Market</a>
  <a href="/backtest">Backtest</a>
  <a href="/chat">Agent Chat</a>
  <a href="/settings">Settings</a>
</nav>
<div class="container">
{body}
</div>
<div id="toast"></div>
<script>
function toast(msg, ok=true) {{
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.style.display = 'block';
  el.style.color = ok ? '#22c55e' : '#ef4444';
  setTimeout(() => el.style.display = 'none', 3000);
}}
async function api(url, opts={{}}) {{
  const r = await fetch(url, {{headers: {{'Content-Type':'application/json'}}, ...opts}});
  return r.json();
}}
</script>
</body>
</html>"""


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    results = load_latest_results()
    settings = get_settings()

    if not results:
        stock_list = ", ".join(settings.stock_list) if settings.stock_list else "None configured"
        body = f"""
        <h1>📈 Dashboard</h1>
        <div class="alert alert-info">No analysis results yet. Configure your stock list and run an analysis.</div>
        <div class="card">
          <h2>Run Analysis</h2>
          <div class="form-row">
            <input id="syms" placeholder="Symbols e.g. AAPL,TSLA,NVDA (leave blank for {stock_list})" />
            <button onclick="runAnalysis()">▶ Analyze</button>
          </div>
          <div id="run-status" class="muted"></div>
        </div>
        <script>
        async function runAnalysis() {{
          document.getElementById('run-status').textContent = '⏳ Running analysis... this may take 1-2 minutes.';
          const syms = document.getElementById('syms').value;
          const r = await api('/api/analyze', {{method:'POST', body: JSON.stringify({{symbols: syms}})}});
          if (r.ok) {{ toast('Analysis complete! Reloading...'); setTimeout(() => location.reload(), 1500); }}
          else {{ document.getElementById('run-status').textContent = 'Error: ' + (r.error || 'unknown'); }}
        }}
        </script>"""
    else:
        date_str = results[0].get("saved_at", "")[:10]
        buys  = sum(1 for r in results if r.get("signal") == "BUY")
        watch = sum(1 for r in results if r.get("signal") == "WATCH")
        sells = sum(1 for r in results if r.get("signal") == "SELL")

        cards = ""
        for r in results:
            sig  = r.get("signal", "WATCH").lower()
            chg  = r.get("change_pct", 0)
            chg_cls = "up" if chg >= 0 else "down"
            chg_sym = "+" if chg >= 0 else ""
            score = r.get("score", 50)
            cards += f"""
            <div class="stock-card">
              <div class="stock-header">
                <div>
                  <div class="stock-symbol">{r.get("symbol","")}</div>
                  <div class="stock-name">{r.get("name","")}</div>
                </div>
                <span class="badge badge-{sig}">{r.get("signal","")}</span>
              </div>
              <div class="price-row">
                <span class="price">${r.get("price",0)}</span>
                <span class="change {chg_cls}">{chg_sym}{chg:.2f}%</span>
              </div>
              <div class="conclusion">{r.get("conclusion","")}</div>
              <div class="score-bar"><div class="score-fill" style="width:{score}%"></div></div>
              <div class="score-label">Score: {score}/100 &nbsp;|&nbsp; {r.get("outlook","")}</div>
            </div>"""

        body = f"""
        <div class="flex" style="justify-content:space-between; margin-bottom:1.5rem;">
          <h1>📈 Dashboard <span class="muted" style="font-size:.9rem;">— {date_str}</span></h1>
          <div class="flex">
            <button class="secondary" onclick="runAnalysis()">↺ Re-run</button>
            <button onclick="sendNotification()">📤 Send</button>
          </div>
        </div>
        <div class="card" style="padding:1rem 1.5rem; margin-bottom:1.5rem;">
          <div class="flex" style="gap:2rem;">
            <span>🟢 Buy: <strong>{buys}</strong></span>
            <span>🟡 Watch: <strong>{watch}</strong></span>
            <span>🔴 Sell: <strong>{sells}</strong></span>
            <span class="muted">Total: {len(results)}</span>
          </div>
        </div>
        <div class="card-grid">{cards}</div>
        <div class="card mt2">
          <h2>Run New Analysis</h2>
          <div class="form-row">
            <input id="syms" placeholder="Symbols e.g. AAPL,TSLA (leave blank for saved list)" />
            <button onclick="runAnalysis()">▶ Analyze</button>
          </div>
          <div id="run-status" class="muted"></div>
        </div>
        <script>
        async function runAnalysis() {{
          document.getElementById('run-status').textContent = '⏳ Running... this may take 1-2 minutes.';
          const syms = document.getElementById('syms').value;
          const r = await api('/api/analyze', {{method:'POST', body: JSON.stringify({{symbols: syms}})}});
          if (r.ok) {{ toast('Done! Reloading...'); setTimeout(() => location.reload(), 1500); }}
          else {{ document.getElementById('run-status').textContent = 'Error: ' + (r.error || 'unknown'); }}
        }}
        async function sendNotification() {{
          const r = await api('/api/notify', {{method:'POST'}});
          toast(r.ok ? 'Notifications sent!' : 'Failed: ' + r.error, r.ok);
        }}
        </script>"""

    return HTMLResponse(_html_page("Dashboard", body))


# ── History ───────────────────────────────────────────────────────────────────

@app.get("/history", response_class=HTMLResponse)
async def history_page():
    dates = list_history_dates()
    if not dates:
        body = "<h1>📜 History</h1><div class='alert alert-info'>No history yet.</div>"
        return HTMLResponse(_html_page("History", body))

    rows = ""
    for date in dates:
        recs = load_results(date_str=date)
        for r in recs:
            sig = r.get("signal","WATCH").lower()
            rows += f"""<tr>
              <td>{date}</td>
              <td><strong>{r.get("symbol","")}</strong></td>
              <td>{r.get("name","")}</td>
              <td><span class="badge badge-{sig}">{r.get("signal","")}</span></td>
              <td>{r.get("score","")}/100</td>
              <td>${r.get("price","")}</td>
              <td class="muted">{r.get("conclusion","")[:80]}...</td>
              <td><button class="danger" style="padding:.3rem .7rem;font-size:.75rem;"
                  onclick="del('{date}','{r.get('symbol','')}')">Delete</button></td>
            </tr>"""

    body = f"""
    <h1>📜 History</h1>
    <div class="card" style="overflow-x:auto;">
      <table>
        <thead><tr><th>Date</th><th>Symbol</th><th>Name</th><th>Signal</th><th>Score</th><th>Price</th><th>Conclusion</th><th></th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <script>
    async function del(date, sym) {{
      if (!confirm('Delete ' + sym + ' (' + date + ')?')) return;
      const r = await api('/api/history/' + date + '/' + sym, {{method:'DELETE'}});
      toast(r.ok ? 'Deleted' : 'Failed', r.ok);
      if (r.ok) location.reload();
    }}
    </script>"""
    return HTMLResponse(_html_page("History", body))


# ── Market Review ─────────────────────────────────────────────────────────────

@app.get("/market", response_class=HTMLResponse)
async def market_page():
    body = """
    <h1>🌍 Market Review</h1>
    <div class="card">
      <button onclick="loadMarket()">🔄 Fetch Latest Market Data</button>
    </div>
    <div id="market-content" class="card" style="display:none;"><pre id="market-pre"></pre></div>
    <script>
    async function loadMarket() {
      document.getElementById('market-content').style.display = 'block';
      document.getElementById('market-pre').textContent = 'Fetching...';
      const r = await api('/api/market');
      document.getElementById('market-pre').textContent = r.text || JSON.stringify(r, null, 2);
    }
    </script>"""
    return HTMLResponse(_html_page("Market", body))


# ── Backtest ──────────────────────────────────────────────────────────────────

@app.get("/backtest", response_class=HTMLResponse)
async def backtest_page():
    records = load_backtest()
    if not records:
        body = """
        <h1>📊 Backtest</h1>
        <div class="alert alert-info">No backtest data yet. Run an analysis first, then validate.</div>
        <button onclick="runBacktest()">▶ Run Backtest</button>
        <div id="bt-status" class="muted mt1"></div>
        <script>
        async function runBacktest() {
          document.getElementById('bt-status').textContent = 'Running...';
          const r = await api('/api/backtest', {method:'POST'});
          if (r.ok) { toast('Done!'); setTimeout(() => location.reload(), 1500); }
          else { document.getElementById('bt-status').textContent = 'Error: ' + r.error; }
        }
        </script>"""
        return HTMLResponse(_html_page("Backtest", body))

    rows = ""
    for r in records:
        correct = r.get("direction_correct")
        icon = "✅" if correct else ("❌" if correct is False else "⏳")
        chg  = r.get("actual_change_pct")
        rows += f"""<tr>
          <td>{r.get("analysis_date","")}</td>
          <td><strong>{r.get("symbol","")}</strong></td>
          <td>{r.get("predicted_signal","")}</td>
          <td>{r.get("predicted_outlook","")}</td>
          <td>${r.get("price_at_analysis","")}</td>
          <td>{("$"+str(r.get("price_next_day",""))) if r.get("price_next_day") else "—"}</td>
          <td>{(f"{chg:+.2f}%") if chg is not None else "—"}</td>
          <td>{icon}</td>
        </tr>"""

    validated = [r for r in records if r.get("direction_correct") is not None]
    correct   = sum(1 for r in validated if r.get("direction_correct"))
    accuracy  = round(correct / len(validated) * 100, 1) if validated else 0

    body = f"""
    <div class="flex" style="justify-content:space-between; margin-bottom:1.5rem;">
      <h1>📊 Backtest</h1>
      <button onclick="runBacktest()">↺ Re-run</button>
    </div>
    <div class="card flex" style="gap:3rem;">
      <div><div class="muted">Validated</div><strong style="font-size:1.5rem;">{len(validated)}</strong></div>
      <div><div class="muted">Correct</div><strong style="font-size:1.5rem;color:var(--green)">{correct}</strong></div>
      <div><div class="muted">Accuracy</div><strong style="font-size:1.5rem;">{accuracy}%</strong></div>
    </div>
    <div class="card" style="overflow-x:auto;">
      <table>
        <thead><tr><th>Date</th><th>Symbol</th><th>Signal</th><th>Outlook</th><th>Price Then</th><th>Next Day</th><th>Change</th><th>Correct</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <script>
    async function runBacktest() {{
      const r = await api('/api/backtest', {{method:'POST'}});
      toast(r.ok ? 'Done!' : 'Error: ' + r.error, r.ok);
      if (r.ok) setTimeout(() => location.reload(), 1500);
    }}
    </script>"""
    return HTMLResponse(_html_page("Backtest", body))


# ── Agent Chat ────────────────────────────────────────────────────────────────

@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    sid = str(uuid.uuid4())
    body = f"""
    <h1>🤖 Agent Chat</h1>
    <p class="muted" style="margin-bottom:1rem;">Ask me anything about US stocks. I'll fetch live data to support my answers.</p>
    <div class="card" style="padding:0;">
      <div class="chat-box">
        <div class="messages" id="messages">
          <div class="msg assistant">Hi! Ask me about any US stock — e.g. "Analyze AAPL" or "Is NVDA overvalued?"</div>
        </div>
        <div class="chat-input">
          <input id="msg-input" placeholder="Ask about a stock..." onkeydown="if(event.key==='Enter') sendMsg()" />
          <button onclick="sendMsg()">Send</button>
        </div>
      </div>
    </div>
    <script>
    const SESSION_ID = '{sid}';
    async function sendMsg() {{
      const input = document.getElementById('msg-input');
      const text  = input.value.trim();
      if (!text) return;
      input.value = '';
      addMsg('user', text);
      addMsg('assistant', '⏳ Thinking...');
      const r = await api('/api/chat', {{method:'POST', body: JSON.stringify({{session_id: SESSION_ID, message: text}})}});
      const msgs = document.getElementById('messages');
      msgs.lastChild.textContent = r.reply || ('Error: ' + r.error);
      msgs.scrollTop = msgs.scrollHeight;
    }}
    function addMsg(role, text) {{
      const msgs = document.getElementById('messages');
      const div  = document.createElement('div');
      div.className = 'msg ' + role;
      div.textContent = text;
      msgs.appendChild(div);
      msgs.scrollTop = msgs.scrollHeight;
    }}
    </script>"""
    return HTMLResponse(_html_page("Agent Chat", body))


# ── Settings ──────────────────────────────────────────────────────────────────

@app.get("/settings", response_class=HTMLResponse)
async def settings_page():
    s = get_settings()
    body = f"""
    <h1>⚙️ Settings</h1>
    <div class="card">
      <h2>Watchlist</h2>
      <div class="form-row">
        <input id="stock-list" value="{','.join(s.stock_list)}" placeholder="AAPL,TSLA,NVDA" />
        <button onclick="saveSetting('stock_list', document.getElementById('stock-list').value)">Save</button>
      </div>
    </div>
    <div class="card">
      <h2>Behavior</h2>
      <div class="form-row">
        <input id="report-type" value="{s.report_type}" placeholder="full | simple | brief" />
        <input id="news-days"   value="{s.news_max_age_days}" placeholder="News max age (days)" />
        <input id="bias-thresh" value="{s.bias_threshold}" placeholder="MA20 deviation threshold %" />
      </div>
      <button onclick="saveSettings()">Save</button>
    </div>
    <div class="card">
      <h2>Environment Variables</h2>
      <p class="muted">Sensitive keys (API keys, tokens) are loaded from environment variables or your <code>.env</code> file. Edit that file directly to change them.</p>
      <div class="mt2">
        <table>
          <tr><th>Variable</th><th>Status</th></tr>
          <tr><td>OPENAI_API_KEY</td><td>{'✅ Set' if s.openai_api_key else '❌ Not set'}</td></tr>
          <tr><td>ANTHROPIC_API_KEY</td><td>{'✅ Set' if s.anthropic_api_key else '❌ Not set'}</td></tr>
          <tr><td>GEMINI_API_KEY</td><td>{'✅ Set' if s.gemini_api_key else '❌ Not set'}</td></tr>
          <tr><td>TELEGRAM_BOT_TOKEN</td><td>{'✅ Set' if s.telegram_bot_token else '❌ Not set'}</td></tr>
          <tr><td>DISCORD_WEBHOOK_URL</td><td>{'✅ Set' if s.discord_webhook_url else '❌ Not set'}</td></tr>
          <tr><td>SLACK_BOT_TOKEN</td><td>{'✅ Set' if s.slack_bot_token else '❌ Not set'}</td></tr>
          <tr><td>EMAIL_SENDER</td><td>{'✅ Set' if s.email_sender else '❌ Not set'}</td></tr>
          <tr><td>TAVILY_API_KEY</td><td>{'✅ Set' if s.tavily_api_key else '❌ Not set'}</td></tr>
        </table>
      </div>
    </div>
    <script>
    async function saveSetting(key, val) {{
      const r = await api('/api/settings', {{method:'POST', body: JSON.stringify({{[key]: val}})}});
      toast(r.ok ? 'Saved!' : 'Error: ' + r.error, r.ok);
    }}
    async function saveSettings() {{
      const data = {{
        report_type: document.getElementById('report-type').value,
        news_max_age_days: parseInt(document.getElementById('news-days').value) || 3,
        bias_threshold: parseFloat(document.getElementById('bias-thresh').value) || 5.0,
      }};
      const r = await api('/api/settings', {{method:'POST', body: JSON.stringify(data)}});
      toast(r.ok ? 'Saved!' : 'Error: ' + r.error, r.ok);
    }}
    </script>"""
    return HTMLResponse(_html_page("Settings", body))


# ── API Endpoints ─────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    symbols: Optional[str] = None


@app.post("/api/analyze")
async def api_analyze(req: AnalyzeRequest):
    from storage.store import save_result
    settings = get_settings()
    symbols  = [s.strip().upper() for s in req.symbols.split(",")] if req.symbols else settings.stock_list
    if not symbols:
        raise HTTPException(400, "No symbols provided")

    analyzer = StockAnalyzer(settings)
    results  = []
    for sym in symbols:
        try:
            r = await analyzer.analyze(sym)
            save_result(r.to_dict())
            results.append(r.to_dict())
        except Exception as e:
            log.warning(f"Failed {sym}: {e}")

    return {"ok": True, "count": len(results)}


@app.post("/api/notify")
async def api_notify():
    settings  = get_settings()
    results   = load_latest_results()
    if not results:
        return {"ok": False, "error": "No results to send"}

    analyzer   = StockAnalyzer(settings)
    from analysis.analyzer import StockResult
    result_objs = [StockResult(**{k: v for k, v in r.items() if k in StockResult.__dataclass_fields__}) for r in results]
    dashboard   = analyzer.build_dashboard(result_objs)
    dispatcher  = NotificationDispatcher(settings)
    await dispatcher.send(dashboard, result_objs)
    return {"ok": True}


@app.get("/api/market")
async def api_market():
    try:
        review = fetch_market_review()
        return {"ok": True, "text": review.to_text(), "data": review.to_dict()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/backtest")
async def api_backtest():
    try:
        records  = run_backtest()
        summary  = backtest_summary(records)
        return {"ok": True, "summary": summary, "count": len(records)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    settings = get_settings()
    try:
        reply = chat(req.session_id, req.message, settings)
        return {"ok": True, "reply": reply}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/settings")
async def api_save_settings(request: Request):
    global _settings
    data = await request.json()
    save_settings(data)
    _settings = None  # force reload
    return {"ok": True}


@app.delete("/api/history/{date}/{symbol}")
async def api_delete_history(date: str, symbol: str):
    ok = delete_result(date, symbol)
    return {"ok": ok}


@app.get("/api/results")
async def api_results(date: Optional[str] = None, symbol: Optional[str] = None):
    return load_results(date_str=date, symbol=symbol)


# ── Portfolio API ─────────────────────────────────────────────────────────────

@app.get("/api/portfolio/summary")
async def api_portfolio_summary():
    from portfolio.tracker import PortfolioTracker
    try:
        return PortfolioTracker().summary()
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/portfolio/trades")
async def api_portfolio_trades():
    from portfolio.tracker import PortfolioTracker
    return [t.to_dict() for t in PortfolioTracker().get_trades()]


class TradeRequest(BaseModel):
    symbol: str
    name: str = ""
    action: str = "BUY"
    shares: float
    price: float
    notes: str = ""


@app.post("/api/portfolio/trades")
async def api_add_trade(req: TradeRequest):
    from portfolio.tracker import PortfolioTracker
    try:
        trade = PortfolioTracker().add_trade(
            req.symbol, req.name, req.action, req.shares, req.price, req.notes
        )
        return {"ok": True, "trade": trade.to_dict()}
    except ValueError as e:
        return {"ok": False, "error": str(e)}


@app.delete("/api/portfolio/trades/{trade_id}")
async def api_delete_trade(trade_id: str):
    from portfolio.tracker import PortfolioTracker
    ok = PortfolioTracker().delete_trade(trade_id)
    return {"ok": ok}
