"""
持仓估值引擎 — 汇率换算 + 总资产计算

支持 A 股 (CNY)、港股 (HKD)、美股 (USD) 自动折算为 CNY。
汇率每 60 分钟刷新一次。
"""

from __future__ import annotations

import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

CST = timezone(timedelta(hours=8))

# Approximate FX rates (fallback if API fails)
DEFAULT_FX = {"HKD": 0.92, "USD": 7.25, "CNY": 1.0}

# 汇率缓存：60 分钟 TTL
_FX_CACHE: Dict[str, Any] = {"rates": None, "ts": None}
_FX_TTL_SEC = 60 * 60


def get_fx_rates() -> Dict[str, float]:
    """Get FX rates to CNY. DB 优先，API 回退，缓存 60 min。"""
    now = datetime.now(CST).timestamp()
    if _FX_CACHE["rates"] is not None and _FX_CACHE["ts"] is not None:
        if now - _FX_CACHE["ts"] < _FX_TTL_SEC:
            return _FX_CACHE["rates"]
    rates = dict(DEFAULT_FX)
    if os.environ.get("PFA_USE_DB", "1") == "1":
        try:
            from backend.services.fx_service import get_fx_rates_from_db, sync_fx_rates
            db_rates = get_fx_rates_from_db()
            if db_rates:
                rates.update(db_rates)
            else:
                rates = sync_fx_rates()
        except Exception:
            pass
    if rates == dict(DEFAULT_FX) or "USD" not in rates:
        try:
            resp = requests.get(
                "https://api.exchangerate-api.com/v4/latest/CNY",
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"},
                proxies={"http": None, "https": None},
            )
            if resp.status_code == 200:
                data = resp.json().get("rates", {})
                if "HKD" in data and data["HKD"] > 0:
                    rates["HKD"] = 1.0 / data["HKD"]
                if "USD" in data and data["USD"] > 0:
                    rates["USD"] = 1.0 / data["USD"]
        except Exception:
            pass
    rates["CNY"] = 1.0
    _FX_CACHE["rates"] = rates
    _FX_CACHE["ts"] = now
    return rates


def get_fx_rates_for_target(target: str) -> Dict[str, float]:
    """Returns {currency: rate_to_target}. target in CNY, USD, HKD."""
    fx_cny = get_fx_rates()
    t = target.strip().upper()
    if t not in fx_cny or fx_cny[t] == 0:
        t = "CNY"
    divisor = fx_cny[t]
    return {c: (v / divisor) for c, v in fx_cny.items()}


def get_fx_updated_at() -> Optional[str]:
    """Return ISO timestamp of last FX cache update, or None if not cached."""
    ts = _FX_CACHE.get("ts")
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, CST).strftime("%Y-%m-%dT%H:%M:%S%z")


def market_to_currency(market: str) -> str:
    return {"A": "CNY", "HK": "HKD", "US": "USD"}.get(market, "CNY")


def get_holding_currency(h: Dict) -> str:
    """标的原始币种：优先 explicit currency，否则由 market 推断。"""
    c = (h.get("currency") or "").strip().upper()
    if c in ("CNY", "USD", "HKD"):
        return c
    return market_to_currency(h.get("market", "A"))


def get_realtime_prices(holdings: List[Dict]) -> Dict[str, Dict]:
    """Get real-time prices for all holdings.

    Uses Sina Finance API (instant, no browser needed).
    Fallback to Xueqiu via Playwright if Sina fails.
    """
    try:
        from pfa.realtime_quote import get_realtime_quotes
        return get_realtime_quotes(holdings)
    except Exception:
        pass

    # Fallback: Xueqiu via Playwright (slow but reliable)
    prices = {}
    try:
        from pfa.browser_fetcher import fetch_xueqiu_quote
        symbols = []
        for h in holdings:
            sym, mkt = h["symbol"], h.get("market", "A")
            prefix = "SH" if mkt == "A" and sym.startswith("6") else "SZ" if mkt == "A" else ""
            symbols.append(f"{prefix}{sym}")
        quotes = fetch_xueqiu_quote(symbols)
        for q in quotes:
            raw_sym = q["symbol"]
            clean = raw_sym.lstrip("SH").lstrip("SZ")
            prices[clean] = {
                "current": q.get("current"),
                "percent": q.get("percent"),
                "name": q.get("name", ""),
            }
    except Exception:
        pass
    return prices


def calculate_portfolio_value(
    holdings: List[Dict],
    prices: Optional[Dict] = None,
    fx: Optional[Dict] = None,
    target_currency: str = "CNY",
) -> Dict[str, Any]:
    """Calculate portfolio value. target_currency: CNY, USD, or original.

    When target_currency is 'original': each holding keeps value_local, currency.
    When CNY/USD: all values converted to target.

    Returns: {
        total_value, total_cost, total_pnl, total_pnl_pct,
        target_currency, fx_updated_at,
        by_account: {account: {value, cost, pnl, holdings: [...]}},
        by_market, account_count, holding_count, fx_rates,
    }
    """
    if prices is None:
        prices = {}
    is_original = (target_currency or "").strip().lower() == "original"
    if is_original:
        fx = get_fx_rates()  # rate_to_cny for aggregation
    else:
        t = (target_currency or "CNY").strip().upper()
        if t not in ("CNY", "USD", "HKD"):
            t = "CNY"
        target_currency = t
        fx = get_fx_rates_for_target(t) if fx is None else fx

    fx_updated_at = get_fx_updated_at()
    by_account: Dict[str, Dict] = {}
    by_market: Dict[str, Dict] = {}
    total_value = 0.0
    total_cost = 0.0

    for h in holdings:
        sym = h["symbol"]
        market = h.get("market", "A")
        account = h.get("account", "默认")
        currency = get_holding_currency(h)
        fx_rate_raw = fx.get(currency)
        currency_error = fx_rate_raw is None or fx_rate_raw <= 0
        fx_rate = round(float(fx_rate_raw or 1.0), 4) if not currency_error else 0.0

        cost_price = float(h.get("cost_price", 0) or 0)
        quantity = float(h.get("quantity", 0) or 0)

        p = prices.get(sym, {})
        current = p.get("current")
        if current is not None:
            current = float(current)
        else:
            current = cost_price

        value_local = round(current * quantity, 4)
        cost_local = round(cost_price * quantity, 4)
        value_target = round(value_local * fx_rate, 4) if not currency_error else 0.0
        cost_target = round(cost_local * fx_rate, 4) if not currency_error else 0.0
        pnl_target = value_target - cost_target

        total_value += value_target
        total_cost += cost_target

        if account not in by_account:
            by_account[account] = {"value": 0, "cost": 0, "pnl": 0, "holdings": []}
        by_account[account]["value"] += value_target
        by_account[account]["cost"] += cost_target
        by_account[account]["pnl"] += pnl_target
        today_pct = p.get("percent")
        today_pct_val = float(today_pct) if today_pct is not None else 0.0
        today_pnl_target = round(value_local * (today_pct_val / 100) * fx_rate, 2) if not currency_error and today_pct_val else 0.0

        ho: Dict[str, Any] = {
            **h,
            "current_price": current,
            "value_local": value_local,
            "currency": currency,
            "value_cny": value_target,
            "value_display": round(value_target, 2) if not currency_error else None,
            "currency_error": currency_error,
            "pnl_cny": pnl_target,
            "pnl_pct": ((current - cost_price) / cost_price * 100) if cost_price > 0 else 0,
            "today_pct": today_pct_val,
            "today_pnl": today_pnl_target,
        }
        by_account[account]["holdings"].append(ho)

        if market not in by_market:
            by_market[market] = {"value": 0, "count": 0}
        by_market[market]["value"] += value_target
        by_market[market]["count"] += 1

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    for acct_data in by_account.values():
        acct_val = acct_data["value"]
        for ho in acct_data["holdings"]:
            v = ho.get("value_cny", ho.get("value_local", 0))
            ho["position_pct"] = (v / acct_val * 100) if acct_val > 0 else 0

    raw_rates = get_fx_rates()
    fx_rates_rounded = {k: round(v, 4) for k, v in raw_rates.items()}
    out: Dict[str, Any] = {
        "total_value_cny": round(total_value, 2),
        "total_cost_cny": round(total_cost, 2),
        "total_pnl_cny": round(total_pnl, 2),
        "total_pnl_pct": total_pnl_pct,
        "target_currency": "original" if is_original else target_currency,
        "fx_updated_at": fx_updated_at,
        "by_account": by_account,
        "by_market": by_market,
        "account_count": len(by_account),
        "holding_count": len(holdings),
        "fx_rates": fx_rates_rounded,
    }
    return out
