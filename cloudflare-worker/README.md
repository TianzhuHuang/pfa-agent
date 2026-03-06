# PFA 价格接口代理 — Cloudflare Worker

解决阿里云等机房 IP 被 Binance、Yahoo Finance 封锁的问题。

## 1. 部署 Worker

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 左侧 **Workers & Pages** → **Create** → **Create Worker**
3. 命名为 `pfa-proxy`（或任意名称）
4. 点击 **Edit code**，删除默认内容，粘贴 `index.js` 全部代码
5. **Save and Deploy**
6. 记下 Worker 地址，如 `https://pfa-proxy.你的子域名.workers.dev`

## 2. 在阿里云 ECS 上测试

将 `YOUR_WORKER_URL` 替换为你的 Worker 地址。

### 测试 Binance（比特币）

```bash
curl -s "https://YOUR_WORKER_URL/proxy?url=binance&symbol=BTCUSDT"
```

预期：`{"symbol":"BTCUSDT","price":"XXXXX.XX"}`

### 测试 Yahoo 美股（蔚来 NIO）

```bash
curl -s "https://YOUR_WORKER_URL/proxy?url=yahoo&symbol=NIO"
```

预期：返回 chart 行情 JSON，含 `regularMarketPrice` 等字段。

### 测试 Yahoo 港股（中海油 00883）

```bash
curl -s "https://YOUR_WORKER_URL/proxy?url=yahoo&symbol=00883.HK"
```

### 测试 Yahoo 新加坡股（T14）

```bash
curl -s "https://YOUR_WORKER_URL/proxy?url=yahoo&symbol=T14.SI"
```

预期：不再出现 `Network unreachable` 或 `HTTP 403`。

## 3. 一键测试脚本

在 ECS 上执行（先替换 Worker URL）：

```bash
WORKER="https://pfa-proxy.你的子域名.workers.dev"

echo "=== Binance BTC ==="
curl -s "${WORKER}/proxy?url=binance&symbol=BTCUSDT" | head -c 200

echo -e "\n\n=== Yahoo NIO ==="
curl -s "${WORKER}/proxy?url=yahoo&symbol=NIO" | head -c 300

echo -e "\n\n=== Yahoo T14.SI ==="
curl -s "${WORKER}/proxy?url=yahoo&symbol=T14.SI" | head -c 300
```

## 4. 后续集成

测试通过后，可在 `pfa/crypto_quote.py`、`pfa/sgx_quote.py`、`pfa/realtime_quote.py` 中配置 `PFA_PROXY_URL` 环境变量，请求时优先走 Worker 代理。
