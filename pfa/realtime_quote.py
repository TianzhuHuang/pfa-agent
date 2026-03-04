"""
实时行情 API — 腾讯财经 / 东方财富 / 新浪财经 / Yahoo Finance

ECS 等机房 IP 常被新浪、东财、Yahoo 拦截，腾讯 qt.gtimg.cn 对云服务器相对宽松。
A 股、港股：腾讯优先，东财/新浪/Yahoo 回退。
美股：新浪优先，Yahoo 回退。
"""

from __future__ import annotations

import logging
import re
import requests
from typing import Dict, List, Optional

TENCENT_QUOTE_URL = "http://qt.gtimg.cn/q="
TENCENT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "http://gu.qq.com/",
}

SINA_HQ_URL = "https://hq.sinajs.cn/list="
SINA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://finance.sina.com.cn/",
}

EASTMONEY_QUOTE_URL = "https://push2.eastmoney.com/api/qt/stock/get"
EASTMONEY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
}

_log = logging.getLogger("pfa.realtime_quote")


def _to_secid(symbol: str, market: str) -> Optional[str]:
    """Convert PFA symbol to East Money secid. 1=沪 0=深."""
    if market != "A":
        return None
    if symbol.startswith("6"):
        return f"1.{symbol}"
    return f"0.{symbol}"


def _to_tencent_code(symbol: str, market: str) -> Optional[str]:
    """PFA symbol -> 腾讯代码。A股 s_sh/s_sz，港股 hk。"""
    sym = str(symbol).strip()
    if not sym:
        return None
    if market == "A":
        return f"s_sh{sym}" if sym.startswith("6") else f"s_sz{sym}"
    if market == "HK":
        return f"hk{sym}"
    return None


def _to_sina_code(symbol: str, market: str) -> str:
    """Convert PFA symbol to Sina format."""
    if market == "A":
        if symbol.startswith("6"):
            return f"sh{symbol}"
        else:
            return f"sz{symbol}"
    elif market == "HK":
        return f"hk{symbol}"
    elif market == "US":
        return f"gb_{symbol.lower()}"
    return ""


def _parse_tencent_response(text: str, code_to_symbol: Dict[str, str]) -> Dict[str, Dict]:
    """解析腾讯返回：v_s_sh600519="1~贵州茅台~600519~1401.18~涨跌~涨跌%~..."
    现价=index 3，涨跌%=index 5（若有）。
    """
    results = {}
    for line in text.strip().split("\n"):
        if not line or "=" not in line:
            continue
        m = re.match(r'v_(\w+)="([^"]+)"', line.strip())
        if not m:
            continue
        tc_code = m.group(1)
        pfa_sym = code_to_symbol.get(tc_code)
        if not pfa_sym:
            continue
        parts = m.group(2).split("~")
        if len(parts) < 4:
            continue
        try:
            current = float(parts[3])
            if current <= 0:
                continue
            pct = 0.0
            chg = 0.0
            if len(parts) > 6 and parts[5]:
                try:
                    chg = float(parts[4])
                    pct = float(parts[5])
                except (ValueError, TypeError):
                    pass
            if pct == 0 and chg == 0 and len(parts) > 4 and parts[4]:
                try:
                    last_close = float(parts[4])
                    if last_close > 0:
                        chg = current - last_close
                        pct = (chg / last_close) * 100
                except (ValueError, TypeError):
                    pass
            results[pfa_sym] = {
                "current": current,
                "percent": round(pct, 2),
                "change": round(chg, 2),
                "name": parts[1] if len(parts) > 1 else pfa_sym,
            }
        except (ValueError, TypeError):
            continue
    return results


def _fetch_tencent_ashares(holdings: List[Dict]) -> Dict[str, Dict]:
    """A 股：腾讯财经（ECS 机房首选）。"""
    ashare = [h for h in holdings if h.get("market") == "A"]
    if not ashare:
        return {}
    code_to_symbol = {}
    codes = []
    for h in ashare:
        tc = _to_tencent_code(h["symbol"], "A")
        if tc:
            code_to_symbol[tc] = h["symbol"]
            codes.append(tc)
    if not codes:
        return {}
    try:
        url = TENCENT_QUOTE_URL + ",".join(codes)
        r = requests.get(url, headers=TENCENT_HEADERS, timeout=8)
        r.raise_for_status()
        return _parse_tencent_response(r.text, code_to_symbol)
    except Exception as e:
        _log.warning("腾讯 A 股请求失败: %s", e)
        return {}


def _fetch_tencent_hk(holdings: List[Dict]) -> Dict[str, Dict]:
    """港股：腾讯财经（ECS 机房首选）。"""
    hk = [h for h in holdings if h.get("market") == "HK"]
    if not hk:
        return {}
    code_to_symbol = {}
    codes = []
    for h in hk:
        tc = _to_tencent_code(h["symbol"], "HK")
        if tc:
            code_to_symbol[tc] = h["symbol"]
            codes.append(tc)
    if not codes:
        return {}
    try:
        url = TENCENT_QUOTE_URL + ",".join(codes)
        r = requests.get(url, headers=TENCENT_HEADERS, timeout=8)
        r.raise_for_status()
        return _parse_tencent_response(r.text, code_to_symbol)
    except Exception as e:
        _log.warning("腾讯港股请求失败: %s", e)
        return {}


def _fetch_eastmoney_ashares(holdings: List[Dict]) -> Dict[str, Dict]:
    """Fetch A-share quotes from East Money (primary source)."""
    results = {}
    for h in holdings:
        if h.get("market") != "A":
            continue
        sym = h["symbol"]
        secid = _to_secid(sym, "A")
        if not secid:
            continue
        try:
            r = requests.get(
                EASTMONEY_QUOTE_URL,
                params={"secid": secid},
                headers=EASTMONEY_HEADERS,
                timeout=10,
            )
            r.raise_for_status()
            j = r.json()
        except Exception as e:
            _log.warning("East Money %s 请求失败: %s", sym, e)
            continue
        d = j.get("data")
        if not d or not isinstance(d, dict):
            _log.warning("East Money %s 无 data 或格式异常: %s", sym, str(j)[:150])
            continue
        try:
            current = float(d.get("f43", 0)) / 100
            last_close = float(d.get("f60", 0)) / 100
            if current <= 0 or last_close <= 0:
                _log.warning("East Money %s 价格异常: f43=%s f60=%s", sym, d.get("f43"), d.get("f60"))
                continue
            pct = ((current - last_close) / last_close * 100) if last_close > 0 else 0
            chg = current - last_close
            results[sym] = {
                "current": current,
                "percent": round(pct, 2),
                "change": round(chg, 2),
                "name": d.get("f58", sym),
                "open": float(d.get("f46", 0)) / 100,
                "high": float(d.get("f44", 0)) / 100,
                "low": float(d.get("f45", 0)) / 100,
                "last_close": last_close,
                "volume": float(d.get("f47", 0)),
                "amount": float(d.get("f48", 0)),
                "update_time": "",
            }
        except (ValueError, TypeError):
            continue
    return results


def _parse_sina_response(resp_text: str, code_map: Dict[str, str]) -> Dict[str, Dict]:
    """Parse Sina API response into {symbol: quote_dict}."""
    results = {}
    for line in resp_text.strip().split("\n"):
        if not line or "=" not in line:
            continue
        match = re.match(r'var hq_str_(\w+)="(.+)"', line.strip())
        if not match:
            continue
        sina_code = match.group(1)
        fields = match.group(2).split(",")
        pfa_symbol = code_map.get(sina_code, "")
        if not pfa_symbol:
            continue
        try:
            if sina_code.startswith(("sh", "sz")):
                current = float(fields[3])
                last_close = float(fields[2])
                pct = ((current - last_close) / last_close * 100) if last_close > 0 else 0
                chg = current - last_close
                vol = float(fields[8]) if len(fields) > 8 else 0
                amount = float(fields[9]) if len(fields) > 9 else 0
                date_str = fields[30] if len(fields) > 30 else ""
                time_str = fields[31] if len(fields) > 31 else ""
                results[pfa_symbol] = {
                    "current": current,
                    "percent": round(pct, 2),
                    "change": round(chg, 2),
                    "name": fields[0],
                    "open": float(fields[1]),
                    "high": float(fields[4]),
                    "low": float(fields[5]),
                    "last_close": last_close,
                    "volume": vol,
                    "amount": amount,
                    "update_time": f"{date_str} {time_str}".strip(),
                }
            elif sina_code.startswith("hk"):
                current = float(fields[6])
                pct = float(fields[8])
                chg = float(fields[7])
                results[pfa_symbol] = {
                    "current": current,
                    "percent": round(pct, 2),
                    "change": round(chg, 3),
                    "name": fields[1],
                    "open": float(fields[2]),
                    "high": float(fields[4]),
                    "low": float(fields[5]),
                    "last_close": float(fields[3]),
                    "update_time": fields[17] if len(fields) > 17 else "",
                }
            elif sina_code.startswith("gb_"):
                if len(fields) > 1:
                    current = float(fields[1])
                    last_close = float(fields[26]) if len(fields) > 26 else 0
                    pct = ((current - last_close) / last_close * 100) if last_close > 0 else 0
                    results[pfa_symbol] = {
                        "current": current,
                        "percent": round(pct, 2),
                        "name": fields[0],
                    }
        except (ValueError, IndexError):
            continue
    return results


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


def _to_yahoo_symbol(symbol: str, market: str) -> Optional[str]:
    """PFA symbol -> Yahoo symbol. HK: 00883.HK, US: NIO"""
    sym = str(symbol).strip().upper()
    if not sym:
        return None
    if market == "HK":
        return f"{sym}.HK"
    if market == "US":
        return sym  # 美股直接使用
    return None


def _fetch_yahoo_hk_us(holdings: List[Dict]) -> Dict[str, Dict]:
    """港股、美股：Yahoo Finance（新浪 403 时回退）。"""
    results = {}
    for h in holdings:
        market = str(h.get("market", "")).upper()
        if market not in ("HK", "US"):
            continue
        sym = h["symbol"]
        yahoo_sym = _to_yahoo_symbol(sym, market)
        if not yahoo_sym:
            continue
        try:
            r = requests.get(
                YAHOO_CHART_URL.format(symbol=yahoo_sym),
                params={"interval": "1d", "range": "1d"},
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            _log.warning("Yahoo %s (%s) 请求失败: %s", sym, yahoo_sym, e)
            continue
        try:
            r = data.get("chart", {}).get("result", [])
            if not r:
                continue
            meta = r[0].get("meta", {})
            current = meta.get("regularMarketPrice") or meta.get("previousClose")
            if current is None:
                continue
            prev = meta.get("previousClose") or current
            pct = ((float(current) - float(prev)) / float(prev) * 100) if prev else 0
            results[sym] = {
                "current": float(current),
                "percent": round(pct, 2),
                "change": round(float(current) - float(prev), 2),
                "name": meta.get("shortName", sym),
            }
        except (ValueError, TypeError):
            continue
    return results


def _fetch_sina_quotes(code_map: Dict[str, str]) -> Dict[str, Dict]:
    """Fetch quotes from Sina for given code_map {sina_code: pfa_symbol}."""
    if not code_map:
        return {}
    try:
        url = SINA_HQ_URL + ",".join(code_map.keys())
        resp = requests.get(url, headers=SINA_HEADERS, timeout=8)
        resp.encoding = "gbk"
        if resp.status_code != 200:
            _log.warning("Sina API returned status %s", resp.status_code)
            return {}
        return _parse_sina_response(resp.text, code_map)
    except Exception as e:
        _log.warning("Sina API error: %s", e)
        return {}


def get_realtime_quotes(holdings: List[Dict]) -> Dict[str, Dict]:
    """Get real-time quotes. A股/港股: 腾讯优先（ECS 机房首选），东财/新浪回退；美股: 新浪优先，Yahoo 回退。"""
    ashare_holdings = [h for h in holdings if h.get("market") == "A"]
    hk_holdings = [h for h in holdings if h.get("market") == "HK"]
    us_holdings = [h for h in holdings if h.get("market") == "US"]

    results: Dict[str, Dict] = {}

    # A 股：腾讯优先（ECS 机房唯一可用），东财/新浪回退
    if ashare_holdings:
        results.update(_fetch_tencent_ashares(ashare_holdings))
        ashare_missing = [h for h in ashare_holdings if h["symbol"] not in results]
        if ashare_missing:
            results.update(_fetch_eastmoney_ashares(ashare_missing))
            ashare_missing = [h for h in ashare_missing if h["symbol"] not in results]
        if ashare_missing:
            _log.info("腾讯/东财未命中 %d 只 A 股，回退新浪", len(ashare_missing))
            code_map = {_to_sina_code(h["symbol"], "A"): h["symbol"] for h in ashare_missing}
            results.update(_fetch_sina_quotes(code_map))

    # 港股：腾讯优先（ECS 机房唯一可用），新浪/Yahoo 回退
    if hk_holdings:
        results.update(_fetch_tencent_hk(hk_holdings))
        hk_missing = [h for h in hk_holdings if h["symbol"] not in results]
        if hk_missing:
            code_map = {_to_sina_code(h["symbol"], "HK"): h["symbol"] for h in hk_missing}
            results.update(_fetch_sina_quotes(code_map))
            hk_missing = [h for h in hk_missing if h["symbol"] not in results]
        if hk_missing:
            _log.info("腾讯/新浪未命中 %d 只港股，回退 Yahoo", len(hk_missing))
            results.update(_fetch_yahoo_hk_us(hk_missing))

    # 美股：新浪优先，Yahoo 回退（ECS 上两者均可能 403）
    if us_holdings:
        code_map = {_to_sina_code(h["symbol"], "US"): h["symbol"] for h in us_holdings}
        results.update(_fetch_sina_quotes(code_map))
        us_missing = [h for h in us_holdings if h["symbol"] not in results]
        if us_missing:
            _log.info("新浪未命中 %d 只美股，回退 Yahoo", len(us_missing))
            results.update(_fetch_yahoo_hk_us(us_missing))

    return results
