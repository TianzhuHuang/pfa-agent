/**
 * PFA 价格接口代理 — Cloudflare Worker
 *
 * 解决阿里云等机房 IP 被 Binance、Yahoo Finance 封锁的问题。
 * 部署后通过 Worker 转发请求，利用 CF 边缘节点 IP 池访问。
 *
 * 部署: Cloudflare Dashboard -> Workers -> Create -> 粘贴此代码
 * 测试: curl "https://你的worker.workers.dev/proxy?url=binance&symbol=BTCUSDT"
 */

const BINANCE_BASE = "https://api.binance.com";
const YAHOO_BASE = "https://query1.finance.yahoo.com";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname !== "/proxy" && url.pathname !== "/") {
      return new Response("Not Found", { status: 404 });
    }
    if (url.pathname === "/" && !url.searchParams.has("url")) {
      return jsonResponse({
        name: "PFA Price Proxy",
        usage: "/proxy?url=binance&symbol=BTCUSDT | /proxy?url=yahoo&symbol=NIO",
      });
    }

    const target = url.searchParams.get("url"); // binance | yahoo
    const symbol = url.searchParams.get("symbol"); // BTCUSDT | NIO | T14.SI | 00883.HK

    if (!target || !symbol) {
      return jsonResponse({
        error: "Missing params",
        usage: {
          binance: "/proxy?url=binance&symbol=BTCUSDT",
          yahoo: "/proxy?url=yahoo&symbol=NIO",
          yahoo_hk: "/proxy?url=yahoo&symbol=00883.HK",
          yahoo_sgx: "/proxy?url=yahoo&symbol=T14.SI",
        },
      }, 400);
    }

    try {
      if (target === "binance") {
        const res = await fetch(`${BINANCE_BASE}/api/v3/ticker/price?symbol=${encodeURIComponent(symbol)}`, {
          headers: { "User-Agent": "Mozilla/5.0" },
        });
        const data = await res.json();
        return jsonResponse(data, res.status);
      }

      if (target === "yahoo") {
        const chartUrl = `${YAHOO_BASE}/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1d&range=1d`;
        const res = await fetch(chartUrl, {
          headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" },
        });
        const data = await res.json();
        return jsonResponse(data, res.status);
      }

      return jsonResponse({ error: "Unknown target. Use binance or yahoo" }, 400);
    } catch (e) {
      return jsonResponse({ error: String(e.message || e) }, 500);
    }
  },
};

function jsonResponse(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
  });
}
