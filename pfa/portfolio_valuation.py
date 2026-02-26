"""
持仓估值引擎 — 汇率换算 + 总资产计算

支持 A 股 (CNY)、港股 (HKD)、美股 (USD) 自动折算为 CNY。
"""

from __future__ import annotations

import requests
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

CST = timezone(timedelta(hours=8))

# Approximate FX rates (fallback if API fails)
DEFAULT_FX = {"HKD": 0.92, "USD": 7.25, "CNY": 1.0}


def get_fx_rates() -> Dict[str, float]:
    """Get FX rates to CNY. Returns {currency: rate_to_cny}."""
    rates = dict(DEFAULT_FX)
    try:
        resp = requests.get(
            "https://api.exchangerate-api.com/v4/latest/CNY",
            timeout=5, headers={"User-Agent": "Mozilla/5.0"},
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
    return rates


def market_to_currency(market: str) -> str:
    return {"A": "CNY", "HK": "HKD", "US": "USD"}.get(market, "CNY")


def get_realtime_prices(holdings: List[Dict]) -> Dict[str, Dict]:
    """Get real-time prices for all holdings via Xueqiu API.

    Returns {symbol: {current, percent, name}}.
    """
    prices = {}
    try:
        from pfa.browser_fetcher import fetch_xueqiu_quote
        symbols = []
        for h in holdings:
            sym, mkt = h["symbol"], h.get("market", "A")
            if mkt == "A":
                prefix = "SH" if sym.startswith("6") else "SZ"
            elif mkt == "HK":
                prefix = ""
            else:
                prefix = ""
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
) -> Dict[str, Any]:
    """Calculate total portfolio value in CNY.

    Returns: {
        total_value_cny, total_cost_cny, total_pnl_cny, total_pnl_pct,
        by_account: {account: {value, cost, pnl, holdings: [...]}},
        by_market: {market: {value, count}},
        account_count, holding_count,
    }
    """
    if fx is None:
        fx = get_fx_rates()
    if prices is None:
        prices = {}

    by_account: Dict[str, Dict] = {}
    by_market: Dict[str, Dict] = {}
    total_value = 0.0
    total_cost = 0.0

    for h in holdings:
        sym = h["symbol"]
        market = h.get("market", "A")
        account = h.get("account", "默认")
        currency = market_to_currency(market)
        fx_rate = fx.get(currency, 1.0)

        cost_price = float(h.get("cost_price", 0) or 0)
        quantity = float(h.get("quantity", 0) or 0)

        # Get current price
        p = prices.get(sym, {})
        current = p.get("current")
        if current is not None:
            current = float(current)
        else:
            current = cost_price  # fallback

        # HKD prices for HK stocks
        if market == "HK":
            value_local = current * quantity
            cost_local = cost_price * quantity
        else:
            value_local = current * quantity
            cost_local = cost_price * quantity

        value_cny = value_local * fx_rate
        cost_cny = cost_local * fx_rate
        pnl_cny = value_cny - cost_cny

        total_value += value_cny
        total_cost += cost_cny

        # By account
        if account not in by_account:
            by_account[account] = {"value": 0, "cost": 0, "pnl": 0, "holdings": []}
        by_account[account]["value"] += value_cny
        by_account[account]["cost"] += cost_cny
        by_account[account]["pnl"] += pnl_cny
        by_account[account]["holdings"].append({
            **h,
            "current_price": current,
            "value_cny": value_cny,
            "pnl_cny": pnl_cny,
            "pnl_pct": ((current - cost_price) / cost_price * 100) if cost_price > 0 else 0,
            "currency": currency,
        })

        # By market
        if market not in by_market:
            by_market[market] = {"value": 0, "count": 0}
        by_market[market]["value"] += value_cny
        by_market[market]["count"] += 1

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    return {
        "total_value_cny": total_value,
        "total_cost_cny": total_cost,
        "total_pnl_cny": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "by_account": by_account,
        "by_market": by_market,
        "account_count": len(by_account),
        "holding_count": len(holdings),
        "fx_rates": fx,
    }
