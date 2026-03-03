/**
 * PFA 雪球助手 — Content Script
 * 在 PFA 设置页面 (localhost:3000/8000) 注入，响应「同步 Cookie」和「同步关注列表」请求
 */

const PFA_ORIGIN = "pfa-xueqiu-sync";

window.addEventListener("message", async (event) => {
  if (event.data?.origin !== PFA_ORIGIN) return;

  if (event.data?.type === "PFA_XUEQIU_SYNC_FOLLOWS") {
    const { requestId } = event.data;
    try {
      const result = await chrome.runtime.sendMessage({ action: "fetchXueqiuFollowList" });
      window.postMessage(
        {
          type: "PFA_XUEQIU_FOLLOWS_RESPONSE",
          requestId,
          ok: result?.ok ?? false,
          ids: result?.ids ?? [],
          error: result?.error,
          origin: PFA_ORIGIN,
        },
        "*"
      );
    } catch (e) {
      window.postMessage(
        {
          type: "PFA_XUEQIU_FOLLOWS_RESPONSE",
          requestId,
          ok: false,
          ids: [],
          error: e?.message || "扩展未响应",
          origin: PFA_ORIGIN,
        },
        "*"
      );
    }
    return;
  }

  if (event.data?.type !== "PFA_XUEQIU_SYNC") return;

  const { requestId, apiBase = "http://localhost:8000" } = event.data;

  const sendResponse = (ok, msg, hasAuth) => {
    window.postMessage(
      { type: "PFA_XUEQIU_RESPONSE", requestId, ok, msg, hasAuth, origin: PFA_ORIGIN },
      "*"
    );
  };

  try {
    const cookies = await chrome.runtime.sendMessage({ action: "getXueqiuCookies" });
    if (!cookies || !Array.isArray(cookies)) {
      sendResponse(false, "扩展未响应。请检查扩展是否已启用并刷新页面", false);
      return;
    }
    const hasToken = cookies.some((c) => c.name === "xq_a_token" && c.value);
    const isLogin = cookies.some((c) => c.name === "xq_is_login" && c.value === "1");

    if (!hasToken && !isLogin) {
      sendResponse(false, "雪球未登录，请先在浏览器中打开 xueqiu.com 并登录", false);
      return;
    }

    const cookieStr = cookies.map((c) => `${c.name}=${c.value}`).join("; ");
    const resp = await fetch(`${apiBase.replace(/\/$/, "")}/api/settings/xueqiu/cookie`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cookie: cookieStr, has_login: isLogin }),
    });

    const data = await resp.json().catch(() => ({}));
    if (resp.ok && data.ok) {
      sendResponse(true, "Cookie 已同步", true);
    } else {
      sendResponse(false, data.error || data.message || "同步失败", false);
    }
  } catch (e) {
    sendResponse(false, `请求失败: ${e.message}`, false);
  }
});
