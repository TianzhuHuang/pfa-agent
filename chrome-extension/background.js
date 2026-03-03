/**
 * PFA 雪球助手 — Background Service Worker
 *
 * 在已登录的浏览器环境内抓取雪球数据，推送到 PFA 本地服务。
 * 因为运行在浏览器扩展中，天然绕过 WAF。
 */

const PFA_SERVER = "http://localhost:8765";
const FETCH_INTERVAL_MIN = 30; // 每 30 分钟自动抓取一次

// ===================================================================
// 雪球 API 抓取（在已登录的浏览器环境中执行，自动带 cookie）
// ===================================================================

async function fetchXueqiuUserTimeline(userId, count = 10) {
  try {
    const resp = await fetch(
      `https://xueqiu.com/v4/statuses/user_timeline.json?user_id=${userId}&page=1&type=0`,
      { credentials: "include" }
    );
    const data = await resp.json();
    const statuses = (data.statuses || []).slice(0, count);
    return statuses.map((s) => ({
      title: s.title || "",
      text: (s.description || s.text || "").replace(/<[^>]+>/g, "").substring(0, 300),
      user: (s.user || {}).screen_name || "",
      user_id: String((s.user || {}).id || userId),
      target: s.target || "",
      created_at: s.created_at || "",
      source: "xueqiu_user",
    }));
  } catch (e) {
    console.error("[PFA] fetchXueqiuUserTimeline error:", e);
    return [];
  }
}

async function fetchXueqiuStockPosts(symbol, count = 10) {
  try {
    const resp = await fetch(
      `https://xueqiu.com/query/v1/symbol/search/status.json?count=${count}&comment=0&symbol=${symbol}&hl=0&source=all&sort=time&page=1&q=&type=11`,
      { credentials: "include" }
    );
    const data = await resp.json();
    return (data.list || []).slice(0, count).map((s) => ({
      title: s.title || "",
      text: (s.text || s.description || "").replace(/<[^>]+>/g, "").substring(0, 300),
      user: (s.user || {}).screen_name || "",
      target: s.target || "",
      created_at: s.created_at || "",
      symbol: symbol,
      source: "xueqiu_stock",
    }));
  } catch (e) {
    console.error("[PFA] fetchXueqiuStockPosts error:", e);
    return [];
  }
}

async function fetchXueqiuFollowList() {
  try {
    let myUid = "";

    // 1) 尝试从 HTML 页面提取 user_id（多种格式兼容雪球改版）
    const pageResp = await fetch("https://xueqiu.com/", { credentials: "include" });
    const html = await pageResp.text();
    const patterns = [
      /"user_id"\s*:\s*"?(\d+)"?/,
      /"uid"\s*:\s*"?(\d+)"?/,
      /SNB\.user_id\s*=\s*["']?(\d+)["']?/,
      /SNB\.userId\s*=\s*["']?(\d+)["']?/,
      /"id"\s*:\s*"?(\d+)"?[^}]*"screen_name"/,
    ];
    for (const re of patterns) {
      const m = html.match(re);
      if (m && m[1]) {
        myUid = m[1];
        break;
      }
    }

    // 2) 若 HTML 未解析到，尝试从 Cookie 的 u 参数获取（雪球登录后会将 u=用户ID 写入 cookie）
    if (!myUid) {
      const cookies = await chrome.cookies.getAll({ domain: ".xueqiu.com" });
      const uCookie = cookies.find((c) => c.name === "u" && c.value && /^\d+$/.test(c.value));
      if (uCookie) myUid = uCookie.value;
    }

    if (!myUid) {
      return { ok: false, ids: [], error: "无法获取当前用户ID，请确保已登录雪球并刷新页面" };
    }
    const resp = await fetch(
      `https://xueqiu.com/friendships/groups/members.json?uid=${myUid}&page=1&gid=0`,
      { credentials: "include" }
    );
    const data = await resp.json();
    const users = data.users || data.list || [];
    const ids = (users).map((u) => String(u.id || u.user_id || "")).filter(Boolean);
    return { ok: true, ids };
  } catch (e) {
    console.error("[PFA] fetchXueqiuFollowList error:", e);
    return { ok: false, ids: [], error: e.message };
  }
}

async function fetchXueqiuPage(url) {
  try {
    const resp = await fetch(url, { credentials: "include" });
    const html = await resp.text();
    // Service Worker 中无 DOMParser，用正则提取文本
    const text = html.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, "").replace(/<style[^>]*>[\s\S]*?<\/style>/gi, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
    const titleMatch = html.match(/<title[^>]*>([^<]*)<\/title>/i);
    return {
      url,
      title: titleMatch ? titleMatch[1].trim() : "",
      content: text.substring(0, 2000),
      source: "xueqiu_page",
    };
  } catch (e) {
    console.error("[PFA] fetchXueqiuPage error:", e);
    return { url, error: e.message, source: "xueqiu_page" };
  }
}

// ===================================================================
// 推送到 PFA 本地服务
// ===================================================================

async function pushToPFA(data) {
  try {
    const resp = await fetch(PFA_SERVER, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return resp.ok;
  } catch (e) {
    console.warn("[PFA] Push failed (server offline?):", e.message);
    return false;
  }
}

// ===================================================================
// 主抓取逻辑
// ===================================================================

async function loadConfigFromPFA() {
  try {
    const resp = await fetch("http://localhost:8000/api/settings/data-sources", { method: "GET" });
    if (resp.ok) {
      const data = await resp.json();
      return {
        userIds: data.xueqiu_user_ids || [],
        monitorUrls: data.monitor_urls || [],
      };
    }
  } catch (e) {
    console.warn("[PFA] Could not load config from API:", e.message);
  }
  return null;
}

async function runFetchAll() {
  console.log("[PFA] Starting fetch cycle...");

  let userIds = [];
  let symbols = [];
  let monitorUrls = [];
  const pfaConfig = await loadConfigFromPFA();
  if (pfaConfig) {
    userIds = pfaConfig.userIds;
    monitorUrls = pfaConfig.monitorUrls;
    const storage = await chrome.storage.local.get(["symbols"]);
    symbols = storage.symbols || [];
  } else {
    const config = await chrome.storage.local.get(["userIds", "symbols", "monitorUrls"]);
    userIds = config.userIds || [];
    symbols = config.symbols || [];
    monitorUrls = config.monitorUrls || [];
  }

  const allResults = { timestamp: new Date().toISOString(), items: [] };

  // Fetch user timelines
  for (const uid of userIds) {
    const posts = await fetchXueqiuUserTimeline(uid, 5);
    allResults.items.push(...posts);
    console.log(`[PFA] User ${uid}: ${posts.length} posts`);
  }

  // Fetch stock discussions
  for (const sym of symbols) {
    const posts = await fetchXueqiuStockPosts(sym, 5);
    allResults.items.push(...posts);
    console.log(`[PFA] Stock ${sym}: ${posts.length} posts`);
  }

  // Fetch monitor URLs
  for (const url of monitorUrls) {
    if (url.includes("xueqiu.com")) {
      const page = await fetchXueqiuPage(url);
      allResults.items.push(page);
      console.log(`[PFA] URL ${url}: fetched`);
    }
  }

  // Push to PFA
  const success = await pushToPFA(allResults);
  console.log(`[PFA] Pushed ${allResults.items.length} items, success=${success}`);

  // Save last fetch info
  await chrome.storage.local.set({
    lastFetch: new Date().toISOString(),
    lastCount: allResults.items.length,
    lastSuccess: success,
  });

  return allResults;
}

// ===================================================================
// 定时任务
// ===================================================================

chrome.alarms.create("pfaFetch", { periodInMinutes: FETCH_INTERVAL_MIN });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "pfaFetch") {
    runFetchAll();
  }
});

// ===================================================================
// 消息处理（来自 popup）
// ===================================================================

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "fetchNow") {
    runFetchAll().then((result) => {
      sendResponse({ success: true, count: result.items.length });
    });
    return true; // async response
  }
  if (msg.action === "saveConfig") {
    chrome.storage.local.set(msg.config).then(() => {
      sendResponse({ success: true });
    });
    return true;
  }
  if (msg.action === "getStatus") {
    chrome.storage.local
      .get(["lastFetch", "lastCount", "lastSuccess", "userIds", "symbols", "monitorUrls"])
      .then((data) => {
        sendResponse(data);
      });
    return true;
  }
  if (msg.action === "getXueqiuCookies") {
    chrome.cookies.getAll({ domain: ".xueqiu.com" }).then((cookies) => {
      sendResponse(cookies);
    });
    return true;
  }
  if (msg.action === "fetchXueqiuFollowList") {
    fetchXueqiuFollowList().then((result) => {
      sendResponse(result);
    });
    return true;
  }
});

// Initial fetch on install
chrome.runtime.onInstalled.addListener(() => {
  // Set default config from PFA data-sources.json
  chrome.storage.local.set({
    userIds: ["9650668145"],
    symbols: ["SH600519", "HK00883", "SH600900"],
    monitorUrls: ["https://xueqiu.com/S/SH600900"],
  });
  console.log("[PFA] Extension installed, default config set");
});
