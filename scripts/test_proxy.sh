#!/bin/bash
# 在 ECS 上测试 Cloudflare Worker 代理
# 用法: bash scripts/test_proxy.sh https://pfa-proxy.你的子域名.workers.dev

WORKER="${1:?请传入 Worker 地址，如 https://pfa-proxy.xxx.workers.dev}"

echo "=== 测试 Worker: $WORKER ==="
echo ""

echo "1. Binance BTC:"
OUT=$(curl -s "${WORKER}/proxy?url=binance&symbol=BTCUSDT")
if echo "$OUT" | grep -q '"price"'; then
  echo "  ✓ 成功: $(echo "$OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('symbol',''), '=', d.get('price',''))" 2>/dev/null || echo "$OUT" | head -c 80)"
else
  echo "  ✗ 失败: ${OUT:0:120}"
fi

echo ""
echo "2. Yahoo 美股 NIO:"
OUT=$(curl -s "${WORKER}/proxy?url=yahoo&symbol=NIO")
if echo "$OUT" | grep -q '"chart"'; then
  P=$(echo "$OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('chart',{}).get('result',[]); m=r[0].get('meta',{}) if r else {}; print(m.get('regularMarketPrice') or m.get('previousClose','?'))" 2>/dev/null)
  echo "  ✓ 成功: NIO = $P"
else
  echo "  ✗ 失败: ${OUT:0:120}"
fi

echo ""
echo "3. Yahoo 新加坡 T14.SI:"
OUT=$(curl -s "${WORKER}/proxy?url=yahoo&symbol=T14.SI")
if echo "$OUT" | grep -q '"chart"'; then
  P=$(echo "$OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('chart',{}).get('result',[]); m=r[0].get('meta',{}) if r else {}; print(m.get('regularMarketPrice') or m.get('previousClose','?'))" 2>/dev/null)
  echo "  ✓ 成功: T14.SI = $P"
else
  echo "  ✗ 失败: ${OUT:0:120}"
fi

echo ""
echo "=== 测试完成 ==="
