"use client";

import React, { useState, useEffect, useCallback } from "react";
import { EditAccountsModal } from "@/components/EditAccountsModal";
import { useColorScheme } from "@/contexts/ColorSchemeContext";
import { apiFetch, API_BASE } from "@/lib/api";

type RssItem = { url: string; name?: string; category?: string; enabled?: boolean; via?: string };
type ApiSource = { type: string; name: string; category?: string; mode?: string; enabled?: boolean; api_url?: string };

const CATEGORY_COLORS: Record<string, string> = {
  宏观与快讯: "bg-blue-500/20 text-blue-400",
  深度分析: "bg-purple-500/20 text-purple-400",
  官方公告: "bg-emerald-500/20 text-emerald-400",
  其他: "bg-white/10 text-[#888]",
};

const CATEGORY_OPTIONS = ["宏观与快讯", "深度分析", "官方公告", "其他"];

export default function SettingsPage() {
  const [accounts, setAccounts] = useState<{ id: string; name: string; base_currency: string }[]>([]);
  const [fx, setFx] = useState<{ rates?: Record<string, number>; updated_at?: string } | null>(null);
  const [dataSources, setDataSources] = useState<{
    rss_urls?: (string | RssItem)[];
    api_sources?: ApiSource[];
    twitter_handles?: string[];
    xueqiu_user_ids?: string[];
    monitor_urls?: string[];
    unavailable_sources?: { name: string; reason: string }[];
    self_hosted_rsshub?: string;
  } | null>(null);
  const [editAccountsOpen, setEditAccountsOpen] = useState(false);
  const [refreshingFx, setRefreshingFx] = useState(false);
  const [apiStatus, setApiStatus] = useState<{ dashscope_ok?: boolean; openai_ok?: boolean } | null>(null);
  const [activeTab, setActiveTab] = useState<"subscription" | "social">("subscription");
  const { mode: colorScheme, setMode: setColorScheme } = useColorScheme();

  // RSS add form
  const [newRssUrl, setNewRssUrl] = useState("");
  const [newRssName, setNewRssName] = useState("");
  const [newRssCategory, setNewRssCategory] = useState("宏观与快讯");
  const [rssTestResult, setRssTestResult] = useState<{ idx: number; ok: boolean; msg: string } | null>(null);
  const [rssTestingIdx, setRssTestingIdx] = useState<number | null>(null);
  const [rssEditIdx, setRssEditIdx] = useState<number | null>(null);
  const [rssEditUrl, setRssEditUrl] = useState("");
  const [rssEditName, setRssEditName] = useState("");
  const [rssEditCategory, setRssEditCategory] = useState("宏观与快讯");

  // Social add form
  const [socialType, setSocialType] = useState<"twitter_handles" | "xueqiu_user_ids" | "monitor_urls">("twitter_handles");
  const [socialValue, setSocialValue] = useState("");
  const [socialTestResult, setSocialTestResult] = useState<{ key: string; ok: boolean; msg: string } | null>(null);
  const [socialTestingKey, setSocialTestingKey] = useState<string | null>(null);
  const [xueqiuHasAuth, setXueqiuHasAuth] = useState<boolean | null>(null);
  const [xueqiuCookieExpired, setXueqiuCookieExpired] = useState(false);
  const [xueqiuSyncStatus, setXueqiuSyncStatus] = useState<"idle" | "syncing" | "ok" | "fail" | "no_ext">("idle");
  const [xueqiuSyncMsg, setXueqiuSyncMsg] = useState("");
  const [xueqiuFollowSyncStatus, setXueqiuFollowSyncStatus] = useState<"idle" | "syncing" | "ok" | "fail">("idle");
  const [xueqiuFollowSyncMsg, setXueqiuFollowSyncMsg] = useState("");

  // API source test
  const [apiTestResult, setApiTestResult] = useState<{ type: string; ok: boolean; msg: string } | null>(null);
  const [apiTestingType, setApiTestingType] = useState<string | null>(null);

  const loadAccounts = useCallback(() => {
    apiFetch(`${API_BASE}/api/portfolio/accounts`)
      .then((r) => r.json())
      .then((d) => setAccounts(d.accounts ?? []))
      .catch(() => setAccounts([]));
  }, []);

  const loadFx = useCallback(() => {
    apiFetch(`${API_BASE}/api/portfolio/fx`)
      .then((r) => r.json())
      .then(setFx)
      .catch(() => setFx(null));
  }, []);

  const loadDataSources = useCallback(() => {
    apiFetch(`${API_BASE}/api/settings/data-sources`)
      .then((r) => r.json())
      .then(setDataSources)
      .catch(() => setDataSources(null));
  }, []);

  const loadApiStatus = useCallback(() => {
    apiFetch(`${API_BASE}/api/settings/api-status`)
      .then((r) => r.json())
      .then(setApiStatus)
      .catch(() => setApiStatus(null));
  }, []);

  const loadXueqiuStatus = useCallback(() => {
    apiFetch(`${API_BASE}/api/settings/xueqiu/status`)
      .then((r) => r.json())
      .then((d) => {
        setXueqiuHasAuth(!!d.has_auth);
        setXueqiuCookieExpired(!!d.cookie_expired);
      })
      .catch(() => {
        setXueqiuHasAuth(null);
        setXueqiuCookieExpired(false);
      });
  }, []);

  useEffect(() => {
    loadAccounts();
    loadFx();
    loadDataSources();
    loadApiStatus();
    loadXueqiuStatus();
  }, [loadAccounts, loadFx, loadDataSources, loadApiStatus, loadXueqiuStatus]);

  const syncXueqiuCookie = useCallback(() => {
    setXueqiuSyncStatus("syncing");
    setXueqiuSyncMsg("");
    const apiBase = API_BASE || (typeof window !== "undefined" ? `${window.location.protocol}//${window.location.hostname}:8000` : "http://localhost:8000");
    const responded = { current: false };
    const attempt = { current: 0 };
    const maxAttempts = 2;

    const runAttempt = () => {
      attempt.current += 1;
      const requestId = `pfa-${Date.now()}`;

      const handler = (e: MessageEvent) => {
        const d = e.data;
        if (d?.type !== "PFA_XUEQIU_RESPONSE" || d?.requestId !== requestId || d?.origin !== "pfa-xueqiu-sync") return;
        responded.current = true;
        window.removeEventListener("message", handler);
        let msg = d.msg || "";
        if (!d.ok && (msg.includes("getAll") || msg.includes("undefined"))) {
          msg = "扩展可能未正确加载，请尝试刷新扩展或重新加载页面。";
        }
        setXueqiuSyncStatus(d.ok ? "ok" : "fail");
        setXueqiuSyncMsg(msg);
        if (d.ok) loadXueqiuStatus();
      };

      window.addEventListener("message", handler);
      window.postMessage({ type: "PFA_XUEQIU_SYNC", origin: "pfa-xueqiu-sync", requestId, apiBase }, "*");

      window.setTimeout(() => {
        window.removeEventListener("message", handler);
        if (!responded.current) {
          if (attempt.current < maxAttempts) {
            window.setTimeout(runAttempt, 2000);
          } else {
            setXueqiuSyncStatus("no_ext");
            setXueqiuSyncMsg("插件未响应。请检查扩展是否已启用、是否允许访问 localhost，并刷新页面。");
          }
        }
      }, 2500);
    };

    runAttempt();
  }, [loadXueqiuStatus]);

  const syncXueqiuFollowList = useCallback(() => {
    setXueqiuFollowSyncStatus("syncing");
    setXueqiuFollowSyncMsg("");
    const requestId = `pfa-follows-${Date.now()}`;
    let responded = false;
    const handler = (e: MessageEvent) => {
      const d = e.data;
      if (d?.type !== "PFA_XUEQIU_FOLLOWS_RESPONSE" || d?.requestId !== requestId || d?.origin !== "pfa-xueqiu-sync") return;
      responded = true;
      window.removeEventListener("message", handler);
      if (d.ok && Array.isArray(d.ids)) {
        apiFetch(`${API_BASE}/api/settings/social/xueqiu-user-ids/replace`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ids: d.ids }),
        })
          .then((r) => r.json())
          .then((res) => {
            if (res.ok) {
              setXueqiuFollowSyncStatus("ok");
              setXueqiuFollowSyncMsg(d.ids.length > 0 ? `已同步 ${d.ids.length} 个关注用户` : "关注列表为空");
              loadDataSources();
            } else {
              setXueqiuFollowSyncStatus("fail");
              setXueqiuFollowSyncMsg(res.message || "保存失败");
            }
          })
          .catch(() => {
            setXueqiuFollowSyncStatus("fail");
            setXueqiuFollowSyncMsg("请求失败");
          });
      } else {
        setXueqiuFollowSyncStatus("fail");
        setXueqiuFollowSyncMsg(d?.error || "未获取到关注列表");
      }
    };
    window.addEventListener("message", handler);
    window.postMessage({ type: "PFA_XUEQIU_SYNC_FOLLOWS", requestId, origin: "pfa-xueqiu-sync" }, "*");
    window.setTimeout(() => {
      window.removeEventListener("message", handler);
      if (!responded) {
        setXueqiuFollowSyncStatus("fail");
        setXueqiuFollowSyncMsg("插件未响应，请确认扩展已启用");
      }
    }, 8000);
  }, [loadDataSources]);

  const refreshFx = async () => {
    setRefreshingFx(true);
    try {
      const r = await apiFetch(`${API_BASE}/api/portfolio/fx`);
      const d = await r.json();
      setFx(d);
    } finally {
      setRefreshingFx(false);
    }
  };

  const rssList = (dataSources?.rss_urls ?? []).map((r) =>
    typeof r === "string" ? { url: r, name: "", category: "" } : r
  );
  const apiList = dataSources?.api_sources ?? [];
  const hasDashScope = apiStatus?.dashscope_ok ?? false;
  const hasOpenAI = apiStatus?.openai_ok ?? false;

  const testRss = async (url: string, idx: number) => {
    setRssTestingIdx(idx);
    setRssTestResult(null);
    try {
      const r = await apiFetch(`${API_BASE}/api/settings/rss/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const d = await r.json();
      setRssTestResult({ idx, ok: d.ok ?? false, msg: d.message ?? (d.ok ? "成功" : "失败") });
    } catch {
      setRssTestResult({ idx, ok: false, msg: "请求失败" });
    } finally {
      setRssTestingIdx(null);
    }
  };

  const addRss = async () => {
    const url = newRssUrl.trim();
    if (!url) return;
    try {
      const r = await apiFetch(`${API_BASE}/api/settings/rss`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, name: newRssName.trim(), category: newRssCategory }),
      });
      const d = await r.json();
      if (d.ok) {
        setNewRssUrl("");
        setNewRssName("");
        setNewRssCategory("宏观与快讯");
        loadDataSources();
      }
    } catch {
      // ignore
    }
  };

  const updateRss = async () => {
    if (rssEditIdx == null) return;
    const item = rssList[rssEditIdx];
    if (!item) return;
    const url = rssEditUrl.trim();
    if (!url) return;
    try {
      const r = await apiFetch(`${API_BASE}/api/settings/rss`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          old_url: item.url,
          url,
          name: rssEditName.trim(),
          category: rssEditCategory,
        }),
      });
      const d = await r.json();
      if (d.ok) {
        setRssEditIdx(null);
        loadDataSources();
      }
    } catch {
      // ignore
    }
  };

  const deleteRss = async (url: string) => {
    if (!confirm("确定删除该 RSS 订阅？")) return;
    try {
      const r = await apiFetch(`${API_BASE}/api/settings/rss?url=${encodeURIComponent(url)}`, { method: "DELETE" });
      const d = await r.json();
      if (d.ok) loadDataSources();
    } catch {
      // ignore
    }
  };

  const toggleApi = async (type: string, enabled: boolean) => {
    try {
      const r = await apiFetch(`${API_BASE}/api/settings/api-sources/${type}/toggle`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      const d = await r.json();
      if (d.ok) loadDataSources();
    } catch {
      // ignore
    }
  };

  const testApi = async (type: string) => {
    setApiTestingType(type);
    setApiTestResult(null);
    try {
      const r = await apiFetch(`${API_BASE}/api/settings/api-sources/test?source_type=${encodeURIComponent(type)}`, {
        method: "POST",
      });
      const d = await r.json();
      setApiTestResult({ type, ok: d.ok ?? false, msg: d.message ?? "" });
    } catch {
      setApiTestResult({ type, ok: false, msg: "请求失败" });
    } finally {
      setApiTestingType(null);
    }
  };

  const extractXueqiuId = (input: string): string => {
    const s = input.trim();
    const m = s.match(/xueqiu\.com\/u\/(\d+)/i);
    if (m) return m[1];
    if (/^\d+$/.test(s)) return s;
    return s;
  };

  const addSocial = async () => {
    const val = socialValue.trim();
    if (!val) return;
    const valueToSend =
      socialType === "xueqiu_user_ids" ? extractXueqiuId(val) : socialType === "twitter_handles" ? val.replace(/^@/, "") : val;
    if (!valueToSend) return;
    try {
      const r = await apiFetch(`${API_BASE}/api/settings/social`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: socialType, value: valueToSend }),
      });
      const d = await r.json();
      if (d.ok) {
        setSocialValue("");
        loadDataSources();
      }
    } catch {
      // ignore
    }
  };

  const removeSocial = async (type: string, value: string) => {
    if (!confirm("确定删除？")) return;
    try {
      const r = await apiFetch(
        `${API_BASE}/api/settings/social?type=${encodeURIComponent(type)}&value=${encodeURIComponent(value)}`,
        { method: "DELETE" }
      );
      const d = await r.json();
      if (d.ok) loadDataSources();
    } catch {
      // ignore
    }
  };

  const testSocial = async (type: string, value: string) => {
    const key = `${type}:${value}`;
    setSocialTestingKey(key);
    setSocialTestResult(null);
    try {
      const r = await apiFetch(
        `${API_BASE}/api/settings/social/test?type=${encodeURIComponent(type)}&value=${encodeURIComponent(value)}`,
        { method: "POST" }
      );
      const text = await r.text();
      let d: { ok?: boolean; message?: string } = {};
      try {
        d = text ? JSON.parse(text) : {};
      } catch {
        setSocialTestResult({ key, ok: false, msg: r.ok ? "响应格式异常" : `HTTP ${r.status}` });
        return;
      }
      setSocialTestResult({ key, ok: d.ok ?? false, msg: d.message ?? "" });
    } catch (e) {
      setSocialTestResult({ key, ok: false, msg: "请求失败" });
    } finally {
      setSocialTestingKey(null);
    }
  };

  const startEditRss = (idx: number) => {
    const item = rssList[idx];
    if (item) {
      setRssEditIdx(idx);
      setRssEditUrl(item.url);
      setRssEditName(item.name ?? "");
      setRssEditCategory(item.category ?? "宏观与快讯");
    }
  };

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="mb-8 text-xl font-semibold text-white">系统设置</h1>

      <div className="space-y-8">
        {/* 界面显示 */}
        <div className="rounded-lg overflow-hidden border border-white/5 bg-[#0a0a0a]">
          <div className="border-b border-white/5 px-4 py-3">
            <span className="text-sm font-medium text-[#888888]">界面显示</span>
          </div>
          <div className="divide-y divide-white/5">
            <div className="flex items-center justify-between px-4 py-3">
              <div>
                <div className="font-medium text-white">涨跌颜色</div>
                <div className="text-xs text-[#666]">绿涨红跌（国际） / 红涨绿跌（A股）</div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setColorScheme("green_up")}
                  className={`rounded px-3 py-1.5 text-xs font-medium transition-colors ${
                    colorScheme === "green_up" ? "bg-[#00e701]/20 text-[#00e701]" : "bg-white/5 text-[#888] hover:bg-white/10"
                  }`}
                >
                  绿涨红跌
                </button>
                <button
                  onClick={() => setColorScheme("red_up")}
                  className={`rounded px-3 py-1.5 text-xs font-medium transition-colors ${
                    colorScheme === "red_up" ? "bg-[#ff4e33]/20 text-[#ff4e33]" : "bg-white/5 text-[#888] hover:bg-white/10"
                  }`}
                >
                  红涨绿跌
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* 账户中心 */}
        <div className="rounded-lg overflow-hidden border border-white/5 bg-[#0a0a0a]">
          <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
            <span className="text-sm font-medium text-[#888888]">账户中心</span>
            <button
              onClick={() => setEditAccountsOpen(true)}
              className="text-sm text-[#1976d2] hover:text-[#42a5f5]"
            >
              编辑
            </button>
          </div>
          <div className="divide-y divide-white/5">
            {accounts.length === 0 ? (
              <div className="px-4 py-6 text-center text-sm text-[#666]">暂无账户</div>
            ) : (
              accounts.map((a) => (
                <div key={a.id} className="flex items-center justify-between px-4 py-3">
                  <span className="font-medium text-white">{a.name}</span>
                  <span className="text-sm text-[#888]">{a.base_currency || "CNY"}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* API 配置 */}
        <div className="rounded-lg overflow-hidden border border-white/5 bg-[#0a0a0a]">
          <div className="border-b border-white/5 px-4 py-3">
            <span className="text-sm font-medium text-[#888888]">API 配置</span>
          </div>
          <div className="divide-y divide-white/5">
            <div className="flex items-center justify-between px-4 py-3">
              <div>
                <div className="font-medium text-white">通义千问 (DashScope)</div>
                <div className="text-xs text-[#666]">Analyst / OCR</div>
              </div>
              <span
                className={`inline-flex h-6 items-center rounded-full px-2.5 text-xs font-medium ${
                  hasDashScope ? "bg-[#00e701]/20 text-[#00e701]" : "bg-white/10 text-[#888]"
                }`}
              >
                {hasDashScope ? "已配置" : "未配置"}
              </span>
            </div>
            <div className="flex items-center justify-between px-4 py-3">
              <div>
                <div className="font-medium text-white">OpenAI</div>
                <div className="text-xs text-[#666]">Auditor 交叉校验</div>
              </div>
              <span
                className={`inline-flex h-6 items-center rounded-full px-2.5 text-xs font-medium ${
                  hasOpenAI ? "bg-[#00e701]/20 text-[#00e701]" : "bg-white/10 text-[#888]"
                }`}
              >
                {hasOpenAI ? "已配置" : "未配置"}
              </span>
            </div>
          </div>
          <div className="border-t border-white/5 px-4 py-2 text-xs text-[#666]">
            在项目根目录 .env 中配置 DASHSCOPE_API_KEY、OPENAI_API_KEY
          </div>
        </div>

        {/* 汇率管理 */}
        <div className="rounded-lg overflow-hidden border border-white/5 bg-[#0a0a0a]">
          <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
            <span className="text-sm font-medium text-[#888888]">参考汇率</span>
            <button
              onClick={refreshFx}
              disabled={refreshingFx}
              className="text-sm text-[#1976d2] hover:text-[#42a5f5] disabled:opacity-50"
            >
              {refreshingFx ? "刷新中..." : "强制刷新"}
            </button>
          </div>
          <div className="divide-y divide-white/5 px-4 py-3">
            {fx?.rates ? (
              <>
                <div className="flex justify-between py-2 text-sm">
                  <span className="text-[#888]">1 USD</span>
                  <span className="text-white">≈ {fx.rates.USD?.toFixed(4)} CNY</span>
                </div>
                <div className="flex justify-between py-2 text-sm">
                  <span className="text-[#888]">1 HKD</span>
                  <span className="text-white">≈ {fx.rates.HKD?.toFixed(4)} CNY</span>
                </div>
                {fx.updated_at && (
                  <div className="pt-2 text-xs text-[#666]">更新于 {fx.updated_at?.slice(0, 19)}</div>
                )}
              </>
            ) : (
              <div className="py-4 text-center text-sm text-[#666]">暂无汇率数据</div>
            )}
          </div>
        </div>

        {/* 数据源 — Tab 切换 */}
        <div className="rounded-lg overflow-hidden border border-white/5 bg-[#0a0a0a]">
          <div className="flex border-b border-white/5">
            <button
              onClick={() => setActiveTab("subscription")}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === "subscription"
                  ? "border-b-2 border-[#1976d2] text-white"
                  : "text-[#888] hover:text-white"
              }`}
            >
              订阅与 API
            </button>
            <button
              onClick={() => setActiveTab("social")}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === "social" ? "border-b-2 border-[#1976d2] text-white" : "text-[#888] hover:text-white"
              }`}
            >
              社交与监控
            </button>
          </div>

          {activeTab === "subscription" && (
            <div className="divide-y divide-white/5">
              {/* RSS 订阅 */}
              <div className="p-4">
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-sm font-medium text-[#888888]">RSS 订阅</span>
                  <span className="text-xs text-[#666]">{rssList.length} 条</span>
                </div>

                {/* 添加 RSS */}
                <div className="mb-4 rounded border border-white/5 bg-black/30 p-3">
                  <div className="mb-2 text-xs text-[#888]">添加订阅</div>
                  <div className="space-y-2">
                    <input
                      type="url"
                      placeholder="RSS URL"
                      value={newRssUrl}
                      onChange={(e) => setNewRssUrl(e.target.value)}
                      className="w-full rounded border border-white/10 bg-black/50 px-3 py-2 text-sm text-white placeholder:text-[#666] focus:border-[#1976d2]/50 focus:outline-none"
                    />
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="名称"
                        value={newRssName}
                        onChange={(e) => setNewRssName(e.target.value)}
                        className="flex-1 rounded border border-white/10 bg-black/50 px-3 py-2 text-sm text-white placeholder:text-[#666] focus:border-[#1976d2]/50 focus:outline-none"
                      />
                      <select
                        value={newRssCategory}
                        onChange={(e) => setNewRssCategory(e.target.value)}
                        className="rounded border border-white/10 bg-black/50 px-3 py-2 text-sm text-white focus:border-[#1976d2]/50 focus:outline-none"
                      >
                        {CATEGORY_OPTIONS.map((c) => (
                          <option key={c} value={c} className="bg-[#1a1a1a]">
                            {c}
                          </option>
                        ))}
                      </select>
                    </div>
                    <button
                      onClick={addRss}
                      disabled={!newRssUrl.trim()}
                      className="rounded bg-[#1976d2] px-4 py-2 text-sm text-white hover:bg-[#1565c0] disabled:opacity-50"
                    >
                      添加 RSS
                    </button>
                  </div>
                </div>

                {/* RSS 列表 */}
                <div className="space-y-1">
                  {rssList.length === 0 ? (
                    <div className="py-6 text-center text-sm text-[#666]">暂无 RSS</div>
                  ) : (
                    rssList.map((item, i) => {
                      if (rssEditIdx === i) {
                        return (
                          <div key={i} className="rounded border border-white/10 bg-black/30 p-3">
                            <input
                              type="url"
                              value={rssEditUrl}
                              onChange={(e) => setRssEditUrl(e.target.value)}
                              className="mb-2 w-full rounded border border-white/10 bg-black/50 px-2 py-1.5 text-sm text-white focus:outline-none"
                              placeholder="URL"
                            />
                            <div className="mb-2 flex gap-2">
                              <input
                                type="text"
                                value={rssEditName}
                                onChange={(e) => setRssEditName(e.target.value)}
                                className="flex-1 rounded border border-white/10 bg-black/50 px-2 py-1.5 text-sm text-white focus:outline-none"
                                placeholder="名称"
                              />
                              <select
                                value={rssEditCategory}
                                onChange={(e) => setRssEditCategory(e.target.value)}
                                className="rounded border border-white/10 bg-black/50 px-2 py-1.5 text-sm text-white focus:outline-none"
                              >
                                {CATEGORY_OPTIONS.map((c) => (
                                  <option key={c} value={c} className="bg-[#1a1a1a]">
                                    {c}
                                  </option>
                                ))}
                              </select>
                            </div>
                            <div className="flex gap-2">
                              <button
                                onClick={updateRss}
                                className="rounded bg-[#00e701]/20 px-3 py-1.5 text-xs text-[#00e701] hover:bg-[#00e701]/30"
                              >
                                保存
                              </button>
                              <button
                                onClick={() => setRssEditIdx(null)}
                                className="rounded bg-white/10 px-3 py-1.5 text-xs text-[#888] hover:bg-white/20"
                              >
                                取消
                              </button>
                            </div>
                          </div>
                        );
                      }
                      const cat = item.category || "其他";
                      const tagClass = CATEGORY_COLORS[cat] ?? CATEGORY_COLORS.其他;
                      const testOk = rssTestResult?.idx === i ? rssTestResult.ok : null;
                      return (
                        <div
                          key={i}
                          className="flex items-center justify-between gap-2 rounded border border-white/5 bg-black/20 px-3 py-2"
                        >
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className="truncate text-sm font-medium text-white">{item.name || "—"}</span>
                              <span className={`shrink-0 rounded px-1.5 py-0.5 text-xs ${tagClass}`}>{cat}</span>
                            </div>
                            <div className="truncate text-xs text-[#666]">{item.url}</div>
                            {testOk !== null && (
                              <span
                                className={`mt-1 inline-block text-xs ${
                                  testOk ? "text-[#00e701]" : "text-red-400"
                                }`}
                              >
                                {testOk ? "✅ 连接成功" : "❌ 抓取失败"}
                                {rssTestResult?.idx === i && ` — ${rssTestResult.msg}`}
                              </span>
                            )}
                          </div>
                          <div className="flex shrink-0 gap-1">
                            <button
                              onClick={() => testRss(item.url, i)}
                              disabled={rssTestingIdx === i}
                              className="rounded px-2 py-1 text-xs text-[#1976d2] hover:bg-white/10 disabled:opacity-50"
                            >
                              {rssTestingIdx === i ? "测试中..." : "测试"}
                            </button>
                            <button
                              onClick={() => startEditRss(i)}
                              className="rounded px-2 py-1 text-xs text-[#888] hover:bg-white/10 hover:text-white"
                            >
                              编辑
                            </button>
                            <button
                              onClick={() => deleteRss(item.url)}
                              className="rounded px-2 py-1 text-xs text-red-400 hover:bg-red-500/10"
                            >
                              删除
                            </button>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* API 数据源 */}
              {apiList.length > 0 && (
                <div className="border-t border-white/5 p-4">
                  <div className="mb-3 text-sm font-medium text-[#888888]">API 数据源</div>
                  <div className="space-y-2">
                    {apiList.map((src) => (
                      <div
                        key={src.type}
                        className="flex items-center justify-between gap-2 rounded border border-white/5 bg-black/20 px-3 py-2"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-white">{src.name}</span>
                            <span
                              className={`shrink-0 rounded px-1.5 py-0.5 text-xs ${
                                src.enabled ? "bg-[#00e701]/20 text-[#00e701]" : "bg-white/10 text-[#888]"
                              }`}
                            >
                              {src.enabled ? "✅ 启用" : "⚪ 禁用"}
                            </span>
                          </div>
                          <div className="text-xs text-[#666]">
                            {src.category ?? ""} · {src.mode === "global" ? "全局" : "按标的"}
                          </div>
                          {apiTestResult?.type === src.type && (
                            <span
                              className={`mt-1 inline-block text-xs ${
                                apiTestResult.ok ? "text-[#00e701]" : "text-red-400"
                              }`}
                            >
                              {apiTestResult.ok ? "✅" : "❌"} {apiTestResult.msg}
                            </span>
                          )}
                        </div>
                        <div className="flex shrink-0 gap-1">
                          <button
                            onClick={() => toggleApi(src.type, !src.enabled)}
                            className="rounded px-2 py-1 text-xs text-[#888] hover:bg-white/10 hover:text-white"
                          >
                            {src.enabled ? "禁用" : "启用"}
                          </button>
                          <button
                            onClick={() => testApi(src.type)}
                            disabled={apiTestingType === src.type}
                            className="rounded px-2 py-1 text-xs text-[#1976d2] hover:bg-white/10 disabled:opacity-50"
                          >
                            {apiTestingType === src.type ? "测试中..." : "测试"}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* RSSHub */}
              <div className="border-t border-white/5 px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[#888]">RSSHub:</span>
                  <input
                    type="url"
                    defaultValue={dataSources?.self_hosted_rsshub ?? "http://localhost:1200"}
                    onBlur={(e) => {
                      const v = e.target.value.trim();
                      if (v && v !== dataSources?.self_hosted_rsshub) {
                        apiFetch(`${API_BASE}/api/settings/rsshub`, {
                          method: "PUT",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ url: v }),
                        }).then(() => loadDataSources());
                      }
                    }}
                    className="flex-1 rounded border border-white/10 bg-black/50 px-2 py-1.5 text-xs text-white focus:outline-none"
                    placeholder="http://localhost:1200"
                  />
                </div>
                <div className="mt-1 text-xs text-[#666]">本地 RSSHub 地址，失焦自动保存</div>
              </div>

              {/* 待激活 */}
              {(dataSources?.unavailable_sources?.length ?? 0) > 0 && (
                <div className="border-t border-white/5 p-4">
                  <div className="mb-2 text-sm font-medium text-[#888888]">待激活数据源</div>
                  <div className="space-y-1 text-xs text-[#666]">
                    {dataSources!.unavailable_sources!.map((s, i) => (
                      <div key={i}>
                        {s.name} — {s.reason}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "social" && (
            <div className="divide-y divide-white/5 p-4">
              {/* 添加社交源 */}
              <div className="mb-4 rounded border border-white/5 bg-black/30 p-3">
                <div className="mb-2 text-xs text-[#888]">添加监控源</div>
                <div className="flex gap-2">
                  <select
                    value={socialType}
                    onChange={(e) => setSocialType(e.target.value as typeof socialType)}
                    className="rounded border border-white/10 bg-black/50 px-3 py-2 text-sm text-white focus:outline-none"
                  >
                    <option value="twitter_handles" className="bg-[#1a1a1a]">
                      Twitter
                    </option>
                    <option value="xueqiu_user_ids" className="bg-[#1a1a1a]">
                      雪球用户
                    </option>
                    <option value="monitor_urls" className="bg-[#1a1a1a]">
                      监控 URL
                    </option>
                  </select>
                  <input
                    type="text"
                    placeholder={
                      socialType === "twitter_handles"
                        ? "@elonmusk"
                        : socialType === "xueqiu_user_ids"
                          ? "雪球主页链接或用户 ID"
                          : "https://..."
                    }
                    value={socialValue}
                    onChange={(e) => setSocialValue(e.target.value)}
                    className="flex-1 rounded border border-white/10 bg-black/50 px-3 py-2 text-sm text-white placeholder:text-[#666] focus:outline-none"
                  />
                  <button
                    onClick={addSocial}
                    disabled={!socialValue.trim()}
                    className="rounded bg-[#1976d2] px-4 py-2 text-sm text-white hover:bg-[#1565c0] disabled:opacity-50"
                  >
                    添加
                  </button>
                </div>
              </div>

              {/* Twitter */}
              <SocialList
                title="Twitter"
                type="twitter_handles"
                items={dataSources?.twitter_handles ?? []}
                format={(v) => `@${v}`}
                onTest={testSocial}
                onRemove={removeSocial}
                testResult={socialTestResult}
                testingKey={socialTestingKey}
                testNote="需登录或配置 API Key"
              />

              {/* 雪球 */}
              <div className="py-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-[#888888]">雪球</span>
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex h-6 items-center rounded-full px-2.5 text-xs font-medium ${
                        xueqiuCookieExpired
                          ? "animate-pulse bg-red-500/30 text-red-400"
                          : xueqiuHasAuth
                            ? "bg-[#00e701]/20 text-[#00e701]"
                            : "bg-white/10 text-[#888]"
                      }`}
                    >
                      {xueqiuHasAuth === null ? "—" : xueqiuCookieExpired ? "Cookie 已失效" : xueqiuHasAuth ? "已授权" : "需要登录"}
                    </span>
                    <button
                      onClick={syncXueqiuCookie}
                      disabled={xueqiuSyncStatus === "syncing"}
                      className="rounded bg-[#1976d2] px-3 py-1.5 text-xs text-white hover:bg-[#1565c0] disabled:opacity-50"
                    >
                      {xueqiuSyncStatus === "syncing" ? "同步中..." : "同步 Cookie"}
                    </button>
                    <button
                      onClick={syncXueqiuFollowList}
                      disabled={xueqiuFollowSyncStatus === "syncing"}
                      className="rounded border border-white/20 px-3 py-1.5 text-xs text-white hover:bg-white/10 disabled:opacity-50"
                    >
                      {xueqiuFollowSyncStatus === "syncing" ? "同步中..." : "同步关注列表"}
                    </button>
                  </div>
                </div>
                {xueqiuFollowSyncStatus === "ok" && xueqiuFollowSyncMsg && (
                  <div className="mb-2 text-xs text-[#00e701]">✅ {xueqiuFollowSyncMsg}</div>
                )}
                {xueqiuFollowSyncStatus === "fail" && xueqiuFollowSyncMsg && (
                  <div className="mb-2 text-xs text-red-400">⚠️ {xueqiuFollowSyncMsg}</div>
                )}
                {xueqiuCookieExpired && (
                  <div className="mb-2 rounded border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
                    Cookie 已失效，请重新同步
                  </div>
                )}
                {(xueqiuSyncStatus === "no_ext" || xueqiuSyncStatus === "fail") && !xueqiuCookieExpired && (
                  <div className="mb-2 rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-400">
                    ⚠️ 雪球需通过 Chrome 扩展访问，请确认扩展已安装并登录。
                    <a href="/docs/xueqiu-extension" className="ml-2 text-[#1976d2] hover:underline">
                      下载扩展程序
                    </a>
                    {xueqiuSyncMsg && <span className="block mt-1 text-[#888]">{xueqiuSyncMsg}</span>}
                  </div>
                )}
                {xueqiuSyncStatus === "ok" && xueqiuSyncMsg && (
                  <div className="mb-2 text-xs text-[#00e701]">✅ {xueqiuSyncMsg}</div>
                )}
                <SocialList
                  title=""
                  type="xueqiu_user_ids"
                  items={dataSources?.xueqiu_user_ids ?? []}
                  format={(v) => v}
                  onTest={testSocial}
                  onRemove={removeSocial}
                  testResult={socialTestResult}
                  testingKey={socialTestingKey}
                  testNote="需 Cookie 登录"
                  hideTitle
                />
              </div>

              {/* 监控 URL */}
              <SocialList
                title="监控 URL"
                type="monitor_urls"
                items={dataSources?.monitor_urls ?? []}
                format={(v) => v}
                onTest={testSocial}
                onRemove={removeSocial}
                testResult={socialTestResult}
                testingKey={socialTestingKey}
              />
            </div>
          )}
        </div>
      </div>

      <EditAccountsModal open={editAccountsOpen} onClose={() => setEditAccountsOpen(false)} onUpdated={loadAccounts} />
    </div>
  );
}

function SocialList({
  title,
  type,
  items,
  format,
  onTest,
  onRemove,
  testResult,
  testingKey,
  testNote,
  hideTitle,
}: {
  title: string;
  type: string;
  items: string[];
  format: (v: string) => string;
  onTest: (type: string, value: string) => void;
  onRemove: (type: string, value: string) => void;
  testResult: { key: string; ok: boolean; msg: string } | null;
  testingKey: string | null;
  testNote?: string;
  hideTitle?: boolean;
}) {
  return (
    <div className="py-3">
      {!hideTitle && <div className="mb-2 text-sm font-medium text-[#888888]">{title}</div>}
      {items.length === 0 ? (
        <div className="text-xs text-[#666]">暂无</div>
      ) : (
        <div className="space-y-1">
          {items.map((v) => {
            const key = `${type}:${v}`;
            const testing = testingKey === key;
            const result = testResult?.key === key ? testResult : null;
            return (
              <div
                key={v}
                className="flex items-center justify-between gap-2 rounded border border-white/5 bg-black/20 px-3 py-2"
              >
                <div className="min-w-0 flex-1">
                  <span className="truncate text-sm text-white">{format(v)}</span>
                  {result && (
                    <span className={`block text-xs ${result.ok ? "text-[#00e701]" : "text-amber-400"}`}>
                      {result.ok ? "✅" : "⚠️"} {result.msg}
                    </span>
                  )}
                </div>
                <div className="flex shrink-0 gap-1">
                  <button
                    onClick={() => onTest(type, v)}
                    disabled={testing}
                    className="rounded px-2 py-1 text-xs text-[#1976d2] hover:bg-white/10 disabled:opacity-50"
                  >
                    {testing ? "测试中..." : "测试"}
                  </button>
                  <button
                    onClick={() => onRemove(type, v)}
                    className="rounded px-2 py-1 text-xs text-red-400 hover:bg-red-500/10"
                  >
                    删除
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
      {testNote && items.length > 0 && (
        <div className="mt-1 text-xs text-[#666]">{testNote}</div>
      )}
    </div>
  );
}
