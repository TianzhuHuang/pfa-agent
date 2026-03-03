"""
组合服务 — 从 DB 读写账户与持仓
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from backend.database.session import get_session, init_db
from backend.database.models import Account, Holding, PortfolioMeta

ROOT = Path(__file__).resolve().parent.parent.parent
PORTFOLIO_JSON = ROOT / "config" / "my-portfolio.json"


def _holding_to_dict(h: Holding) -> Dict:
    out = {
        "symbol": h.symbol,
        "name": h.name or "",
        "market": h.market or "A",
        "quantity": h.quantity or 0,
        "cost_price": h.cost_price,
        "currency": h.currency,
        "exchange": h.exchange,
        "account": h.account or "默认",
        "source": h.source or "manual",
        "position_pct": h.position_pct,
        "memo_history": h.memo_history or [],
        "updated_at": h.updated_at.isoformat() if h.updated_at else None,
    }
    if hasattr(h, "ocr_confirmed") and h.ocr_confirmed is not None:
        out["ocr_confirmed"] = bool(h.ocr_confirmed)
    if hasattr(h, "price_deviation_warn") and h.price_deviation_warn is not None:
        out["price_deviation_warn"] = bool(h.price_deviation_warn)
    return out


def _account_to_dict(a: Account) -> Dict:
    return {
        "id": a.account_id,
        "name": a.name,
        "base_currency": a.base_currency or "CNY",
        "broker": a.broker or "",
        "account_type": a.account_type or "股票",
        "balance": float(a.balance or 0),
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


def load_portfolio_db(user_id: str = "admin") -> Dict[str, Any]:
    """从 DB 加载组合。"""
    init_db()
    db = get_session()
    try:
        uid = user_id or "admin"
        data = {
            "version": "1.0",
            "holdings": [],
            "accounts": [],
            "channels": {"rss_urls": [], "xueqiu_user_ids": [], "twitter_handles": []},
            "preferences": {},
        }
        for h in db.query(Holding).filter(Holding.user_id == uid).all():
            data["holdings"].append(_holding_to_dict(h))
        for a in db.query(Account).filter(Account.user_id == uid).all():
            data["accounts"].append(_account_to_dict(a))
        for m in db.query(PortfolioMeta).filter(PortfolioMeta.user_id == uid).all():
            if m.meta_key == "channels" and m.meta_value:
                data["channels"] = m.meta_value
            elif m.meta_key == "preferences" and m.meta_value:
                data["preferences"] = m.meta_value
        return data
    finally:
        db.close()


def save_portfolio_db(data: Dict[str, Any], user_id: str = "admin") -> None:
    """保存组合到 DB。"""
    init_db()
    db = get_session()
    try:
        uid = user_id or "admin"
        db.query(Holding).filter(Holding.user_id == uid).delete()
        db.query(Account).filter(Account.user_id == uid).delete()
        db.query(PortfolioMeta).filter(PortfolioMeta.user_id == uid).delete()
        now = datetime.utcnow()
        for h in data.get("holdings", []):
            sym = str(h.get("symbol", "")).strip()
            if not sym:
                continue
            db.add(Holding(
                user_id=uid,
                symbol=sym,
                name=str(h.get("name", "")).strip() or None,
                market=str(h.get("market", "A"))[:2] or "A",
                quantity=float(h.get("quantity", 0) or 0),
                cost_price=float(h["cost_price"]) if h.get("cost_price") is not None else None,
                currency=h.get("currency"),
                exchange=h.get("exchange"),
                account=str(h.get("account", "默认")).strip() or "默认",
                source=str(h.get("source", "manual")).strip() or "manual",
                position_pct=float(h["position_pct"]) if h.get("position_pct") is not None else None,
                memo_history=h.get("memo_history"),
                ocr_confirmed=h.get("ocr_confirmed") if h.get("ocr_confirmed") is not None else None,
                price_deviation_warn=h.get("price_deviation_warn") if h.get("price_deviation_warn") is not None else None,
            ))
        for a in data.get("accounts", []):
            aid = str(a.get("id", a.get("name", ""))).strip()
            if not aid:
                continue
            db.add(Account(
                user_id=uid,
                account_id=aid,
                name=str(a.get("name", aid)).strip(),
                base_currency=str(a.get("base_currency", a.get("currency", "CNY"))).strip().upper() or "CNY",
                broker=str(a.get("broker", "")).strip() or None,
                account_type=str(a.get("account_type", "股票")).strip() or "股票",
                balance=float(a.get("balance", 0) or 0),
            ))
        ch = data.get("channels", {})
        if ch:
            db.add(PortfolioMeta(user_id=uid, meta_key="channels", meta_value=ch))
        pref = data.get("preferences", {})
        if pref:
            db.add(PortfolioMeta(user_id=uid, meta_key="preferences", meta_value=pref))
        db.commit()
    finally:
        db.close()


def migrate_json_to_db(user_id: str = "admin") -> bool:
    """从 JSON 迁移到 DB。"""
    if not PORTFOLIO_JSON.exists():
        return False
    try:
        with open(PORTFOLIO_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        save_portfolio_db(data, user_id)
        return True
    except Exception:
        return False
