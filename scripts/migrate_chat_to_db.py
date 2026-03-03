#!/usr/bin/env python3
"""
将对话历史从 JSON 迁移到 SQLite。

用法：python scripts/migrate_chat_to_db.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pfa.data.store import load_chat_history as load_json
from backend.database.session import init_db
from backend.database.models import ChatMessage
from backend.database.session import get_session


def main():
    init_db()
    msgs = load_json("admin")
    if not msgs:
        print("无 JSON 对话记录，跳过迁移")
        return
    db = get_session()
    try:
        db.query(ChatMessage).filter(ChatMessage.user_id == "admin").delete()
        for m in msgs[-200:]:
            role = m.get("role", "assistant")
            content = (m.get("content", "") or "").replace("\r\n", "\n").replace("\r", "\n")
            db.add(ChatMessage(user_id="admin", role=role, content=content))
        db.commit()
        print(f"已迁移 {len(msgs)} 条对话到 data/pfa.db")
    finally:
        db.close()


if __name__ == "__main__":
    main()
