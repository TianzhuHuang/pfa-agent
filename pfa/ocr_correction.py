"""
OCR 识别结果自纠错 — 名称-代码一致性校验

当 OCR 行位移导致「名字对、代码错、价格错」时，以名称为准检索正确代码并更新价格。
"""

from __future__ import annotations

from typing import Any, Dict, List

PRICE_DEVIATION_THRESHOLD = 0.05  # 5%


def _normalize_symbol_for_compare(symbol: str, market: str) -> str:
    """标准化 symbol 用于比较：去除后缀、港股 5 位补全。"""
    from pfa.symbol_utils import normalize_hk_symbol
    s = (symbol or "").strip()
    for suffix in (".HK", ".hk", ".SH", ".sh", ".SZ", ".sz"):
        if s.upper().endswith(suffix.upper()):
            s = s[: -len(suffix)]
    if (market or "A")[:2] == "HK":
        return normalize_hk_symbol(s)
    return s


def validate_and_correct_ocr_holdings(holdings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """对 OCR 结果做名称-代码一致性校验与纠错。

    - 若 name 与 symbol 不匹配：以 name 为准，用 search_stock 获取正确 symbol，并拉取实时价覆盖。
    - 若 OCR 价格与实时价偏差 > 5%：设置 price_deviation_warn。
    """
    if not holdings:
        return holdings

    from pfa.stock_search import search_stock
    from pfa.realtime_quote import get_realtime_quotes

    # 同名去重，减少 API 调用
    name_cache: Dict[str, List[Dict]] = {}
    out = []
    for h in holdings:
        h = dict(h)
        name = (h.get("name") or "").strip()
        if not name:
            out.append(h)
            continue

        if name not in name_cache:
            try:
                name_cache[name] = search_stock(name, count=3)
            except Exception:
                name_cache[name] = []
                out.append(h)
                continue

        results = name_cache[name]
        if not results:
            out.append(h)
            continue

        first = results[0]
        correct_code = (first.get("code") or "").strip()
        correct_name = (first.get("name") or "").strip()
        correct_market = (first.get("market") or "A")[:2] or "A"

        if not correct_code:
            out.append(h)
            continue

        ocr_symbol = _normalize_symbol_for_compare(h.get("symbol", ""), h.get("market", "A"))
        correct_symbol_norm = _normalize_symbol_for_compare(correct_code, correct_market)

        if ocr_symbol != correct_symbol_norm:
            # 冲突：以 name 为准重置 symbol
            from pfa.symbol_utils import normalize_hk_symbol
            if correct_market == "HK":
                h["symbol"] = normalize_hk_symbol(correct_code)
            else:
                h["symbol"] = correct_code
            h["name"] = correct_name
            h["market"] = correct_market
            if correct_market == "HK":
                h["currency"] = "HKD"
            elif correct_market == "US":
                h["currency"] = "USD"
            else:
                h["currency"] = "CNY"

        # 拉取实时价，覆盖 current_price
        try:
            prices = get_realtime_quotes([h])
            real_price = prices.get(h["symbol"], {}).get("current")
            if real_price is not None:
                ocr_price = h.get("current_price")
                h["current_price"] = float(real_price)
                if ocr_price is not None and float(ocr_price) > 0:
                    deviation = abs(float(real_price) - float(ocr_price)) / float(ocr_price)
                    if deviation > PRICE_DEVIATION_THRESHOLD:
                        h["price_deviation_warn"] = True
        except Exception:
            pass

        out.append(h)
    return out
