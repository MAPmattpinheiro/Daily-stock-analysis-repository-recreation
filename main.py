"""
Daily Stock Analyzer -- main entry point
"""

import argparse
import asyncio
import logging
import sys

from config.settings import Settings
from analysis.analyzer import StockAnalyzer
from notifiers.dispatcher import NotificationDispatcher
from storage.store import save_result

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Daily Stock Analyzer")
    parser.add_argument("--stocks",        help="Comma-separated symbols, e.g. AAPL,TSLA")
    parser.add_argument("--dry-run",       action="store_true", help="Skip notifications")
    parser.add_argument("--debug",         action="store_true", help="Verbose logging")
    parser.add_argument("--market-review", action="store_true", help="Run market review only")
    parser.add_argument("--backtest",      action="store_true", help="Run backtest validation")
    parser.add_argument("--webui",         action="store_true", help="Start Web UI + scheduled analysis")
    parser.add_argument("--webui-only",    action="store_true", help="Start Web UI only")
    parser.add_argument("--port",          type=int, default=8000, help="Web UI port (default: 8000)")
    return parser.parse_args()


async def run_analysis(args, settings):
    symbols = [s.strip().upper() for s in args.stocks.split(",")] if args.stocks else settings.stock_list
    if not symbols:
        log.error("No stocks configured. Set STOCK_LIST in .env or pass --stocks.")
        sys.exit(1)

    log.info(f"Analyzing {len(symbols)} stock(s): {', '.join(symbols)}")
    analyzer   = StockAnalyzer(settings)
    dispatcher = NotificationDispatcher(settings)
    results    = []

    for symbol in symbols:
        symbol = symbol.strip().upper()
        log.info(f"  → {symbol}")
        try:
            result = await analyzer.analyze(symbol)
            save_result(result.to_dict())
            results.append(result)
        except Exception as e:
            log.warning(f"  ✗ {symbol} failed: {e}")

    if not results:
        log.error("No results produced.")
        sys.exit(1)

    dashboard = analyzer.build_dashboard(results)
    print("\n" + dashboard + "\n")

    if not args.dry_run:
        await dispatcher.send(dashboard, results)
        log.info("Notifications sent.")
    else:
        log.info("Dry-run — notifications skipped.")


async def run_market_review(args, settings):
    from market_review.review import fetch_market_review
    from notifiers.dispatcher import NotificationDispatcher
    log.info("Fetching market review...")
    review = fetch_market_review()
    print("\n" + review.to_text() + "\n")
    if not args.dry_run:
        dispatcher = NotificationDispatcher(settings)
        await dispatcher.send(review.to_text(), [])
        log.info("Market review sent.")


async def run_backtest():
    from backtest.validator import run_backtest as _bt, backtest_summary
    log.info("Running backtest validation...")
    records = _bt()
    print("\n" + backtest_summary(records) + "\n")


def start_webui(port: int, with_scheduler: bool, settings: Settings):
    import threading
    import uvicorn
    from web.app import app

    if with_scheduler:
        def scheduler():
            import time
            import asyncio as aio
            log.info("Scheduler started — analysis runs Mon-Fri after market close.")
            while True:
                from datetime import datetime
                now = datetime.now()
                # Run at 17:05 on weekdays (after 5pm ET)
                if now.weekday() < 5 and now.hour == 17 and now.minute == 5:
                    log.info("Scheduler: running daily analysis...")
                    loop = aio.new_event_loop()
                    aio.set_event_loop(loop)

                    class FakeArgs:
                        stocks = None
                        dry_run = False
                    loop.run_until_complete(run_analysis(FakeArgs(), settings))
                    loop.close()
                    time.sleep(60)  # avoid double-trigger
                time.sleep(30)

        t = threading.Thread(target=scheduler, daemon=True)
        t.start()

    log.info(f"Web UI starting at http://127.0.0.1:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


def main():
    args     = parse_args()
    settings = Settings()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.webui_only:
        start_webui(args.port, with_scheduler=False, settings=settings)
        return

    if args.webui:
        start_webui(args.port, with_scheduler=True, settings=settings)
        return

    if args.market_review:
        asyncio.run(run_market_review(args, settings))
        return

    if args.backtest:
        asyncio.run(run_backtest())
        return

    asyncio.run(run_analysis(args, settings))


if __name__ == "__main__":
    main()
