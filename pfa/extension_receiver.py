"""
PFA 扩展数据接收器 — 接收 Chrome 扩展推送的雪球数据

启动: python3 -m pfa.extension_receiver
端口: 8765

接收来自 PFA 雪球助手扩展的 POST 请求，将数据写入统一数据层。
"""

from __future__ import annotations

import hashlib
import json
import sys
import threading
from datetime import datetime, timedelta, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pfa.data.store import FeedItem, save_feed_items

CST = timezone(timedelta(hours=8))
PORT = 8765


class ReceiverHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")

        try:
            data = json.loads(body)
            items = data.get("items", [])
            feed_items = _convert_to_feed_items(items)
            if feed_items:
                path = save_feed_items(feed_items, source_label="xueqiu_ext")
                print(f"[RECV] {len(feed_items)} items saved → {path}")
            self._respond(200, {"status": "ok", "count": len(feed_items)})
        except Exception as e:
            print(f"[RECV] Error: {e}")
            self._respond(400, {"status": "error", "error": str(e)})

    def do_OPTIONS(self):
        self._respond(200, "")

    def _respond(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        if body:
            self.wfile.write(json.dumps(body, ensure_ascii=False).encode())

    def log_message(self, format, *args):
        pass  # suppress default logging


def _convert_to_feed_items(items: List[Dict]) -> List[FeedItem]:
    now = datetime.now(CST).isoformat()
    result = []
    for it in items:
        source = it.get("source", "xueqiu")
        title = it.get("title", "") or it.get("text", "")[:60]
        text = it.get("text", it.get("content", ""))[:300]
        url = ""
        target = it.get("target", "")
        if target:
            url = f"https://xueqiu.com{target}"
        elif it.get("url"):
            url = it["url"]

        fid = hashlib.md5((url or title or text[:50]).encode()).hexdigest()[:12]

        result.append(FeedItem(
            id=fid,
            title=title[:100] if title else text[:60],
            url=url,
            published_at=it.get("created_at", ""),
            content_snippet=text,
            source=source,
            source_id=it.get("user", it.get("user_id", "")),
            symbol=it.get("symbol", ""),
            symbol_name="",
            market="",
            fetched_at=now,
        ))
    return result


def start_server(port: int = PORT):
    server = HTTPServer(("0.0.0.0", port), ReceiverHandler)
    print(f"[PFA Extension Receiver] Listening on :{port}")
    server.serve_forever()


if __name__ == "__main__":
    start_server()
