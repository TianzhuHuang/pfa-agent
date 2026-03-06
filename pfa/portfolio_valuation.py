"""
持仓估值引擎 — 汇率换算 + 总资产计算

支持 A 股 (CNY)、港股 (HKD)、美股 (USD) 自动折算为 CNY。
汇率每 60 分钟刷新一次。
"""

from __future__ import annotations

import logging
import os
import requests

_log = logging.getLogger(__name__)
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


def get_realtime_prices(holdings: List[Dict], accounts: Optional[List[Dict]] = None) -> Dict[str, Dict]:
    """Get real-time prices for all holdings.

    多源聚合：Sina(A/HK/US) + Binance/CoinGecko(数字货币) + Yahoo(SGX)。
    单源失败不中断，返回部分结果。

    Args:
        holdings: 持仓列表
        accounts: 账户列表（可选），用于按 account_type 识别数字货币账户
    """
    prices: Dict[str, Dict] = {}

    # 数字货币账户名集合：account_type=数字货币 或 account 名为「数字货币」
    crypto_account_names: set = {"数字货币"}
    if accounts:
        for acc in accounts:
            if str(acc.get("account_type", "")).strip() == "数字货币":
                name = str(acc.get("name", acc.get("id", ""))).strip()
                if name:
                    crypto_account_names.add(name)

    # 1. Sina: A 股、港股、美股
    sina_holdings = [h for h in holdings if str(h.get("market", "")).upper() in ("A", "HK", "US")]
    if sina_holdings:
        try:
            from pfa.realtime_quote import get_realtime_quotes
            quotes = get_realtime_quotes(sina_holdings)
            prices.update(quotes)
            if not quotes and sina_holdings:
                _log.warning("get_realtime_quotes 返回空，A/HK/US 共 %d 只", len(sina_holdings))
        except Exception as e:
            _log.warning("A/HK/US 价格获取失败: %s", e, exc_info=True)

    # 2. 数字货币：Binance 优先，CoinGecko 回退
    crypto_holdings = [
        h for h in holdings
        if str(h.get("market", "")).upper() in ("OT", "CRYPTO")
        or str(h.get("account", "")).strip() in crypto_account_names
    ]
    if crypto_holdings:
        try:
            from pfa.crypto_quote import get_crypto_quotes
            prices.update(get_crypto_quotes(crypto_holdings))
        except Exception as e:
            _log.warning("Crypto price fetch failed: %s", e)

    # 3. SGX 新加坡市场：Yahoo Finance
    sgx_holdings = [
        h for h in holdings
        if str(h.get("market", "")).upper() == "SGX" or str(h.get("exchange", "")).upper() == "SGX"
    ]
    if sgx_holdings:
        try:
            from pfa.sgx_quote import get_sgx_quotes
            prices.update(get_sgx_quotes(sgx_holdings))
        except Exception as e:
            _log.warning("SGX price fetch failed: %s", e)

    # 4. OT 中非数字货币（如 SGX 标的误标为 OT）：尝试 SGX
    ot_non_crypto = [
        h for h in holdings
        if str(h.get("market", "")).upper() == "OT"
        and str(h.get("account", "")).strip() != "数字货币"
        and h["symbol"] not in prices
    ]
    if ot_non_crypto:
        try:
            from pfa.sgx_quote import get_sgx_quotes
            prices.update(get_sgx_quotes(ot_non_crypto))
        except Exception as e:
            _log.warning("SGX fallback for OT non-crypto failed: %s", e)

    # 5. Sina 失败时的 Xueqiu 回退（仅 A/HK/US）
    if sina_holdings and not any(prices.get(h["symbol"]) for h in sina_holdings):
        try:
            from pfa.browser_fetcher import fetch_xueqiu_quote
            symbols = []
            for h in sina_holdings:
                sym, mkt = h["symbol"], str(h.get("market", "A")).upper()
                if mkt == "A":
                    prefix = "SH" if str(sym).startswith("6") else "SZ"
                elif mkt == "HK":
                    prefix = "HK"
                else:
                    prefix = ""
                symbols.append(f"{prefix}{sym}" if prefix else sym)
            quotes = fetch_xueqiu_quote(symbols)
            for q in quotes:
                raw_sym = q.get("symbol", "")
                for p in ("SH", "SZ", "HK"):
                    if raw_sym.upper().startswith(p):
                        raw_sym = raw_sym[len(p):]
                        break
                prices[raw_sym] = {"current": q.get("current"), "percent": q.get("percent"), "name": q.get("name", "")}
        except Exception as e:
            _log.warning("Xueqiu fallback failed: %s", e)

    loaded = len(prices)
    total = len(holdings)
    if total > 0 and loaded == 0:
        _log.warning("get_realtime_prices: 0/%d 价格获取成功，请检查网络或 API", total)
    elif loaded < total:
        _log.info("get_realtime_prices: %d/%d 价格获取成功", loaded, total)
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

        # 价格查找：HK 标的可能以 00700 或 00700.HK 存储，需兼容
        p = prices.get(sym, {})
        if not p and market == "HK":
            alt = str(sym or "").rstrip(".HK").rstrip(".hk").strip()
            if alt and alt != sym:
                p = prices.get(alt, {})
            if not p and not str(sym or "").upper().endswith(".HK"):
                p = prices.get(f"{sym}.HK", prices.get(f"{sym}.hk", {}))
        current = p.get("current")
        price_loaded = current is not None
        if current is not None:
            current = float(current)
            # 现价为 0 时多为 API 异常，避免误显示 0（现金等除外）
            if current == 0 and not h.get("is_cash"):
                current = None
                price_loaded = False
        else:
            current = None  # 未加载成功时保持 null，禁止用成本价占位

        # 未加载价格时 value_local 不参与 total_value，市值显示 --
        if price_loaded and current is not None:
            value_local = round(current * quantity, 4)
            value_target = round(value_local * fx_rate, 4) if not currency_error else 0.0
            total_value += value_target
        else:
            value_local = None
            value_target = None

        cost_local = round(cost_price * quantity, 4)
        cost_target = round(cost_local * fx_rate, 4) if not currency_error else 0.0
        pnl_target = (value_target - cost_target) if value_target is not None else 0.0

        total_cost += cost_target

        if account not in by_account:
            by_account[account] = {"value": 0, "cost": 0, "pnl": 0, "holdings": []}
        v_target = value_target if value_target is not None else 0.0
        by_account[account]["value"] += v_target
        by_account[account]["cost"] += cost_target
        by_account[account]["pnl"] += pnl_target
        # 今日涨跌幅：仅当价格成功加载时才有意义
        today_pct_raw = p.get("percent")
        if price_loaded and today_pct_raw is not None:
            today_pct_val: Optional[float] = float(today_pct_raw)
            # 防御性校验：涨跌幅绝对值 > 50% 视为异常（如误用最高价 504 作为 percent）
            if abs(today_pct_val) > 50:
                today_pct_val = None
                today_pnl_target = None
            else:
                today_pnl_target = (
                    round(value_local * (today_pct_val / 100) * fx_rate, 2)
                    if value_local is not None and not currency_error and today_pct_val
                    else 0.0
                )
        else:
            # 价格未加载时，今日涨跌幅为 None（前端显示 "—"）
            today_pct_val = None
            today_pnl_target = None

        if sym in ("00700", "00700.HK"):
            _log.info(
                "[calculate_portfolio_value] 00700 symbol=%s p.percent=%s today_pct_raw=%s today_pct_val=%s",
                sym, p.get("percent"), today_pct_raw, today_pct_val,
            )

        # 累计盈亏率：仅当价格成功加载时计算
        pnl_pct_val: Optional[float] = (
            ((current - cost_price) / cost_price * 100)
            if (price_loaded and current is not None and cost_price > 0)
            else None
        )

        ho: Dict[str, Any] = {
            **h,
            "current_price": current if price_loaded else None,
            "price_loaded": price_loaded,
            "value_local": value_local if price_loaded else None,
            "currency": currency,
            "value_cny": v_target if price_loaded else None,
            "value_display": round(v_target, 2) if not currency_error and price_loaded else None,
            "currency_error": currency_error,
            "pnl_cny": pnl_target if price_loaded else None,
            "pnl_pct": pnl_pct_val,
            "today_pct": today_pct_val,
            "today_pnl": today_pnl_target,
        }
        by_account[account]["holdings"].append(ho)

        if market not in by_market:
            by_market[market] = {"value": 0, "count": 0}
        by_market[market]["value"] += v_target
        by_market[market]["count"] += 1

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    for acct_data in by_account.values():
        acct_val = acct_data["value"]
        for ho in acct_data["holdings"]:
            v = ho.get("value_cny") or ho.get("value_local") or 0
            if v is None:
                v = 0
            ho["position_pct"] = round((v / acct_val * 100), 1) if acct_val > 0 and v else 0

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
