#!/usr/bin/env python3
"""定时同步汇率到 DB。可加入 cron 每日执行。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.services.fx_service import sync_fx_rates

if __name__ == "__main__":
    rates = sync_fx_rates()
    print(f"FX synced: USD={rates.get('USD')}, HKD={rates.get('HKD')}")
