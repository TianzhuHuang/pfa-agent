"""
Supabase 数据层 — 当 SUPABASE_URL + SUPABASE_SERVICE_KEY 配置时使用

与 portfolio_service、chat_service 相同接口，读写 Supabase PostgreSQL。
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional


def _get_client():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
    return create_client(url, key)


def use_supabase() -> bool:
    """是否使用 Supabase（环境变量已配置）。"""
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    return bool(url and key)


def load_portfolio_db(user_id: str = "admin") -> Dict[str, Any]:
    """从 Supabase 加载组合。"""
    sb = _get_client()
    uid = user_id or "admin"

    data = {
        "version": "1.0",
        "holdings": [],
        "accounts": [],
        "channels": {"rss_urls": [], "xueqiu_user_ids": [], "twitter_handles": []},
        "preferences": {},
    }

    r = sb.table("holdings").select("*").eq("user_id", uid).execute()
    for row in r.data or []:
        ho = {
            "symbol": row.get("symbol", ""),
            "name": row.get("name") or "",
            "market": row.get("market") or "A",
            "quantity": float(row.get("quantity", 0) or 0),
            "cost_price": float(row["cost_price"]) if row.get("cost_price") is not None else None,
            "currency": row.get("currency"),
            "exchange": row.get("exchange"),
            "account": row.get("account") or "默认",
            "source": row.get("source") or "manual",
            "position_pct": float(row["position_pct"]) if row.get("position_pct") is not None else None,
            "memo_history": row.get("memo_history") or [],
            "updated_at": row.get("updated_at"),
        }
        if row.get("ocr_confirmed") is not None:
            ho["ocr_confirmed"] = bool(row["ocr_confirmed"])
        if row.get("price_deviation_warn") is not None:
            ho["price_deviation_warn"] = bool(row["price_deviation_warn"])
        data["holdings"].append(ho)

    r = sb.table("accounts").select("*").eq("user_id", uid).execute()
    for row in r.data or []:
        data["accounts"].append({
            "id": row.get("account_id", ""),
            "name": row.get("name", ""),
            "base_currency": row.get("base_currency") or "CNY",
            "broker": row.get("broker") or "",
            "account_type": row.get("account_type") or "股票",
            "balance": float(row.get("balance", 0) or 0),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        })

    r = sb.table("portfolio_meta").select("*").eq("user_id", uid).execute()
    for row in r.data or []:
        if row.get("meta_key") == "channels" and row.get("meta_value"):
            data["channels"] = row["meta_value"]
        elif row.get("meta_key") == "preferences" and row.get("meta_value"):
            data["preferences"] = row["meta_value"]

    return data


def save_portfolio_db(data: Dict[str, Any], user_id: str = "admin") -> None:
    """保存组合到 Supabase。"""
    sb = _get_client()
    uid = user_id or "admin"

    sb.table("holdings").delete().eq("user_id", uid).execute()
    sb.table("accounts").delete().eq("user_id", uid).execute()
    sb.table("portfolio_meta").delete().eq("user_id", uid).execute()

    for h in data.get("holdings", []):
        sym = str(h.get("symbol", "")).strip()
        if not sym:
            continue
        ins = {
            "user_id": uid,
            "symbol": sym,
            "name": str(h.get("name", "")).strip() or None,
            "market": str(h.get("market", "A"))[:2] or "A",
            "quantity": float(h.get("quantity", 0) or 0),
            "cost_price": float(h["cost_price"]) if h.get("cost_price") is not None else None,
            "currency": h.get("currency"),
            "exchange": h.get("exchange"),
            "account": str(h.get("account", "默认")).strip() or "默认",
            "source": str(h.get("source", "manual")).strip() or "manual",
            "position_pct": float(h["position_pct"]) if h.get("position_pct") is not None else None,
            "memo_history": h.get("memo_history"),
        }
        if h.get("ocr_confirmed") is not None:
            ins["ocr_confirmed"] = bool(h["ocr_confirmed"])
        if h.get("price_deviation_warn") is not None:
            ins["price_deviation_warn"] = bool(h["price_deviation_warn"])
        sb.table("holdings").insert(ins).execute()

    for a in data.get("accounts", []):
        aid = str(a.get("id", a.get("name", ""))).strip()
        if not aid:
            continue
        sb.table("accounts").insert({
            "user_id": uid,
            "account_id": aid,
            "name": str(a.get("name", aid)).strip(),
            "base_currency": str(a.get("base_currency", a.get("currency", "CNY"))).strip().upper() or "CNY",
            "broker": str(a.get("broker", "")).strip() or None,
            "account_type": str(a.get("account_type", "股票")).strip() or "股票",
            "balance": float(a.get("balance", 0) or 0),
        }).execute()

    ch = data.get("channels", {})
    pref = data.get("preferences", {})
    if ch or pref:
        for meta_key, meta_value in [("channels", ch), ("preferences", pref)]:
            if meta_value:
                sb.table("portfolio_meta").delete().eq("user_id", uid).eq("meta_key", meta_key).execute()
                sb.table("portfolio_meta").insert({
                    "user_id": uid,
                    "meta_key": meta_key,
                    "meta_value": meta_value,
                }).execute()


def load_chat_history(user_id: str = "admin") -> List[Dict[str, Any]]:
    """从 Supabase 加载对话历史。"""
    sb = _get_client()
    uid = user_id or "admin"
    r = sb.table("chat_messages").select("role,content").eq("user_id", uid).order("created_at").limit(200).execute()
    return [{"role": row.get("role", "assistant"), "content": row.get("content", "")} for row in (r.data or [])]


def save_chat_history(messages: List[Dict[str, Any]], user_id: str = "admin") -> None:
    """保存对话到 Supabase。"""
    sb = _get_client()
    uid = user_id or "admin"
    sb.table("chat_messages").delete().eq("user_id", uid).execute()
    for m in messages[-200:]:
        content = (m.get("content", "") or "").replace("\r\n", "\n").replace("\r", "\n")
        sb.table("chat_messages").insert({
            "user_id": uid,
            "role": m.get("role", "assistant"),
            "content": content,
        }).execute()


def save_briefing_report(result: dict, user_id: str = "admin") -> Optional[dict]:
    """保存晨报到 Supabase。"""
    import json
    from datetime import datetime, date, time, timedelta

    ar = result.get("analyst_result", {})
    briefing = ar.get("briefing")
    if not briefing and ar.get("analysis"):
        try:
            briefing = json.loads(ar.get("analysis", "{}"))
        except (json.JSONDecodeError, TypeError):
            pass
    if not briefing:
        return None

    one_liner = (briefing.get("one_liner") or "").strip()
    summary = (one_liner[:20] + ("..." if len(one_liner) > 20 else "")) if one_liner else "投研晨报"
    content = json.dumps(briefing, ensure_ascii=False)
    today = date.today()
    report_dt = datetime.combine(today, time.min).isoformat()

    sb = _get_client()
    uid = user_id or "admin"

    r = sb.table("briefing_reports").select("id").eq("user_id", uid).gte(
        "report_date", report_dt
    ).lt("report_date", (datetime.combine(today, time.min) + timedelta(days=1)).isoformat()).execute()

    if r.data and len(r.data) > 0:
        sb.table("briefing_reports").update({
            "content": content,
            "summary": summary,
        }).eq("id", r.data[0]["id"]).execute()
        return r.data[0]

    r = sb.table("briefing_reports").insert({
        "user_id": uid,
        "report_date": report_dt,
        "content": content,
        "summary": summary,
    }).execute()
    return r.data[0] if r.data else None


def list_briefing_reports(
    user_id: str = "admin",
    limit: int = 30,
    offset: int = 0,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    include_content: bool = False,
) -> List[dict]:
    """按日期倒序返回晨报列表。"""
    from datetime import datetime, timedelta

    sb = _get_client()
    uid = user_id or "admin"
    q = sb.table("briefing_reports").select("*").eq("user_id", uid)
    if from_date:
        try:
            q = q.gte("report_date", datetime.strptime(from_date, "%Y-%m-%d").isoformat())
        except ValueError:
            pass
    if to_date:
        try:
            q = q.lt("report_date", (datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)).isoformat())
        except ValueError:
            pass
    r = q.order("report_date", desc=True).range(offset, offset + limit - 1).execute()
    out = []
    for row in r.data or []:
        d = {
            "id": row.get("id"),
            "date": row.get("report_date", "")[:10] if row.get("report_date") else None,
            "content": row.get("content") if include_content else None,
            "summary": row.get("summary") or "",
            "created_at": row.get("created_at"),
        }
        if not include_content:
            d.pop("content", None)
        out.append(d)
    return out


def _default_data_sources() -> dict:
    return {
        "rss_urls": [],
        "api_sources": [
            {"type": "eastmoney", "name": "东方财富-个股新闻", "category": "深度分析", "mode": "per_stock", "enabled": True},
            {"type": "wallstreetcn", "name": "华尔街见闻-全球快讯", "category": "宏观与快讯", "mode": "global", "enabled": True, "api_url": "https://api-one.wallstcn.com/apiv1/content/lives?channel=global-channel&limit=20"},
        ],
        "twitter_handles": [],
        "xueqiu_user_ids": [],
        "monitor_urls": [],
        "unavailable_sources": [],
        "self_hosted_rsshub": "",
    }


def get_data_sources(user_id: str = "admin") -> dict:
    """从 user_settings 加载数据源配置。"""
    sb = _get_client()
    uid = user_id or "admin"
    r = sb.table("user_settings").select("data_sources").eq("user_id", uid).execute()
    if r.data and len(r.data) > 0 and r.data[0].get("data_sources"):
        out = _default_data_sources()
        out.update(r.data[0]["data_sources"])
        return out
    return _default_data_sources()


def save_data_sources(sources: dict, user_id: str = "admin") -> None:
    """保存数据源配置到 user_settings。"""
    sb = _get_client()
    uid = user_id or "admin"
    sb.table("user_settings").upsert(
        {"user_id": uid, "data_sources": sources},
        on_conflict="user_id",
    ).execute()


def get_briefing_by_id(report_id, user_id: str = "admin") -> Optional[dict]:
    """按 ID 获取单条晨报。"""
    sb = _get_client()
    uid = user_id or "admin"
    r = sb.table("briefing_reports").select("*").eq("id", report_id).eq("user_id", uid).execute()
    if r.data and len(r.data) > 0:
        row = r.data[0]
        return {
            "id": row.get("id"),
            "date": row.get("report_date", "")[:10] if row.get("report_date") else None,
            "content": row.get("content"),
            "summary": row.get("summary") or "",
            "created_at": row.get("created_at"),
        }
    return None
