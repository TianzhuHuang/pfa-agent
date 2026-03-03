#!/usr/bin/env python3
"""
将 config/data-sources.json 迁移到 Supabase user_settings.data_sources

用法:
  python scripts/migrate_data_sources_to_supabase.py <user_id>

需要环境变量: SUPABASE_URL, SUPABASE_SERVICE_KEY
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA_SOURCES_PATH = ROOT / "config" / "data-sources.json"


def main():
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not user_id:
        print("用法: python scripts/migrate_data_sources_to_supabase.py <user_id>")
        sys.exit(1)

    if not DATA_SOURCES_PATH.exists():
        print(f"未找到 {DATA_SOURCES_PATH}")
        sys.exit(1)

    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("需要 SUPABASE_URL 和 SUPABASE_SERVICE_KEY")
        sys.exit(1)

    with open(DATA_SOURCES_PATH, "r", encoding="utf-8") as f:
        sources = json.load(f)

    from supabase import create_client
    sb = create_client(url, key)
    sb.table("user_settings").upsert(
        {"user_id": user_id, "data_sources": sources},
        on_conflict="user_id",
    ).execute()

    print(f"已迁移 data_sources 到 user {user_id}")


if __name__ == "__main__":
    main()
