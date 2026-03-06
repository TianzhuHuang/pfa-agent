"""
标的代码标准化 — 港股 5 位补全、后缀去除

Sina 行情接口要求港股代码为 5 位（如 hk00883），OCR 可能返回 883。
"""


def symbol_for_compare(symbol: str, market: str = "") -> str:
    """用于合并/去重比较的规范形式。HK: 00700/00700.HK -> 00700；A: 去除后缀。去除尾部中文名。"""
    s = (symbol or "").strip()
    if not s:
        return s
    # 去除尾部股票名称（如 600900长江电力 -> 600900）
    import re
    s = re.sub(r"[^\d.]+$", "", s)
    s = s.strip()
    m = (market or "").strip().upper()[:2]
    if m == "HK":
        return normalize_hk_symbol(s)
    for suffix in (".HK", ".hk", ".SH", ".sh", ".SZ", ".sz", ".SS", ".ss"):
        if s.upper().endswith(suffix):
            s = s[: -len(suffix)]
            break
    return s.strip()


def normalize_hk_symbol(symbol: str) -> str:
    """港股代码补全为 5 位，如 883 -> 00883。去除 .HK 后缀。"""
    s = (symbol or "").strip().rstrip(".HK").rstrip(".hk")
    if s.isdigit() and len(s) <= 5:
        return s.zfill(5)
    return s
