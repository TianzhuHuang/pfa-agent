"""
社交数据源服务 — 雪球、X.com 连接与测试

雪球 Cookie 存储于 config/xueqiu-auth.json（不提交到 git），严禁日志明文打印。
"""

import json
import base64
from pathlib import Path
from typing import Optional, Dict, Any

ROOT = Path(__file__).resolve().parent.parent.parent
XUEQIU_AUTH_PATH = ROOT / "config" / "xueqiu-auth.json"


def _load_xueqiu_cookie() -> Optional[str]:
    """从本地文件读取雪球 Cookie，不记录日志。"""
    if not XUEQIU_AUTH_PATH.exists():
        return None
    try:
        with open(XUEQIU_AUTH_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("cookie") or data.get("cookie_b64")
        if raw:
            if data.get("encoded"):
                return base64.b64decode(raw).decode("utf-8", errors="replace")
            return raw
    except Exception:
        pass
    return None


def _save_xueqiu_cookie(cookie: str) -> bool:
    """保存雪球 Cookie 到本地，使用 base64 编码降低明文暴露。"""
    try:
        XUEQIU_AUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
        encoded = base64.b64encode(cookie.encode("utf-8")).decode("ascii")
        with open(XUEQIU_AUTH_PATH, "w", encoding="utf-8") as f:
            json.dump({"cookie_b64": encoded, "encoded": True}, f, indent=2)
        return True
    except Exception:
        return False


def has_xueqiu_auth() -> bool:
    """是否已配置雪球 Cookie。"""
    return bool(_load_xueqiu_cookie())


class XueqiuClient:
    """雪球 API 客户端，使用扩展同步的 Cookie。"""

    def __init__(self):
        self._cookie = _load_xueqiu_cookie()
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://xueqiu.com/",
            "Origin": "https://xueqiu.com",
        }
        if self._cookie:
            self._headers["Cookie"] = self._cookie

    def test_connection(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """测试雪球连接。优先用 stock.xueqiu.com 行情接口（限制较松），失败则尝试 user_timeline。"""
        if not self._cookie:
            return {"ok": False, "message": "需要登录", "has_auth": False}

        uid = (user_id or "").strip() or "9650668145"
        try:
            import requests
            # 优先用 stock 行情接口，对 Cookie 校验通常更宽松
            resp = requests.get(
                "https://stock.xueqiu.com/v5/stock/quote.json",
                params={"symbol": "SH600519"},
                headers={**self._headers, "Referer": "https://stock.xueqiu.com/"},
                timeout=10,
                proxies={"http": None, "https": None},
            )
            if resp.status_code == 200:
                text = (resp.text or "").strip()
                if text and not text.startswith("<"):
                    try:
                        data = json.loads(text)
                        if "data" in data or "quote" in data or data.get("error_code") is None:
                            return {"ok": True, "message": "连接成功", "has_auth": True}
                    except json.JSONDecodeError:
                        pass
            # 回退：尝试 user_timeline
            resp = requests.get(
                "https://xueqiu.com/v4/statuses/user_timeline.json",
                params={"user_id": uid, "page": 1, "type": 0, "count": 1},
                headers=self._headers,
                timeout=10,
                proxies={"http": None, "https": None},
            )
            if resp.status_code == 200:
                text = (resp.text or "").strip()
                if not text:
                    return {"ok": False, "message": "雪球返回空响应，请重新同步 Cookie", "has_auth": True}
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    if text.startswith("<") or "html" in (resp.headers.get("Content-Type") or "").lower():
                        return {"ok": False, "message": "雪球返回登录页，Cookie 已失效，请重新同步", "has_auth": True}
                    return {"ok": False, "message": "雪球返回非 JSON 数据，请重新同步 Cookie", "has_auth": True}
                if "statuses" in data or "list" in data:
                    return {"ok": True, "message": "连接成功", "has_auth": True}
                if "error_code" in data or "error_description" in data:
                    return {"ok": False, "message": "Cookie 已失效，请重新同步", "has_auth": True}
            return {"ok": False, "message": f"HTTP {resp.status_code}", "has_auth": True}
        except Exception as e:
            msg = str(e)[:80]
            if "Expecting value" in msg or "JSON" in msg:
                return {"ok": False, "message": "雪球返回非 JSON 数据，Cookie 可能已失效，请重新同步", "has_auth": True}
            return {"ok": False, "message": msg, "has_auth": True}


def fetch_xueqiu_user_timeline(user_id: str, count: int = 20) -> list:
    """抓取雪球用户动态。返回 statuses 列表，失败返回 []。"""
    client = XueqiuClient()
    if not client._cookie:
        return []
    try:
        import requests
        resp = requests.get(
            "https://xueqiu.com/v4/statuses/user_timeline.json",
            params={"user_id": user_id.strip(), "page": 1, "type": 0, "count": count},
            headers=client._headers,
            timeout=15,
            proxies={"http": None, "https": None},
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        statuses = data.get("statuses") or data.get("list") or []
        return statuses if isinstance(statuses, list) else []
    except Exception:
        return []


def test_xueqiu(user_id: Optional[str] = None) -> Dict[str, Any]:
    """测试雪球连接。user_id 为可选，用于测试指定用户动态；无则用默认账号。"""
    return XueqiuClient().test_connection(user_id=user_id)


def test_twitter(handle: str) -> Dict[str, Any]:
    """X.com/Twitter 测试：需登录或 API Key。"""
    return {"ok": False, "message": "Twitter/X 需登录或配置 API Key", "has_auth": False}
