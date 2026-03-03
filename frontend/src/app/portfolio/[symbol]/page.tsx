"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { ChatMessage } from "@/components/ChatMessage";
import { apiFetch, API_BASE } from "@/lib/api";
import { useDisplayCurrency } from "@/contexts/DisplayCurrencyContext";
import { useColorScheme } from "@/contexts/ColorSchemeContext";
import { CurrencyDropdown } from "@/components/CurrencyDropdown";
import { usePageVisibility } from "@/hooks/usePageVisibility";
import { isTradingHours } from "@/lib/tradingHours";
import { DETAIL_REFRESH_INTERVAL } from "@/lib/refreshConstants";

interface TickerSession {
  session_id: string;
  first_question: string;
  updated_at: string;
}

interface HoldingRow {
  symbol?: string;
  name?: string;
  current_price?: number;
  cost_price?: number;
  quantity?: number;
  value_cny?: number;
  value_local?: number;
  value_display?: number | null;
  currency_error?: boolean;
  currency?: string;
  pnl_cny?: number;
  pnl_pct?: number;
  today_pct?: number;
  today_pnl?: number;
  position_pct?: number;
  account?: string;
  exchange?: string;
  market?: string;
  source?: string;
}

interface PortfolioVal {
  target_currency?: string;
  fx_rates?: Record<string, number>;
  by_account?: Record<string, { holdings: HoldingRow[] }>;
}

interface FeedItem {
  id: string;
  title: string;
  url: string;
  published_at: string;
  content_snippet: string;
  source: string;
  source_id: string;
}

interface TimelineEvent {
  id: string;
  timestamp: string;
  event_type: string;
  content: string;
  reasoning?: string;
}

function currencySymbol(c: string): string {
  return { CNY: "¥", USD: "$", HKD: "HK$" }[c] ?? c;
}

export default function StockDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const symbol = (params?.symbol as string) || "";
  const urlSessionId = searchParams?.get("session_id") ?? null;
  const [val, setVal] = useState<PortfolioVal | null>(null);
  const [loading, setLoading] = useState(true);
  const { displayCurrency } = useDisplayCurrency();
  const { upColor, downColor, upBadge, downBadge } = useColorScheme();
  const [feedItems, setFeedItems] = useState<FeedItem[]>([]);
  const [feedLoading, setFeedLoading] = useState(false);
  const [fetchingNews, setFetchingNews] = useState(false);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [activeTab, setActiveTab] = useState<"overview" | "sentiment" | "trades">("overview");
  const [sentiment, setSentiment] = useState<{ label?: string; reason?: string; score?: number } | null>(null);
  const [tickerMessages, setTickerMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [tickerInput, setTickerInput] = useState("");
  const [tickerStreaming, setTickerStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [historyPanelOpen, setHistoryPanelOpen] = useState(false);
  const [historySessions, setHistorySessions] = useState<TickerSession[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const tickerScrollRef = useRef<HTMLDivElement>(null);
  const visible = usePageVisibility();

  const holdings: HoldingRow[] = [];
  if (val?.by_account) {
    for (const acct of Object.values(val.by_account)) {
      for (const h of acct.holdings || []) {
        if (String(h.symbol).trim() === symbol) holdings.push(h);
      }
    }
  }
  const primaryHolding = holdings[0];
  const name = primaryHolding?.name || symbol;
  const market = primaryHolding?.market || "A";
  const targetCur = val?.target_currency ?? displayCurrency;
  const sym = targetCur === "original" ? "¥" : currencySymbol(targetCur);

  const [refreshingQuote, setRefreshingQuote] = useState(false);

  const loadPortfolio = useCallback(async (silent = false) => {
    if (!symbol) return;
    if (!silent) setLoading(true);
    try {
      const r = await apiFetch(`${API_BASE}/api/portfolio?display_currency=${displayCurrency}`);
      const d = await r.json();
      setVal(d);
    } catch {
      setVal(null);
    } finally {
      if (!silent) setLoading(false);
    }
  }, [symbol, displayCurrency]);

  const handleRefreshQuote = useCallback(async () => {
    if (!symbol) return;
    setRefreshingQuote(true);
    try {
      const r = await apiFetch(`${API_BASE}/api/portfolio?display_currency=${displayCurrency}`);
      const d = await r.json();
      setVal(d);
    } catch {
      setVal(null);
    } finally {
      setRefreshingQuote(false);
    }
  }, [symbol, displayCurrency]);

  const loadFeed = useCallback(async () => {
    if (!symbol) return;
    setFeedLoading(true);
    try {
      const r = await apiFetch(`${API_BASE}/api/portfolio/feed?symbol=${encodeURIComponent(symbol)}&since_hours=72`);
      const d = await r.json();
      setFeedItems(d.items || []);
    } catch {
      setFeedItems([]);
    } finally {
      setFeedLoading(false);
    }
  }, [symbol]);

  const loadTimeline = useCallback(async () => {
    if (!symbol) return;
    try {
      const r = await apiFetch(`${API_BASE}/api/portfolio/timeline?symbol=${encodeURIComponent(symbol)}`);
      const d = await r.json();
      setTimelineEvents(d.events || []);
    } catch {
      setTimelineEvents([]);
    }
  }, [symbol]);

  const refreshNews = useCallback(async () => {
    if (!symbol) return;
    setFetchingNews(true);
    try {
      const r = await apiFetch(`${API_BASE}/api/portfolio/fetch-news?symbol=${encodeURIComponent(symbol)}&hours=72`, {
        method: "POST",
      });
      const d = await r.json();
      if (d.ok) {
        await loadFeed();
        const sentR = await apiFetch(`${API_BASE}/api/portfolio/sentiment?symbol=${encodeURIComponent(symbol)}`, {
          method: "POST",
        });
        const sentD = await sentR.json();
        if (sentD.ok) setSentiment({ label: sentD.label, reason: sentD.reason, score: sentD.score });
      }
    } finally {
      setFetchingNews(false);
    }
  }, [symbol, loadFeed]);

  useEffect(() => {
    loadPortfolio();
  }, [loadPortfolio]);

  useEffect(() => {
    if (!visible || !isTradingHours()) return;
    const id = setInterval(() => {
      if (!document.hidden && isTradingHours()) loadPortfolio(true);
    }, DETAIL_REFRESH_INTERVAL);
    return () => clearInterval(id);
  }, [visible, loadPortfolio]);

  useEffect(() => {
    loadFeed();
    loadTimeline();
  }, [loadFeed, loadTimeline]);

  const loadTickerHistory = useCallback(
    async (sidOverride?: string | null) => {
      if (!symbol) return;
      const url = sidOverride
        ? `${API_BASE}/api/chat/ticker-history?symbol=${encodeURIComponent(symbol)}&session_id=${encodeURIComponent(sidOverride)}`
        : `${API_BASE}/api/chat/ticker-history?symbol=${encodeURIComponent(symbol)}`;
      try {
        const r = await apiFetch(url);
        const d = await r.json();
        const msgs = d?.messages ?? [];
        const sid = d?.session_id ?? sidOverride ?? null;
        if (msgs.length > 0 || sid) {
          setTickerMessages(msgs);
          setSessionId(sid);
        } else {
          setSessionId(null);
        }
      } catch {
        setTickerMessages([]);
        setSessionId(null);
      }
    },
    [symbol]
  );

  useEffect(() => {
    if (urlSessionId) {
      loadTickerHistory(urlSessionId);
    } else {
      loadTickerHistory();
    }
  }, [loadTickerHistory, urlSessionId]);

  const saveTickerHistory = useCallback(
    async (msgs: Array<{ role: string; content: string }>, sidOverride?: string) => {
      if (!symbol || msgs.length === 0) return;
      const sid = sidOverride ?? sessionId ?? crypto.randomUUID();
      if (!sessionId && !sidOverride) setSessionId(sid);
      try {
        await apiFetch(`${API_BASE}/api/chat/ticker-history`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symbol, session_id: sid, messages: msgs }),
        });
      } catch {}
    },
    [symbol, sessionId]
  );

  const loadHistorySessions = useCallback(async () => {
    if (!symbol) return;
    setHistoryLoading(true);
    try {
      const r = await apiFetch(
        `${API_BASE}/api/chat/ticker-sessions?symbol=${encodeURIComponent(symbol)}`
      );
      const d = await r.json();
      setHistorySessions(d.sessions ?? []);
    } catch {
      setHistorySessions([]);
    } finally {
      setHistoryLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    if (historyPanelOpen && symbol) loadHistorySessions();
  }, [historyPanelOpen, symbol, loadHistorySessions]);

  const handleNewChat = useCallback(() => {
    setSessionId(crypto.randomUUID());
    setTickerMessages([]);
    setHistoryPanelOpen(false);
  }, []);

  const handleSelectSession = useCallback(
    async (sid: string) => {
      try {
        const r = await apiFetch(
          `${API_BASE}/api/chat/ticker-history?symbol=${encodeURIComponent(symbol)}&session_id=${encodeURIComponent(sid)}`
        );
        const d = await r.json();
        setTickerMessages(d.messages ?? []);
        setSessionId(sid);
        setHistoryPanelOpen(false);
      } catch {
        setHistoryPanelOpen(false);
      }
    },
    [symbol]
  );

  const formatTimeAgo = (iso: string) => {
    if (!iso) return "";
    const d = new Date(iso);
    const now = new Date();
    const diff = (now.getTime() - d.getTime()) / 1000;
    if (diff < 60) return "刚刚";
    if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
    if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`;
    return d.toLocaleDateString("zh-CN");
  };

  useEffect(() => {
    tickerScrollRef.current?.scrollTo({ top: tickerScrollRef.current.scrollHeight, behavior: "smooth" });
  }, [tickerMessages]);

  const sentimentFetched = React.useRef(false);
  useEffect(() => {
    sentimentFetched.current = false;
    setSentiment(null);
  }, [symbol]);
  useEffect(() => {
    if (feedItems.length > 0 && !sentimentFetched.current) {
      sentimentFetched.current = true;
      apiFetch(`${API_BASE}/api/portfolio/sentiment?symbol=${encodeURIComponent(symbol)}`, { method: "POST" })
        .then((r) => r.json())
        .then((d) => d.ok && setSentiment({ label: d.label, reason: d.reason, score: d.score }))
        .catch(() => setSentiment({ label: "暂无情绪" }));
    }
  }, [symbol, feedItems.length]);

  const sendTickerMessage = useCallback(
    async (text: string) => {
      const t = text.trim();
      if (!t || tickerStreaming || !symbol) return;
      setTickerInput("");
      const newUserMsg = { role: "user", content: t };
      const sid = sessionId ?? crypto.randomUUID();
      if (!sessionId) setSessionId(sid);
      const prevMsgs = [...tickerMessages, newUserMsg];
      setTickerMessages([...prevMsgs, { role: "assistant", content: "" }]);
      setTickerStreaming(true);
      let assistantContent = "";
      try {
        const r = await apiFetch(`${API_BASE}/api/chat/stream-ticker`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            symbol,
            session_id: sid,
            messages: prevMsgs,
          }),
        });
        if (!r.ok) throw new Error(`请求失败 ${r.status}`);
        const reader = r.body?.getReader();
        const decoder = new TextDecoder();
        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            for (const line of chunk.split("\n")) {
              if (line.startsWith("data: ")) {
                try {
                  const d = JSON.parse(line.slice(6));
                  if (d.type === "chunk" && d.content) {
                    assistantContent += d.content;
                    setTickerMessages((prev) => {
                      const next = [...prev];
                      const last = next[next.length - 1];
                      if (last?.role === "assistant") {
                        next[next.length - 1] = { ...last, content: assistantContent };
                      } else {
                        next.push({ role: "assistant", content: assistantContent });
                      }
                      return next;
                    });
                  } else if (d.type === "done" && d.content) {
                    assistantContent = d.content;
                    setTickerMessages((prev) => {
                      const next = [...prev];
                      const last = next[next.length - 1];
                      if (last?.role === "assistant") {
                        next[next.length - 1] = { ...last, content: assistantContent };
                      } else {
                        next.push({ role: "assistant", content: assistantContent });
                      }
                      return next;
                    });
                  }
                } catch {}
              }
            }
          }
        }
      } catch (err) {
        assistantContent = (err as Error).message;
        setTickerMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === "assistant") {
            next[next.length - 1] = { ...last, content: assistantContent };
          } else {
            next.push({ role: "assistant", content: assistantContent });
          }
          return next;
        });
      } finally {
        setTickerStreaming(false);
        const toSave = [...prevMsgs, { role: "assistant", content: assistantContent }];
        saveTickerHistory(toSave, sid);
      }
    },
    [symbol, tickerMessages, tickerStreaming, sessionId, saveTickerHistory]
  );

  if (!symbol) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-[#888]">无效的标的代码</p>
        <Link href="/" className="mt-2 inline-block text-[#1976d2] hover:underline">
          返回 Portfolio
        </Link>
      </div>
    );
  }

  if (loading && !val) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <div className="h-8 w-48 animate-pulse rounded bg-white/10" />
      </div>
    );
  }

  if (!primaryHolding) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-[#888]">未持有该标的</p>
        <Link href="/" className="mt-2 inline-block text-[#1976d2] hover:underline">
          返回 Portfolio
        </Link>
      </div>
    );
  }

  const price = primaryHolding.current_price ?? primaryHolding.cost_price ?? 0;
  const todayPct = primaryHolding.today_pct ?? 0;
  const todayUp = todayPct >= 0;
  const sentimentLabel = sentiment?.label || "暂无情绪";
  const sentimentColor =
    sentimentLabel.includes("多") || sentimentLabel.toLowerCase().includes("bullish")
      ? "text-[#00e701]"
      : sentimentLabel.includes("空") || sentimentLabel.toLowerCase().includes("bearish")
        ? "text-[#ff4e33]"
        : "text-[#888888]";

  return (
    <div className="mx-auto max-w-6xl p-6">
      {/* Header: 核心行情 */}
      <div className="mb-6 rounded-lg bg-black/80 px-6 py-4 backdrop-blur-sm">
        <div className="mb-2">
          <Link href="/" className="text-sm text-[#888] hover:text-white">
            Portfolio
          </Link>
          <span className="mx-2 text-[#666]">/</span>
          <span className="text-sm text-white">{symbol}</span>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <span className="text-2xl font-bold text-white">{symbol}</span>
          <span className="text-lg text-[#888]">
            {name} ({symbol}.{market})
          </span>
          {price > 0 && (
            <span
              className={`inline-flex items-center rounded px-2.5 py-1 text-sm font-medium ${
                todayUp ? upBadge : downBadge
              }`}
            >
              {(todayPct >= 0 ? "+" : "")}
              {todayPct.toFixed(2)}% 今日
            </span>
          )}
          <span className={`flex items-center gap-1.5 text-sm ${sentimentColor}`}>
            <span className="h-2 w-2 rounded-full bg-current" />
            {sentimentLabel}
          </span>
          <button
            onClick={handleRefreshQuote}
            disabled={refreshingQuote}
            className="rounded p-1.5 text-[#888] hover:bg-white/10 hover:text-white disabled:opacity-50"
            title="刷新行情"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          <span className="text-xs text-[#666]">
            {refreshingQuote ? "刷新中" : `Updated ${new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}`}
          </span>
        </div>
      </div>

      {/* 统一折算 */}
      <div className="mb-4 flex items-center gap-2">
        <span className="text-xs text-[#888]">统一折算</span>
        <CurrencyDropdown />
      </div>

      {/* Tabs */}
      <div className="mb-4 flex gap-2 border-b border-white/5">
        {(["overview", "sentiment", "trades"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab
                ? "border-[#1976d2] text-white"
                : "border-transparent text-[#888] hover:text-white"
            }`}
          >
            {tab === "overview" ? "概览" : tab === "sentiment" ? "情绪" : "持仓变动"}
          </button>
        ))}
      </div>

      {activeTab === "overview" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {/* 左栏：资产看板 */}
          <div className="space-y-4">
            <div className="rounded-lg bg-[#1A1A1A] p-4">
              <div className="text-2xl font-bold text-white">
                {sym}
                {price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
              </div>
              <div
                className={`text-sm font-semibold ${
                  todayUp ? upColor : downColor
                }`}
              >
                {(todayPct >= 0 ? "+" : "")}
                {todayPct.toFixed(2)}%
              </div>
            </div>
            <div className="rounded-lg bg-[#1A1A1A] p-4">
              <div className="mb-3 text-xs font-medium uppercase tracking-wider text-[#888]">持仓明细</div>
              <table className="w-full text-sm">
                <tbody>
                  {[
                    ["代码", symbol],
                    ["名称", name],
                    ["市场", market],
                    ["成本价", primaryHolding.cost_price ? `${primaryHolding.cost_price}` : "—"],
                    ["持仓量", String(primaryHolding.quantity ?? "—")],
                    ["账户", primaryHolding.account ?? "默认"],
                    ["来源", primaryHolding.source ?? "—"],
                  ].map(([k, v]) => (
                    <tr key={k} className="border-b border-white/5">
                      <td className="py-1.5 text-[#888]">{k}</td>
                      <td className="py-1.5 text-right text-white">{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {holdings.length > 1 && (
                <div className="mt-3 text-xs text-[#666]">
                  该标的在 {holdings.length} 个账户中有持仓
                </div>
              )}
            </div>
          </div>

          {/* 中栏：新闻 FEED */}
          <div className="space-y-4">
            <div className="rounded-lg bg-[#1A1A1A] p-4">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider text-[#888]">新闻 FEED</span>
                <button
                  onClick={refreshNews}
                  disabled={fetchingNews}
                  className="rounded bg-[#1976d2] px-3 py-1.5 text-xs text-white hover:bg-[#1565c0] disabled:opacity-50"
                >
                  {fetchingNews ? "刷新中..." : "刷新数据"}
                </button>
              </div>
              {feedLoading ? (
                <div className="py-8 text-center text-sm text-[#666]">加载中...</div>
              ) : feedItems.length === 0 ? (
                <p className="py-6 text-center text-sm text-[#666]">
                  暂无新闻。点击「刷新数据」抓取。
                </p>
              ) : (
                <div className="space-y-3">
                  {feedItems.slice(0, 15).map((it) => (
                    <div key={it.id} className="border-b border-white/5 pb-3 last:border-0">
                      <a
                        href={it.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-medium text-white hover:text-[#1976d2]"
                      >
                        {it.title}
                      </a>
                      <div className="mt-1 text-xs text-[#666]">
                        {it.source_id || it.source} · {it.published_at?.slice(0, 16) || "—"}
                      </div>
                      {it.content_snippet && (
                        <div className="mt-1 line-clamp-2 text-xs text-[#888]">{it.content_snippet}</div>
                      )}
                      <div className="mt-1">
                        <a
                          href={it.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-[#1976d2] hover:underline"
                        >
                          深挖
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 右栏：Ask PFA Live — 风格对齐首页，会话管理 */}
          <div className="rounded-lg bg-[#1A1A1A] p-4 flex flex-col">
            <div className="mb-2 flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-white">Ask PFA Live</span>
                <span className="rounded bg-[#00e701]/20 px-1.5 py-0.5 text-xs text-[#00e701]">Live</span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={handleNewChat}
                  className="rounded p-1.5 text-[#888] hover:bg-white/10 hover:text-white"
                  title="新建对话"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </button>
                <button
                  onClick={() => setHistoryPanelOpen(true)}
                  className="rounded p-1.5 text-[#888] hover:bg-white/10 hover:text-white"
                  title="历史记录"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </button>
              </div>
            </div>
            <p className="mb-3 text-xs text-[#888]">基于 {name} 最新新闻，向 AI 提问</p>
            <div
              ref={tickerScrollRef}
              className="mb-4 h-[320px] overflow-y-auto space-y-4 scroll-smooth"
            >
              {tickerMessages.length === 0 && !tickerStreaming && (
                <div className="py-4">
                  <div className="mb-3 text-xs font-medium text-[#666]">猜你想问</div>
                  <div className="flex flex-wrap gap-2">
                    {[
                      `${name} 的未来 3 年增长逻辑`,
                      sentiment?.label === "偏多" ? `${name} 有哪些利好因素` : null,
                      sentiment?.label === "偏空" ? `${name} 主要风险有哪些` : null,
                      feedItems.length > 0
                        ? `解读：${feedItems[0]?.title?.slice(0, 20) || ""}...`
                        : null,
                    ]
                      .filter(Boolean)
                      .slice(0, 4)
                      .map((prompt) => (
                        <button
                          key={prompt as string}
                          type="button"
                          onClick={() => sendTickerMessage(prompt as string)}
                          disabled={tickerStreaming}
                          className="rounded-lg border border-[#1976d2]/30 bg-[#1976d2]/10 px-3 py-1.5 text-xs font-medium text-[#b1bad3] transition-colors hover:border-[#1976d2]/50 hover:bg-[#1976d2]/20 hover:text-white disabled:opacity-50"
                        >
                          {prompt}
                        </button>
                      ))}
                  </div>
                </div>
              )}
              {tickerMessages.map((m, i) => (
                <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
                  <ChatMessage
                    content={m.content}
                    role={m.role as "user" | "assistant"}
                    isStreaming={tickerStreaming && m.role === "assistant" && i === tickerMessages.length - 1}
                  />
                </div>
              ))}
            </div>
            <div className="mt-auto space-y-3">
              <div className="flex flex-wrap gap-2">
                {[
                  { label: "分析个股", prompt: `分析 ${name} 的估值与成长性` },
                  { label: "扫描风险", prompt: `${name} 近期有哪些风险点` },
                ].map(({ label, prompt }) => (
                  <button
                    key={label}
                    type="button"
                    onClick={() => sendTickerMessage(prompt)}
                    disabled={tickerStreaming}
                    className="rounded-lg border border-[#1976d2]/30 bg-[#1976d2]/10 px-3 py-1.5 text-xs font-medium text-[#b1bad3] transition-colors hover:border-[#1976d2]/50 hover:bg-[#1976d2]/20 hover:text-white disabled:opacity-50"
                  >
                    {label}
                  </button>
                ))}
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  sendTickerMessage(tickerInput);
                }}
                className="flex gap-2 rounded-full border border-white/10 bg-[#0a0a0a] px-4 py-3"
              >
                <input
                  type="text"
                  value={tickerInput}
                  onChange={(e) => setTickerInput(e.target.value)}
                  placeholder={`例如：${name} 的未来 3 年增长逻辑？`}
                  disabled={tickerStreaming}
                  className="flex-1 bg-transparent text-sm text-white placeholder:text-[#888] outline-none disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={tickerStreaming || !tickerInput.trim()}
                  className="rounded-full bg-[#00e701] px-4 py-1.5 text-sm font-medium text-black disabled:opacity-50"
                >
                  发送
                </button>
              </form>
            </div>
          </div>

          {/* 历史记录侧边栏 */}
          {historyPanelOpen && (
            <>
              <div
                className="fixed inset-0 z-40 bg-black/50"
                onClick={() => setHistoryPanelOpen(false)}
                aria-hidden="true"
              />
              <div className="fixed right-0 top-0 z-50 flex h-full w-full max-w-[280px] sm:w-[280px] flex-col border-l border-white/10 bg-[#0a0a0a] shadow-2xl">
                <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
                  <span className="text-sm font-medium text-white">历史记录</span>
                  <button
                    onClick={() => setHistoryPanelOpen(false)}
                    className="rounded p-1.5 text-[#888] hover:bg-white/10 hover:text-white"
                  >
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto p-3">
                  {historyLoading ? (
                    <div className="py-8 text-center text-sm text-[#666]">加载中...</div>
                  ) : historySessions.length === 0 ? (
                    <div className="py-8 text-center text-sm text-[#666]">暂无历史对话</div>
                  ) : (
                    <div className="space-y-2">
                      {historySessions.map((s) => (
                        <button
                          key={s.session_id}
                          onClick={() => handleSelectSession(s.session_id)}
                          className="w-full rounded-lg border border-white/5 bg-black/30 px-3 py-2 text-left text-sm transition-colors hover:border-[#1976d2]/30 hover:bg-[#1976d2]/10"
                        >
                          <div className="truncate text-white">
                            {s.first_question || "新对话"}
                          </div>
                          <div className="mt-1 text-xs text-[#666]">
                            {formatTimeAgo(s.updated_at)}
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {activeTab === "sentiment" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-lg bg-[#1A1A1A] p-4">
            <div className="mb-2 text-xs font-medium uppercase tracking-wider text-[#888]">Overall Sentiment</div>
            <div className={`text-2xl font-bold ${sentimentColor}`}>{sentiment?.label ?? "—"}</div>
            {sentiment?.score != null && (
              <div className="mt-1 text-sm text-[#888]">Score: {sentiment.score}</div>
            )}
            <div className="mt-1 text-sm text-[#666]">{sentiment?.reason ?? "暂无情绪数据"}</div>
          </div>
          <div className="rounded-lg bg-[#1A1A1A] p-4">
            <div className="mb-2 text-xs font-medium uppercase tracking-wider text-[#888]">7-Day Trend</div>
            <div className="text-sm text-[#666]">暂无</div>
          </div>
          <div className="rounded-lg bg-[#1A1A1A] p-4">
            <div className="mb-2 text-xs font-medium uppercase tracking-wider text-[#888]">Sentiment by Source</div>
            <div className="text-sm text-[#666]">暂无</div>
          </div>
          <div className="rounded-lg bg-[#1A1A1A] p-4">
            <div className="mb-2 text-xs font-medium uppercase tracking-wider text-[#888]">Sentiment Alerts</div>
            <div className="flex items-center gap-2 text-sm text-[#666]">
              <span className="h-2 w-2 rounded-full bg-[#888]" />
              暂无预警
            </div>
          </div>
        </div>
      )}

      {activeTab === "trades" && (
        <div className="rounded-lg bg-[#1A1A1A] p-4">
          <div className="mb-3 text-xs font-medium uppercase tracking-wider text-[#888]">持仓变动</div>
          {timelineEvents.filter((e) => e.event_type === "TRADE").length === 0 ? (
            <p className="py-8 text-center text-sm text-[#666]">暂无持仓变动记录</p>
          ) : (
            <div className="space-y-2">
              {timelineEvents
                .filter((e) => e.event_type === "TRADE")
                .map((e) => (
                  <div key={e.id} className="rounded border border-white/5 px-3 py-2 text-sm">
                    <div className="text-[#888]">{e.timestamp?.slice(0, 19)}</div>
                    <div className="text-white">{e.content}</div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
