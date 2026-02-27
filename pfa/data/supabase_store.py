"""
Supabase 数据层 — 替代本地 JSON 存储

与 store.py 同接口，通过 user_id 实现数据隔离。
RLS 策略确保用户只能访问自己的数据。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

CST = timezone(timedelta(hours=8))


_cached_client = None

def _get_client():
    """Get base Supabase client (anon key, for auth operations)."""
    global _cached_client
    if _cached_client is not None:
        return _cached_client
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        return None
    _cached_client = create_client(url, key)
    return _cached_client


def _get_auth_client(access_token: str = ""):
    """Get authenticated client (for RLS-protected operations).
    
    If access_token provided, sets the session so RLS policies work.
    Falls back to anon client if no token.
    """
    client = _get_client()
    if not client:
        return None
    if access_token:
        try:
            client.postgrest.auth(access_token)
        except Exception:
            pass
    return client


def _auth_client(access_token: str):
    """Get Supabase client with user auth token for RLS."""
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        return None
    client = create_client(url, key)
    client.auth.set_session(access_token, "")
    return client


def is_available() -> bool:
    """Check if Supabase is configured and reachable."""
    try:
        client = _get_client()
        if client is None:
            return False
        client.table("holdings").select("id").limit(0).execute()
        return True
    except Exception:
        return False


# ===================================================================
# Auth helpers
# ===================================================================

def sign_up(email: str, password: str) -> Dict[str, Any]:
    """Register a new user. Auto sign-in after registration."""
    client = _get_client()
    if not client:
        return {"error": "Supabase not configured"}
    try:
        resp = client.auth.sign_up({"email": email, "password": password})
        if resp.user and resp.session:
            # Auto sign-in (email confirm not required in dev)
            return {
                "ok": True,
                "user_id": str(resp.user.id),
                "email": resp.user.email,
                "access_token": resp.session.access_token,
                "refresh_token": resp.session.refresh_token,
            }
        elif resp.user:
            # Email confirm required — try auto sign-in
            try:
                login = client.auth.sign_in_with_password({"email": email, "password": password})
                if login.user and login.session:
                    return {
                        "ok": True,
                        "user_id": str(login.user.id),
                        "email": login.user.email,
                        "access_token": login.session.access_token,
                        "refresh_token": login.session.refresh_token,
                    }
            except Exception:
                pass
            return {"ok": True, "user_id": str(resp.user.id), "email": resp.user.email,
                    "needs_confirm": True}
        return {"error": "注册失败"}
    except Exception as e:
        msg = str(e)
        if "already registered" in msg.lower():
            return {"error": "该邮箱已注册，请直接登录"}
        return {"error": msg}


def sign_in(email: str, password: str) -> Dict[str, Any]:
    """Sign in an existing user."""
    client = _get_client()
    if not client:
        return {"error": "Supabase not configured"}
    try:
        resp = client.auth.sign_in_with_password({"email": email, "password": password})
        if resp.user and resp.session:
            return {
                "ok": True,
                "user_id": str(resp.user.id),
                "email": resp.user.email,
                "access_token": resp.session.access_token,
                "refresh_token": resp.session.refresh_token,
            }
        return {"error": "Login failed"}
    except Exception as e:
        return {"error": str(e)}


def sign_out():
    """Sign out current user."""
    client = _get_client()
    if client:
        try:
            client.auth.sign_out()
        except Exception:
            pass


# ===================================================================
# Holdings CRUD
# ===================================================================

def save_holdings(user_id: str, holdings: List[Dict], access_token: str = "") -> bool:
    """Replace all holdings for a user."""
    client = _get_auth_client(access_token)
    if not client:
        return False
    try:
        # Delete existing
        client.table("holdings").delete().eq("user_id", user_id).execute()
        # Insert new
        rows = []
        for h in holdings:
            rows.append({
                "user_id": user_id,
                "symbol": h.get("symbol", ""),
                "name": h.get("name", ""),
                "market": h.get("market", "A"),
                "cost_price": h.get("cost_price", 0),
                "quantity": h.get("quantity", 0),
                "position_pct": h.get("position_pct", 0),
                "account": h.get("account", ""),
                "source": h.get("source", "manual"),
                "memo_history": json.dumps(h.get("memo_history", []), ensure_ascii=False),
                "updated_at": h.get("updated_at", datetime.now(CST).isoformat()),
            })
        if rows:
            client.table("holdings").insert(rows).execute()
        return True
    except Exception as e:
        print(f"[SUPABASE] save_holdings error: {e}")
        return False


def load_holdings(user_id: str, access_token: str = "") -> List[Dict]:
    """Load all holdings for a user."""
    client = _get_auth_client(access_token)
    if not client:
        return []
    try:
        resp = client.table("holdings").select("*").eq("user_id", user_id).execute()
        holdings = []
        for row in resp.data:
            h = {
                "symbol": row["symbol"],
                "name": row.get("name", ""),
                "market": row.get("market", "A"),
                "source": row.get("source", "manual"),
                "updated_at": row.get("updated_at", ""),
            }
            if row.get("cost_price"):
                h["cost_price"] = float(row["cost_price"])
            if row.get("quantity"):
                h["quantity"] = float(row["quantity"])
            if row.get("account"):
                h["account"] = row["account"]
            memo = row.get("memo_history")
            if memo:
                if isinstance(memo, str):
                    h["memo_history"] = json.loads(memo)
                else:
                    h["memo_history"] = memo
            holdings.append(h)
        return holdings
    except Exception as e:
        print(f"[SUPABASE] load_holdings error: {e}")
        return []


# ===================================================================
# Analyses CRUD
# ===================================================================

def save_analysis_record(user_id: str, record: Dict) -> bool:
    """Save an analysis record."""
    client = _get_client()
    if not client:
        return False
    try:
        analysis = record.get("analysis", "")
        if isinstance(analysis, dict):
            analysis = json.dumps(analysis, ensure_ascii=False)

        client.table("analyses").insert({
            "user_id": user_id,
            "analysis_id": record.get("id", ""),
            "analysis_time": record.get("analysis_time", datetime.now(CST).isoformat()),
            "model": record.get("model", ""),
            "holdings_analyzed": record.get("holdings_analyzed", ""),
            "news_count_input": record.get("news_count_input", 0),
            "analysis": analysis,
            "token_usage": json.dumps(record.get("token_usage", {})),
        }).execute()
        return True
    except Exception as e:
        print(f"[SUPABASE] save_analysis error: {e}")
        return False


def load_analyses(user_id: str, limit: int = 20) -> List[Dict]:
    """Load analysis records for a user, newest first."""
    client = _get_client()
    if not client:
        return []
    try:
        resp = (client.table("analyses")
                .select("*")
                .eq("user_id", user_id)
                .order("analysis_time", desc=True)
                .limit(limit)
                .execute())
        records = []
        for row in resp.data:
            analysis = row.get("analysis", "")
            if isinstance(analysis, str):
                try:
                    analysis = json.loads(analysis)
                except json.JSONDecodeError:
                    pass
            token = row.get("token_usage", {})
            if isinstance(token, str):
                try:
                    token = json.loads(token)
                except json.JSONDecodeError:
                    token = {}
            records.append({
                "id": row.get("analysis_id", ""),
                "analysis_time": str(row.get("analysis_time", "")),
                "model": row.get("model", ""),
                "holdings_analyzed": row.get("holdings_analyzed", ""),
                "news_count_input": row.get("news_count_input", 0),
                "analysis": analysis if isinstance(analysis, str) else json.dumps(analysis, ensure_ascii=False),
                "token_usage": token,
            })
        return records
    except Exception as e:
        print(f"[SUPABASE] load_analyses error: {e}")
        return []


# ===================================================================
# User Settings
# ===================================================================

def save_user_settings(user_id: str, settings: Dict) -> bool:
    """Upsert user settings."""
    client = _get_client()
    if not client:
        return False
    try:
        client.table("user_settings").upsert({
            "user_id": user_id,
            "telegram_chat_id": settings.get("telegram_chat_id", ""),
            "alert_threshold_pct": settings.get("alert_threshold_pct", 3.0),
            "data_sources": json.dumps(settings.get("data_sources", {}), ensure_ascii=False),
            "preferences": json.dumps(settings.get("preferences", {}), ensure_ascii=False),
            "updated_at": datetime.now(CST).isoformat(),
        }).execute()
        return True
    except Exception as e:
        print(f"[SUPABASE] save_settings error: {e}")
        return False


def load_user_settings(user_id: str) -> Dict:
    """Load user settings."""
    client = _get_client()
    if not client:
        return {}
    try:
        resp = client.table("user_settings").select("*").eq("user_id", user_id).limit(1).execute()
        if resp.data:
            row = resp.data[0]
            ds = row.get("data_sources", {})
            if isinstance(ds, str):
                ds = json.loads(ds)
            prefs = row.get("preferences", {})
            if isinstance(prefs, str):
                prefs = json.loads(prefs)
            return {
                "telegram_chat_id": row.get("telegram_chat_id", ""),
                "alert_threshold_pct": float(row.get("alert_threshold_pct", 3.0)),
                "data_sources": ds,
                "preferences": prefs,
            }
    except Exception as e:
        print(f"[SUPABASE] load_settings error: {e}")
    return {}
