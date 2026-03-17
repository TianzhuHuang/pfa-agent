#!/usr/bin/env python3
"""
Local smoke tests for Scout→Analyst→Auditor pipeline.

Usage:
  python3 scripts/smoke_pipeline.py --hours 24
  python3 scripts/smoke_pipeline.py --hours 24 --audit
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()

    from agents.secretary_agent import load_portfolio, run_full_pipeline

    p = load_portfolio()
    holdings = p.get("holdings", [])
    if not holdings:
        print("[SMOKE] no holdings, skipped")
        return 2

    r = run_full_pipeline(holdings, hours=args.hours, do_audit=args.audit)
    print(json.dumps({"status": r.get("status"), "has_scout": bool(r.get("scout_result")), "has_analyst": bool(r.get("analyst_result")), "has_auditor": bool(r.get("auditor_result"))}, ensure_ascii=False))
    return 0 if r.get("status") in ("ok", "partial") else 1


if __name__ == "__main__":
    raise SystemExit(main())

