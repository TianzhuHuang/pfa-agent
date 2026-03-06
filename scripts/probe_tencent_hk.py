#!/usr/bin/env python3
"""本地探测腾讯港股 API 返回的原始数据，便于排查涨跌幅解析问题。"""
import requests

URL = "http://qt.gtimg.cn/q=hk00700"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "http://gu.qq.com/",
}

def main():
    r = requests.get(URL, headers=HEADERS, timeout=10)
    r.encoding = "gbk"
    text = r.text.strip()
    print("=== 腾讯港股 API 原始返回 (hk00700) ===\n")
    print(text)
    print()
    for line in text.split("\n"):
        if "hk00700" in line.lower() and "=" in line:
            import re
            m = re.match(r'v_\w+="([^"]+)"', line.strip())
            if m:
                parts = m.group(1).split("~")
                print("=== 字段解析 (index) ===\n")
                print("  0: 交易所代码", parts[0] if len(parts) > 0 else "N/A")
                print("  1: 股票名称", parts[1] if len(parts) > 1 else "N/A")
                print("  2: 股票代码", parts[2] if len(parts) > 2 else "N/A")
                print("  3: 现价", parts[3] if len(parts) > 3 else "N/A")
                print("  4: 昨收", parts[4] if len(parts) > 4 else "N/A")
                print("  5: 最高价 (港股非涨跌%!)", parts[5] if len(parts) > 5 else "N/A")
                print("  31: 涨跌额", parts[31] if len(parts) > 31 else "N/A")
                print("  32: 涨跌%", parts[32] if len(parts) > 32 else "N/A")
                print()
                print("正确: percent=parts[32], change=parts[31]")
                print("错误: 若用 parts[5] 作为 percent 会得到 504 (最高价)")
            break

if __name__ == "__main__":
    main()
