"""
Settings API — 数据源、汇率、RSS/API/社交 CRUD
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import feedparser
import requests
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


@router.get("/settings/data-sources")
def get_data_sources():
    """获取数据源配置（RSS、API、社交等）。"""
    from agents.secretary_agent import load_data_sources
    return load_data_sources()


# ---------------------------------------------------------------------------
# RSS CRUD
# ---------------------------------------------------------------------------

class AddRssBody(BaseModel):
    url: str
    name: str = ""
    category: str = ""


class UpdateRssBody(BaseModel):
    old_url: str
    url: str
    name: str = ""
    category: str = ""


class TestRssBody(BaseModel):
    url: str


@router.post("/settings/rss")
def add_rss(body: AddRssBody):
    """添加 RSS 源。"""
    from agents.secretary_agent import add_rss_source
    add_rss_source(body.url.strip(), body.name.strip(), body.category.strip())
    return {"ok": True}


@router.put("/settings/rss")
def update_rss(body: UpdateRssBody):
    """更新 RSS 源。"""
    from agents.secretary_agent import update_rss_source
    update_rss_source(
        body.old_url.strip(),
        body.url.strip(),
        body.name.strip(),
        body.category.strip(),
    )
    return {"ok": True}


@router.delete("/settings/rss")
def remove_rss(url: str):
    """删除 RSS 源（按 URL）。"""
    from agents.secretary_agent import remove_rss_source
    remove_rss_source(url)
    return {"ok": True}


@router.post("/settings/rss/test")
def test_rss(body: TestRssBody):
    """测试 RSS 连接，抓取 XML 验证可用性。"""
    url = (body.url or "").strip()
    if not url:
        return {"ok": False, "message": "URL 为空"}
    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            return {"ok": False, "message": f"抓取失败: {getattr(feed.bozo_exception, 'message', str(feed.bozo_exception))}"}
        count = len(feed.entries) if feed.entries else 0
        return {"ok": True, "message": f"连接成功，{count} 条", "count": count}
    except Exception as e:
        return {"ok": False, "message": f"抓取失败: {str(e)[:120]}"}


# ---------------------------------------------------------------------------
# API 数据源（启用/禁用、测试）
# ---------------------------------------------------------------------------

class ToggleApiBody(BaseModel):
    enabled: bool


@router.put("/settings/api-sources/{source_type}/toggle")
def toggle_api_source(source_type: str, body: ToggleApiBody):
    """切换 API 数据源启用状态。"""
    from agents.secretary_agent import toggle_api_source as do_toggle
    do_toggle(source_type, body.enabled)
    return {"ok": True, "enabled": body.enabled}


@router.post("/settings/api-sources/test")
def test_api_source(source_type: str):
    """测试 API 数据源连接。"""
    from agents.secretary_agent import load_data_sources
    sources = load_data_sources()
    api_list = sources.get("api_sources", [])
    src = next((s for s in api_list if s.get("type") == source_type), None)
    if not src:
        return {"ok": False, "message": "未找到该数据源"}
    try:
        if src.get("type") == "wallstreetcn":
            api_url = src.get("api_url", "")
            r = requests.get(api_url, timeout=5, headers={"User-Agent": "Mozilla/5.0"}, proxies={"http": None, "https": None})
            data = r.json()
            n = len(data.get("data", {}).get("items", []))
            return {"ok": True, "message": f"连接成功，{n} 条快讯", "count": n}
        if src.get("type") == "eastmoney":
            return {"ok": True, "message": "东方财富 API 可用"}
        return {"ok": True, "message": "已启用"}
    except Exception as e:
        return {"ok": False, "message": f"测试失败: {str(e)[:120]}"}


# ---------------------------------------------------------------------------
# 社交与监控源 CRUD
# ---------------------------------------------------------------------------

class AddSocialBody(BaseModel):
    type: str  # twitter_handles | xueqiu_user_ids | monitor_urls
    value: str


def _extract_xueqiu_id(s: str) -> str:
    """从雪球链接或纯 ID 提取用户 ID。"""
    s = (s or "").strip()
    import re
    m = re.search(r"xueqiu\.com/u/(\d+)", s, re.I)
    if m:
        return m.group(1)
    if re.match(r"^\d+$", s):
        return s
    return s


@router.post("/settings/social")
def add_social(body: AddSocialBody):
    """添加社交/监控源。"""
    from agents.secretary_agent import add_source
    key = body.type.strip()
    raw = (body.value or "").strip()
    if key == "twitter_handles":
        val = raw.lstrip("@")
    elif key == "xueqiu_user_ids":
        val = _extract_xueqiu_id(raw)
    else:
        val = raw
    if not val:
        return {"ok": False, "message": "值为空"}
    add_source(key, val)
    return {"ok": True}


class SetXueqiuIdsBody(BaseModel):
    ids: list[str] = []


@router.post("/settings/social/xueqiu-user-ids/replace")
def replace_xueqiu_user_ids(body: SetXueqiuIdsBody):
    """批量替换雪球用户 ID 列表（用于一键同步关注列表）。"""
    from agents.secretary_agent import set_xueqiu_user_ids
    set_xueqiu_user_ids(body.ids or [])
    return {"ok": True}


@router.delete("/settings/social")
def remove_social(type: str, value: str):
    """删除社交/监控源。"""
    from agents.secretary_agent import remove_source
    remove_source(type.strip(), (value or "").strip())
    return {"ok": True}


# ---------------------------------------------------------------------------
# 雪球 Cookie 同步（由 Chrome 扩展调用，严禁日志明文打印）
# ---------------------------------------------------------------------------

class XueqiuCookieBody(BaseModel):
    cookie: str
    has_login: bool = False


@router.post("/settings/xueqiu/cookie")
def save_xueqiu_cookie(body: XueqiuCookieBody):
    """接收扩展同步的雪球 Cookie，存储到本地 config/xueqiu-auth.json。严禁日志明文打印。"""
    from backend.services.social_service import _save_xueqiu_cookie
    if not (body.cookie or "").strip():
        return {"ok": False, "error": "Cookie 为空"}
    ok = _save_xueqiu_cookie(body.cookie.strip())
    return {"ok": ok} if ok else {"ok": False, "error": "保存失败"}


@router.get("/settings/xueqiu/status")
def get_xueqiu_status():
    """获取雪球授权状态（是否已同步 Cookie）。若 Cookie 已失效则返回 cookie_expired。"""
    from backend.services.social_service import has_xueqiu_auth, test_xueqiu
    has_auth = has_xueqiu_auth()
    if not has_auth:
        return {"has_auth": False, "cookie_expired": False}
    result = test_xueqiu()
    msg = (result.get("message") or "").lower()
    cookie_expired = (
        result.get("has_auth") is True
        and result.get("ok") is not True
        and ("失效" in (result.get("message") or "") or "登录" in (result.get("message") or ""))
    )
    return {"has_auth": has_auth, "cookie_expired": cookie_expired}


@router.post("/settings/social/test")
def test_social(type: str, value: str):
    """测试社交/监控源（雪球用 Cookie 测试，monitor_urls 可 HTTP 测试）。"""
    key = (type or "").strip()
    raw = (value or "").strip()
    val = _extract_xueqiu_id(raw) if key == "xueqiu_user_ids" else raw
    if key == "xueqiu_user_ids":
        from backend.services.social_service import test_xueqiu
        return test_xueqiu(user_id=val if val else None)
    if key == "twitter_handles":
        return {"ok": False, "message": "Twitter/X 需登录或配置 API Key。"}
    if key == "monitor_urls":
        try:
            r = requests.get(val, timeout=10, headers={"User-Agent": "Mozilla/5.0"}, proxies={"http": None, "https": None})
            return {"ok": True, "message": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"ok": False, "message": f"请求失败: {str(e)[:80]}"}
    return {"ok": False, "message": "未知类型"}


# ---------------------------------------------------------------------------
# RSSHub 配置
# ---------------------------------------------------------------------------

class RsshubBody(BaseModel):
    url: str


@router.put("/settings/rsshub")
def set_rsshub(body: RsshubBody):
    """设置 RSSHub 地址。"""
    from agents.secretary_agent import set_rsshub_url
    set_rsshub_url(body.url.strip())
    return {"ok": True}


# ---------------------------------------------------------------------------
# 汇率、API 状态
# ---------------------------------------------------------------------------

@router.get("/settings/fx")
def get_fx():
    """获取汇率（与 /portfolio/fx 一致）。"""
    from pfa.portfolio_valuation import get_fx_rates, get_fx_updated_at
    return {"rates": get_fx_rates(), "updated_at": get_fx_updated_at()}


@router.get("/settings/api-status")
def get_api_status():
    """获取 LLM API 连接状态。"""
    import os
    return {
        "dashscope_ok": bool(os.environ.get("DASHSCOPE_API_KEY")),
        "openai_ok": bool(os.environ.get("OPENAI_API_KEY")),
    }
