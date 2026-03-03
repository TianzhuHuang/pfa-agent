"""
标的代码标准化 — 港股 5 位补全、后缀去除

Sina 行情接口要求港股代码为 5 位（如 hk00883），OCR 可能返回 883。
"""


def normalize_hk_symbol(symbol: str) -> str:
    """港股代码补全为 5 位，如 883 -> 00883。去除 .HK 后缀。"""
    s = (symbol or "").strip().rstrip(".HK").rstrip(".hk")
    if s.isdigit() and len(s) <= 5:
        return s.zfill(5)
    return s
