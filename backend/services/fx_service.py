"""
汇率服务 — DB 存储 + 定时更新

从 exchangerate-api 拉取并写入 fx_rates 表，供估值使用。
"""

import os
from datetime import datetime
from typing import Dict

import requests

from backend.database.session import init_db, get_session
from backend.database.models import FxRate

DEFAULT_FX = {"HKD": 0.92, "USD": 7.25, "CNY": 1.0}
FX_API = "https://api.exchangerate-api.com/v4/latest/CNY"


def sync_fx_rates() -> Dict[str, float]:
    """从 API 拉取汇率并写入 DB。"""
    init_db()
    rates = dict(DEFAULT_FX)
    try:
        resp = requests.get(
            FX_API,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
            proxies={"http": None, "https": None},
        )
        if resp.status_code == 200:
            data = resp.json().get("rates", {})
            if data.get("HKD", 0) > 0:
                rates["HKD"] = 1.0 / data["HKD"]
            if data.get("USD", 0) > 0:
                rates["USD"] = 1.0 / data["USD"]
    except Exception:
        pass
    rates["CNY"] = 1.0
    db = get_session()
    try:
        for c, r in rates.items():
            if c == "CNY":
                continue
            existing = db.query(FxRate).filter(FxRate.currency == c).first()
            if existing:
                existing.rate_to_cny = r
                existing.updated_at = datetime.utcnow()
            else:
                db.add(FxRate(currency=c, rate_to_cny=r))
        db.commit()
    finally:
        db.close()
    return rates


def get_fx_rates_from_db() -> Dict[str, float] | None:
    """从 DB 读取汇率，无则返回 None。"""
    init_db()
    db = get_session()
    try:
        rows = db.query(FxRate).all()
        if not rows:
            return None
        rates = {"CNY": 1.0}
        for r in rows:
            rates[r.currency] = r.rate_to_cny
        return rates
    finally:
        db.close()
