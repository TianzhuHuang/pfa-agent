"""
PFA 定时任务调度器

定时运行 Scout → Analyst 流水线，生成晨报并推送到 Telegram。

用法:
  python -m pfa.scheduler                    # 启动调度器（后台运行）
  python -m pfa.scheduler --run-now          # 立即执行一次
  python -m pfa.scheduler --cron "0 8 * * *" # 自定义 cron 表达式
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CST = timezone(timedelta(hours=8))


def run_morning_briefing(push_telegram: bool = True) -> dict:
    """Execute the full morning briefing pipeline.

    1. Load portfolio
    2. Scout → fetch all news
    3. Analyst → structured briefing
    4. (Optional) Push to Telegram
    """
    from agents.secretary_agent import load_portfolio, run_full_pipeline
    from pfa.telegram_push import push_briefing

    now = datetime.now(CST)
    print(f"[SCHEDULER] {now.strftime('%Y-%m-%d %H:%M:%S')} Starting morning briefing...")

    portfolio = load_portfolio()
    holdings = portfolio.get("holdings", [])
    if not holdings:
        print("[SCHEDULER] No holdings configured. Skipping.")
        return {"status": "skipped", "reason": "no holdings"}

    result = run_full_pipeline(holdings, hours=24, do_audit=False)

    briefing = None
    if result.get("analyst_result"):
        briefing = result["analyst_result"].get("briefing")
        if not briefing:
            try:
                briefing = json.loads(result["analyst_result"].get("analysis", "{}"))
            except (json.JSONDecodeError, TypeError):
                pass

    if push_telegram and briefing:
        push_briefing(briefing)

    scout_total = (result.get("scout_result") or {}).get("total", 0)
    print(f"[SCHEDULER] Done. Scout: {scout_total} items, "
          f"Briefing: {'OK' if briefing else 'FAILED'}, "
          f"Telegram: {'pushed' if push_telegram and briefing else 'skipped'}")

    return {
        "status": result.get("status", "error"),
        "scout_total": scout_total,
        "has_briefing": bool(briefing),
        "telegram_pushed": push_telegram and bool(briefing),
    }


def start_scheduler(cron_expr: str = "0 8 * * *"):
    """Start APScheduler with a cron job for morning briefing.

    Default: every day at 8:00 AM (CST).
    """
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")

    parts = cron_expr.split()
    trigger = CronTrigger(
        minute=parts[0] if len(parts) > 0 else "0",
        hour=parts[1] if len(parts) > 1 else "8",
        day=parts[2] if len(parts) > 2 else "*",
        month=parts[3] if len(parts) > 3 else "*",
        day_of_week=parts[4] if len(parts) > 4 else "*",
        timezone="Asia/Shanghai",
    )

    scheduler.add_job(run_morning_briefing, trigger, id="morning_briefing",
                      name="PFA Morning Briefing")

    print(f"[SCHEDULER] Started. Cron: {cron_expr} (Asia/Shanghai)")
    print(f"[SCHEDULER] Next run: {scheduler.get_job('morning_briefing').next_run_time}")
    print("[SCHEDULER] Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("[SCHEDULER] Stopped.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PFA Scheduler")
    parser.add_argument("--run-now", action="store_true", help="Run once immediately")
    parser.add_argument("--cron", default="0 8 * * *", help="Cron expression (default: 0 8 * * *)")
    parser.add_argument("--no-telegram", action="store_true", help="Skip Telegram push")
    args = parser.parse_args()

    if args.run_now:
        run_morning_briefing(push_telegram=not args.no_telegram)
    else:
        start_scheduler(args.cron)
