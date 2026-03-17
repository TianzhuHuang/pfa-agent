"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { EntryModal } from "@/components/EntryModal";
import { OnboardingView } from "@/components/OnboardingView";
import { EditAccountsModal } from "@/components/EditAccountsModal";
import { EditHoldingModal } from "@/components/EditHoldingModal";
import { PortfolioCharts } from "@/components/PortfolioCharts";
import { ChatMessage } from "@/components/ChatMessage";
import { TradeConfirmCard, type TradePayload } from "@/components/TradeConfirmCard";
import { apiFetch, API_BASE } from "@/lib/api";
import { useDisplayCurrency, currencySymbol } from "@/contexts/DisplayCurrencyContext";
import { useColorScheme } from "@/contexts/ColorSchemeContext";
import { CurrencyDropdown } from "@/components/CurrencyDropdown";
import { AccountCurrencyDropdown } from "@/components/AccountCurrencyDropdown";
import { LoadingOverlay } from "@/components/LoadingOverlay";
import { usePageVisibility } from "@/hooks/usePageVisibility";
import { isTradingHours } from "@/lib/tradingHours";
import { PORTFOLIO_REFRESH_INTERVAL } from "@/lib/refreshConstants";

interface HoldingRow {
  symbol?: string;
  name?: string;
  is_cash?: boolean;
  current_price?: number | null;
  price_loaded?: boolean;
  cost_price?: number;
  quantity?: number;
  value_cny?: number | null;
  value_local?: number | null;
  value_display?: number | null;
  currency_error?: boolean;
  currency?: string;
  pnl_cny?: number | null;
  pnl_pct?: number | null;
  today_pct?: number | null;
  today_pnl?: number | null;
  position_pct?: number;
  account?: string;
  exchange?: string;
  source?: string;
  ocr_confirmed?: boolean;
  price_deviation_warn?: boolean;
}

interface PortfolioVal {
  total_value_cny?: number;
  total_pnl_cny?: number;
  total_pnl_pct?: number;
  holding_count?: number;
  account_count?: number;
  target_currency?: string;
  fx_updated_at?: string | null;
  fx_rates?: Record<string, number>;
  by_account?: Record<string, { holdings: HoldingRow[]; value?: number; value_cny?: number }>;
}

export default function DashboardPage() {
  const [val, setVal] = useState<PortfolioVal | null>(null);
  const [loading, setLoading] = useState(true);
  const [entryOpen, setEntryOpen] = useState(false);
  const [entryOpenTab, setEntryOpenTab] = useState<"search" | "ocr" | "file">("search");
  const [editAccountsOpen, setEditAccountsOpen] = useState(false);
  const [clearConfirmOpen, setClearConfirmOpen] = useState(false);
  const [chartAccountFilter, setChartAccountFilter] = useState<string | null>("all");
  const [chartPnlMode, setChartPnlMode] = useState<"today" | "cumulative">("today");
  const [messages, setMessages] = useState<Array<{ role: string; content: string; type?: string; payload?: TradePayload }>>([]);
  const [dismissedConfirmIds, setDismissedConfirmIds] = useState<Set<number>>(new Set());
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  // 首次访问默认展开 Ask PFA，后续记住用户偏好
  const [chatDrawerOpen, setChatDrawerOpen] = useState(() => {
    if (typeof window === "undefined") return false;
    const saved = localStorage.getItem("pfa_chat_drawer_closed");
    return saved !== "true"; // 首次访问或未关闭过则默认展开
  });
  const [priceLoadTimedOut, setPriceLoadTimedOut] = useState(false);
  const { displayCurrency } = useDisplayCurrency();
  const { upColor, downColor, upBadge, downBadge } = useColorScheme();
  const [accountCurrencyOverrides, setAccountCurrencyOverrides] = useState<Record<string, "CNY" | "USD" | "HKD">>({});
  const [editHolding, setEditHolding] = useState<HoldingRow | null>(null);
  const [historyPanelOpen, setHistoryPanelOpen] = useState(false);
  const [historySessions, setHistorySessions] = useState<Array<{ type: string; symbol?: string; symbol_name?: string; session_id: string; first_question: string; updated_at: string }>>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [countdown, setCountdown] = useState(Math.floor(PORTFOLIO_REFRESH_INTERVAL / 1000));
  const [flashType, setFlashType] = useState<"up" | "down" | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshProgress, setRefreshProgress] = useState(0);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [firstEntryBannerDismissed, setFirstEntryBannerDismissed] = useState(
    () => typeof window !== "undefined" && localStorage.getItem("pfa_first_entry_done") === "1"
  );
  const prevTotalRef = useRef<number | null>(null);
  const countdownResetRef = useRef<() => void>(() => {});
  const router = useRouter();
  const visible = usePageVisibility();

  const loadHistorySessions = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const r = await apiFetch(`${API_BASE}/api/chat/all-sessions`);
      const d = await r.json();
      setHistorySessions(d.sessions ?? []);
    } catch {
      setHistorySessions([]);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const handleNewChat = useCallback(() => {
    setMessages([]);
    setDismissedConfirmIds(new Set());
    setHistoryPanelOpen(false);
  }, []);

  const handleSelectHistorySession = useCallback(
    async (s: { type: string; symbol?: string; session_id: string }) => {
      if (s.type === "ticker" && s.symbol) {
        setHistoryPanelOpen(false);
        router.push(`/portfolio/${encodeURIComponent(s.symbol)}?session_id=${encodeURIComponent(s.session_id)}`);
        return;
      }
      if (s.type === "global") {
        try {
          const r = await apiFetch(`${API_BASE}/api/chat/history`);
          const d = await r.json();
          const msgs = (d?.messages ?? []).map((m: { role?: string; content?: string }) => ({
            role: m.role || "assistant",
            content: m.content || "",
          }));
          setMessages(msgs);
          setHistoryPanelOpen(false);
        } catch {
          setHistoryPanelOpen(false);
        }
      }
    },
    [router]
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

  const handleSendMessage = useCallback(
    async (text: string) => {
      const t = text.trim();
      if (!t || streaming) return;
      setInput("");
      const newUserMsg = { role: "user" as const, content: t };
      setMessages((prev) => [...prev, newUserMsg, { role: "assistant", content: "" }]);
      setStreaming(true);
      let assistantContent = "";
      let lastAssistantMsg: { role: "assistant"; content: string; type?: string; payload?: TradePayload } = {
        role: "assistant",
        content: "",
      };
      try {
        // 仅传 role/content，后端不接受 type、payload 等扩展字段
        const toSend = [...messages, newUserMsg].map((m) => ({ role: m.role, content: m.content || "" }));
        const r = await apiFetch(`${API_BASE}/api/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ messages: toSend }),
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
                    setMessages((prev) => {
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
                    setMessages((prev) => {
                      const next = [...prev];
                      const last = next[next.length - 1];
                      if (last?.role === "assistant") {
                        next[next.length - 1] = { ...last, content: assistantContent };
                      } else {
                        next.push({ role: "assistant", content: assistantContent });
                      }
                      return next;
                    });
                  } else if (d.type === "confirm" && d.payload) {
                    assistantContent = d.message || "请填写或修改以下信息后点击「确认写入」。";
                    const payload = d.payload as TradePayload;
                    lastAssistantMsg = { role: "assistant", content: assistantContent, type: "confirm", payload };
                    setMessages((prev) => {
                      const next = [...prev];
                      const last = next[next.length - 1];
                      if (last?.role === "assistant" && !last.content) {
                        next[next.length - 1] = lastAssistantMsg;
                      } else {
                        next.push(lastAssistantMsg);
                      }
                      return next;
                    });
                    break;
                  }
                } catch {}
              }
            }
          }
        }
      } catch (err) {
        const msg = (err as Error).message;
        const hint =
          msg.includes("fetch") || msg.includes("Failed")
            ? "无法连接后端，请确认已启动: uvicorn backend.main:app --port 8000"
            : msg;
        assistantContent = `错误: ${hint}`;
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === "assistant" && !last.content) {
            next[next.length - 1] = { role: "assistant", content: assistantContent };
          } else {
            next.push({ role: "assistant", content: assistantContent });
          }
          return next;
        });
      } finally {
        setStreaming(false);
        const finalContent =
          lastAssistantMsg.type ? lastAssistantMsg.content : (assistantContent || "暂无回复，请稍后重试或检查网络。");
        const finalMsg = lastAssistantMsg.type
          ? lastAssistantMsg
          : { role: "assistant" as const, content: finalContent };
        if (!assistantContent && !lastAssistantMsg.type) {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant") next[next.length - 1] = { ...last, content: finalContent };
            return next;
          });
        }
        const toSave = [...messages, newUserMsg, finalMsg];
        apiFetch(`${API_BASE}/api/chat/history`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ messages: toSave }),
        })
          .then((r) => {
            if (!r.ok) {
              try {
                localStorage.setItem("pfa_chat_fallback", JSON.stringify(toSave));
              } catch {}
            }
          })
          .catch(() => {});
      }
    },
    [messages, streaming]
  );

  const refreshPortfolio = useCallback(
    (options?: { silent?: boolean; resetTimer?: boolean }) => {
      const { silent = false, resetTimer = true } = options ?? {};
      if (!silent) {
        setRefreshing(true);
        setRefreshError(null);
      }
      const prevTotal = prevTotalRef.current;
      apiFetch(`${API_BASE}/api/portfolio?display_currency=${displayCurrency}`)
        .then(async (r) => {
          const d = await r.json().catch(() => ({}));
          if (!r.ok) throw new Error((d as { error?: string })?.error || `HTTP ${r.status}`);
          return d;
        })
        .then((d) => {
          const nextTotal = d?.total_value_cny ?? null;
          if (prevTotal != null && nextTotal != null && prevTotal !== nextTotal) {
            setFlashType(nextTotal >= prevTotal ? "up" : "down");
          }
          prevTotalRef.current = nextTotal;
          setVal(d);
          setRefreshError(null);
          if (resetTimer) countdownResetRef.current();
        })
        .catch((err) => {
          // 不清空数据，保留上次成功的结果
          console.error("Portfolio refresh failed:", err);
          if (!silent) {
            setRefreshError(err.message || "刷新失败");
          }
        })
        .finally(() => {
          if (!silent) setRefreshing(false);
        });
    },
    [displayCurrency]
  );

  const handleManualRefresh = useCallback(() => {
    refreshPortfolio({ silent: false, resetTimer: true });
  }, [refreshPortfolio]);

  useEffect(() => {
    apiFetch(`${API_BASE}/api/portfolio?display_currency=${displayCurrency}`)
      .then(async (r) => {
        const d = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error((d as { error?: string })?.error || `HTTP ${r.status}`);
        return d;
      })
      .then((d) => {
        setVal(d);
        setRefreshError(null);
        prevTotalRef.current = d?.total_value_cny ?? null;
        countdownResetRef.current?.();
      })
      .catch(() => {
        setVal(null);
        setRefreshError("数据加载失败，请刷新重试");
      })
      .finally(() => setLoading(false));
  }, [displayCurrency]);

  useEffect(() => {
    if (!visible || !isTradingHours()) return;
    const intervalSec = Math.floor(PORTFOLIO_REFRESH_INTERVAL / 1000);
    let remaining = intervalSec;
    setCountdown(remaining);
    countdownResetRef.current = () => {
      remaining = intervalSec;
      setCountdown(remaining);
    };
    const tick = () => {
      if (!document.hidden && isTradingHours()) {
        remaining -= 1;
        setCountdown(Math.max(0, remaining));
        if (remaining <= 0) {
          remaining = intervalSec;
          refreshPortfolio({ silent: true, resetTimer: false });
        }
      }
    };
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [visible, refreshPortfolio]);

  useEffect(() => {
    if (flashType == null) return;
    const t = setTimeout(() => setFlashType(null), 400);
    return () => clearTimeout(t);
  }, [flashType]);

  useEffect(() => {
    apiFetch(`${API_BASE}/api/chat/history`)
      .then((r) => {
        if (!r.ok) {
          try {
            const fallback = localStorage.getItem("pfa_chat_fallback");
            if (fallback) {
              const msgs = JSON.parse(fallback);
              if (Array.isArray(msgs) && msgs.length > 0) {
                setMessages(msgs.map((m: { role?: string; content?: string }) => ({
                  role: m.role || "assistant",
                  content: m.content || "",
                })));
              }
            }
          } catch {}
          return null;
        }
        return r.json();
      })
      .then((d) => {
        if (!d) return;
        const msgs = d?.messages;
        if (Array.isArray(msgs) && msgs.length > 0) {
          setMessages(msgs.map((m: { role?: string; content?: string }) => ({
            role: m.role || "assistant",
            content: m.content || "",
          })));
        }
      })
      .catch(() => {});
  }, []);

  // 价格加载超时：5秒后标记为超时
  useEffect(() => {
    if (!loading && val) {
      const hasUnloadedPrices = Object.values(val.by_account ?? {}).some((acc) =>
        (acc.holdings ?? []).some((h: HoldingRow) => h.price_loaded === false)
      );
      if (hasUnloadedPrices) {
        const timer = setTimeout(() => setPriceLoadTimedOut(true), 5000);
        return () => clearTimeout(timer);
      }
    }
    setPriceLoadTimedOut(false);
  }, [loading, val]);

  // 保存抽屉状态偏好
  const handleCloseChatDrawer = useCallback(() => {
    setChatDrawerOpen(false);
    localStorage.setItem("pfa_chat_drawer_closed", "true");
  }, []);

  const totalV = val?.total_value_cny ?? 0;
  const totalPnl = val?.total_pnl_cny ?? 0;
  const totalPct = val?.total_pnl_pct ?? 0;
  const pnlColor = totalPnl >= 0 ? upColor : downColor;
  const sign = totalPnl >= 0 ? "+" : "";
  const targetCur = val?.target_currency ?? displayCurrency;
  const sym = targetCur === "original" ? "¥" : currencySymbol(targetCur);
  const isConverted = targetCur !== "original" && targetCur !== "CNY";
  const fxAt = val?.fx_updated_at;
  const fxRate = val?.fx_rates?.["USD"] ?? 0;
  const fxRates = val?.fx_rates ?? { CNY: 1, USD: 7.25, HKD: 0.92 };

  const convertValue = (v: number, from: string, to: string) => {
    if (from === to) return v;
    const rFrom = Number(fxRates[from as keyof typeof fxRates] ?? 1);
    const rTo = Number(fxRates[to as keyof typeof fxRates] ?? 1);
    if (!rTo || rTo <= 0) return v;
    return v * (rFrom / rTo);
  };
  const fxHint = targetCur === "CNY" && fxRate > 0
    ? `1 USD = ${fxRate.toFixed(2)} CNY`
    : targetCur === "USD" && val?.fx_rates?.["CNY"]
    ? `1 CNY = ${(1 / (val.fx_rates!.USD || 1)).toFixed(4)} USD`
    : null;

  return (
    <div className="flex h-[calc(100vh-48px)]">
      {/* Left: Dashboard */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden p-6">
        <div className="mx-auto max-w-6xl">
          {loading ? (
            <LoadingOverlay fullScreen />
          ) : totalV === 0 ? (
            <OnboardingView
              onOpenEntry={(tab) => {
                setEntryOpenTab(tab);
                setEntryOpen(true);
              }}
            />
          ) : (
            <>
          {/* 首笔录入后 AI 洞察引导 */}
          {!firstEntryBannerDismissed && val?.holding_count === 1 && (
            (() => {
              const firstHolding = Object.values(val.by_account ?? {}).flatMap((a) => a.holdings ?? [])[0];
              const firstSymbol = firstHolding?.symbol;
              const firstName = firstHolding?.name ?? firstSymbol ?? "标的";
              const dismiss = () => {
                setFirstEntryBannerDismissed(true);
                localStorage.setItem("pfa_first_entry_done", "1");
              };
              return (
                <div className="mb-6 flex items-center justify-between gap-4 rounded-lg border border-[#22c55e]/30 bg-[#22c55e]/5 px-4 py-3">
                  <div>
                    <span className="text-sm font-medium text-[#22c55e]">已为 {firstName} 完成首次风险扫描</span>
                    <p className="mt-0.5 text-xs text-[#888]">AI 已准备好为你分析持仓，试试 Ask PFA 吧</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {firstSymbol && (
                      <Link
                        href={`/portfolio/${encodeURIComponent(firstSymbol)}`}
                        onClick={dismiss}
                        className="rounded bg-[#22c55e] px-3 py-1.5 text-xs font-medium text-black hover:opacity-90"
                      >
                        查看详情
                      </Link>
                    )}
                    <button
                      type="button"
                      onClick={() => { dismiss(); setEntryOpen(true); }}
                      className="rounded border border-[#22c55e]/50 px-3 py-1.5 text-xs font-medium text-[#22c55e] hover:bg-[#22c55e]/10"
                    >
                      继续添加持仓
                    </button>
                    <button
                      type="button"
                      onClick={dismiss}
                      className="rounded p-1.5 text-[#888] hover:bg-white/10 hover:text-white"
                      aria-label="关闭"
                    >
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
              );
            })()
          )}

          {/* HeaderStats: 两列玻璃仪表盘 */}
          <div className="mb-6 flex flex-col gap-4 sm:flex-row">
            {/* 左侧：资产看板 */}
            <div className="flex-1 min-w-0 rounded-lg border border-[#222] bg-gradient-to-br from-[#0a0a0a] to-[#111] px-5 py-4">
              <span className="text-xs text-[#888888]">Total Wealth</span>
              {loading ? (
                <div className="mt-2 h-9 w-32 animate-pulse rounded bg-white/10" />
              ) : (
                <div className="mt-2 flex items-baseline gap-2">
                  <span className={`text-2xl font-bold tabular-nums ${isConverted ? "opacity-90" : ""} ${flashType === "up" ? "pfa-flash-up" : flashType === "down" ? "pfa-flash-down" : ""}`}>
                    {sym}{totalV.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                  <CurrencyDropdown compact />
                </div>
              )}
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-sm">
                {!loading && (
                  <span className={pnlColor}>
                    {sign}{sym}{totalPnl.toLocaleString()} ({sign}{totalPct.toFixed(2)}%)
                  </span>
                )}
                {!loading && fxHint && (
                  <span className="text-xs text-[#555]">{fxHint}</span>
                )}
              </div>
              {!loading && (
                <div className="mt-3 flex items-center gap-2">
                  {refreshError ? (
                    <>
                      <div className="flex-1" />
                      <span className="shrink-0 text-[10px] text-red-400" title={refreshError}>{refreshError}</span>
                    </>
                  ) : refreshing ? (
                    <>
                      <div className="flex-1 h-0.5 overflow-hidden rounded-full bg-white/5">
                        <div className="h-full rounded-full bg-[#1976d2]/60 animate-pulse" style={{ width: "100%" }} />
                      </div>
                      <span className="shrink-0 text-[10px] text-[#1976d2] tabular-nums">刷新中...</span>
                    </>
                  ) : visible && isTradingHours() ? (
                    <>
                      <div className="flex-1 h-0.5 overflow-hidden rounded-full bg-white/5">
                        <div
                          className="h-full rounded-full bg-[#1976d2]/40 transition-all duration-1000 ease-linear"
                          style={{ width: `${(countdown / Math.floor(PORTFOLIO_REFRESH_INTERVAL / 1000)) * 100}%` }}
                        />
                      </div>
                      <span className="shrink-0 text-[10px] text-[#555] tabular-nums">{countdown}s 后同步</span>
                    </>
                  ) : (
                    <>
                      <div className="flex-1" />
                      <span className="shrink-0 text-[10px] text-[#555]">非交易时段</span>
                    </>
                  )}
                  <button
                    onClick={handleManualRefresh}
                    disabled={refreshing}
                    className="shrink-0 rounded p-1.5 text-[#888] hover:bg-white/10 hover:text-white disabled:opacity-60 transition-colors"
                    title="刷新持仓数据"
                  >
                    <svg className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                </div>
              )}
            </div>

            {/* 右侧：资产管理（统计 + 操作） */}
            <div className="flex min-w-[180px] flex-1 flex-col rounded-lg border border-[#222] bg-gradient-to-br from-[#0a0a0a] to-[#111] overflow-hidden">
              <div className="border-b border-white/5 px-4 py-2.5">
                <span className="text-xs text-[#888888]">资产管理</span>
              </div>
              <div className="flex flex-1 flex-col items-center justify-center px-4 py-3">
                {loading ? (
                  <div className="h-8 w-24 animate-pulse rounded bg-white/10" />
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-semibold text-white tabular-nums">
                      {val?.holding_count ?? 0} 持仓 · {val?.account_count ?? 0} 账户
                    </span>
                    <button
                      onClick={() => setEditAccountsOpen(true)}
                      className="rounded p-1.5 text-[#1976d2] hover:bg-white/10 hover:text-white transition-colors"
                      title="编辑账户"
                    >
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                    </button>
                  </div>
                )}
              </div>
              <div className="flex border-t border-white/5">
                <button
                  onClick={() => setEntryOpen(true)}
                  className="flex-1 py-2.5 text-sm font-medium text-black transition-colors hover:opacity-90"
                  style={{ backgroundColor: "#22C55E" }}
                >
                  录入持仓
                </button>
                <button
                  onClick={() => setClearConfirmOpen(true)}
                  disabled={(val?.holding_count ?? 0) === 0}
                  className="flex-1 border-l border-[#EF4444]/50 py-2.5 text-sm font-medium text-[#EF4444] transition-colors hover:bg-[#EF4444]/10 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent"
                >
                  清空持仓
                </button>
              </div>
            </div>
          </div>

          {/* 第二层：可视化图表区（仓位 + 盈亏） */}
          <div className="mb-10 sm:mb-6 w-full min-w-0 shrink-0">
            <PortfolioCharts
              key={displayCurrency}
              byAccount={val?.by_account ?? {}}
              totalValue={totalV}
              targetCurrency={targetCur}
              loading={loading}
              selectedAccount={chartAccountFilter}
              pnlMode={chartPnlMode}
              onAccountChange={setChartAccountFilter}
              onPnlModeChange={setChartPnlMode}
            />
          </div>

          {/* 第三层：持仓明细表格 */}
          <div className="relative z-10 rounded-lg bg-[#0a0a0a] overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/5 px-4 py-3">
              <span className="text-sm font-medium text-[#888888]">持仓明细</span>
            </div>
            {loading ? (
              <div className="flex min-h-[200px] items-center justify-center">
                <LoadingOverlay fullScreen={false} />
              </div>
            ) : !val?.by_account || Object.keys(val.by_account).length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-4 p-12 text-center">
                <div className="text-4xl">📊</div>
                <div className="text-base font-medium">暂无持仓数据</div>
                <div className="text-sm text-[#888888]">
                  点击「录入持仓」或通过右侧 AI 对话添加持仓
                </div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
                  <thead>
                    <tr className="border-b border-white/5 bg-black/30">
                      <th className="px-3 py-2.5 text-left font-medium text-[#888888]">账户</th>
                      <th className="px-3 py-2.5 text-right font-medium text-[#888888]">现价 (原始)</th>
                      <th className="px-3 py-2.5 text-center font-medium text-[#888888]">今日</th>
                      <th className="px-3 py-2.5 text-right font-medium text-[#888888]">成本</th>
                      <th className="px-3 py-2.5 text-right font-medium text-[#888888]">数量</th>
                      <th className="px-3 py-2.5 text-right font-medium text-[#888888]">
                        市值{targetCur === "original" ? " (原币)" : ` (${targetCur})`}
                      </th>
                      <th className="px-3 py-2.5 text-right font-medium text-[#888888]">仓位</th>
                      <th className="px-3 py-2.5 text-center font-medium text-[#888888]">累计盈亏</th>
                      <th className="px-3 py-2.5 text-center font-medium text-[#888888]">收益率</th>
                      <th className="px-3 py-2.5 w-10"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(val.by_account).map(([acct, data], acctIdx) => {
                      const acctValRaw = data.value ?? data.value_cny ?? 0;
                      const holdings = (data.holdings ?? []) as HoldingRow[];
                      const accountCur = (accountCurrencyOverrides[acct] ?? (displayCurrency === "original" ? "CNY" : displayCurrency)) as "CNY" | "USD" | "HKD";
                      const srcCur = targetCur === "original" ? "CNY" : targetCur;
                      const acctVal = accountCur === srcCur ? acctValRaw : convertValue(acctValRaw, srcCur, accountCur);
                      const acctSym = currencySymbol(accountCur);
                      return (
                        <React.Fragment key={acct}>
                          <tr className="border-b border-white/5 bg-[#161616]" style={acctIdx > 0 ? { borderTop: "1px solid rgba(255,255,255,0.08)" } : undefined}>
                            <td colSpan={5} className={`px-3 py-2.5 ${acctIdx > 0 ? "pt-6" : ""}`}>
                              <div className="flex items-center gap-2 min-w-0">
                                <svg className="h-4 w-4 text-[#888888] shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                                </svg>
                                <span className="font-bold text-white truncate">{acct}</span>
                              </div>
                            </td>
                            <td colSpan={1} className={`px-3 py-2.5 text-right ${acctIdx > 0 ? "pt-6" : ""}`}>
                              <div className="flex items-center justify-end gap-1.5">
                                <AccountCurrencyDropdown
                                  accountId={acct}
                                  value={accountCur}
                                  onChange={(c) => setAccountCurrencyOverrides((prev) => ({ ...prev, [acct]: c }))}
                                />
                                <span className="text-white/90 tabular-nums">{acctSym}{acctVal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                              </div>
                            </td>
                            <td colSpan={4} className={`px-3 py-2.5 ${acctIdx > 0 ? "pt-6" : ""}`} />
                          </tr>
                          {holdings.map((h, i) => {
                            const pnlRaw = h.pnl_cny ?? 0;
                            const pnlSrcCur = targetCur === "original" ? "CNY" : targetCur;
                            const pnl = accountCur === pnlSrcCur ? pnlRaw : convertValue(pnlRaw, pnlSrcCur, accountCur);
                            const pct = h.pnl_pct; // 保留 null，UI 根据 null 显示 "—"
                            const todayPct = h.today_pct; // 保留 null，UI 根据 null 显示 "—"
                            const posPct = h.position_pct ?? 0;
                            const isUp = pnl >= 0;
                            const todayUp = (todayPct ?? 0) >= 0;
                            const origCur = h.currency ?? "CNY";
                            const priceSym = currencySymbol(origCur);
                            const rowSrcCur = targetCur === "original" ? origCur : targetCur;
                            const rowValRaw = targetCur === "original" ? (h.value_local ?? h.value_cny ?? 0) : (h.value_display ?? h.value_cny ?? 0);
                            const rowVal = accountCur === rowSrcCur ? rowValRaw : convertValue(rowValRaw, rowSrcCur, accountCur);
                            const rowSym = currencySymbol(accountCur);
                            const isConvertedRow = accountCur !== "CNY";
                            const currencyErr = h.currency_error === true;
                            // 价格未加载时市值显示 --，禁止用成本价占位
                            const marketValDisplay = currencyErr ? null : (h.price_loaded === false ? null : rowVal);
                            return (
                              <tr
                                key={`${h.symbol}-${h.account}-${i}`}
                                className="border-b border-white/5 bg-[#0d0d0d] hover:bg-white/[0.03]"
                              >
                                <td className="px-3 py-2">
                                  {h.is_cash ? (
                                    <span className="text-[#888888]">{h.name ?? "💰 现金余额"}</span>
                                  ) : (
                                    <>
                                      <Link
                                        href={`/portfolio/${encodeURIComponent(h.symbol ?? "")}`}
                                        className="text-[#1976d2] font-medium hover:underline"
                                      >
                                        {h.symbol ?? "—"}
                                      </Link>
                                      <span className="ml-1.5 text-[#888888] text-xs">{h.name ?? ""}</span>
                                      {h.source === "ocr" && !h.ocr_confirmed && (
                                        <span
                                          className="ml-1.5 cursor-pointer text-[10px] text-amber-400 hover:underline"
                                          title="OCR 导入，点击确认"
                                          onClick={(e) => { e.preventDefault(); setEditHolding(h); }}
                                        >
                                          未确认
                                        </span>
                                      )}
                                    </>
                                  )}
                                </td>
                                <td className="px-3 py-2 text-right text-white">
                                  {h.is_cash ? "1.00" : h.price_loaded === false ? (
                                    priceLoadTimedOut ? (
                                      <span className="text-xs text-[#666]" title="无法获取实时行情">暂无行情</span>
                                    ) : (
                                      <span className="inline-flex items-center gap-1 text-[#888]">
                                        <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-[#888] border-t-transparent" />
                                        <span className="text-xs">获取中</span>
                                      </span>
                                    )
                                  ) : `${priceSym}${(h.current_price ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`}
                                </td>
                                <td className="px-3 py-2 text-center">
                                  {h.is_cash ? (
                                    <span className="text-[#888888]">—</span>
                                  ) : h.price_loaded === false || todayPct == null ? (
                                    <span className="text-[#888888]">—</span>
                                  ) : (
                                    <span
                                      className={`inline-block min-w-[3rem] rounded px-1.5 py-0.5 text-xs ${
                                        todayPct === 0 ? "bg-white/5 text-[#888888]" : todayUp ? upBadge : downBadge
                                      }`}
                                    >
                                      {((todayPct ?? 0) >= 0 ? "+" : "")}{(todayPct ?? 0).toFixed(2)}%
                                    </span>
                                  )}
                                </td>
                                <td className="px-3 py-2 text-right text-white">
                                  {h.is_cash ? "1.00" : `${priceSym}${(h.cost_price ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`}
                                </td>
                                <td className="px-3 py-2 text-right text-white">
                                  {(h.quantity ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}
                                </td>
                                <td
                                  className={
                                    "px-3 py-2 text-right font-medium " +
                                    (currencyErr ? "text-[#ff4e33]" : "text-white " + (isConvertedRow ? "opacity-90 " : "") + (h.price_deviation_warn ? "border border-amber-500/30 rounded" : ""))
                                  }
                                  title={h.price_deviation_warn ? "识别价格与市场价偏差较大，请确认" : undefined}
                                >
                                  {currencyErr ? (
                                    <span className="cursor-pointer hover:underline" title="币种配置错误，点击右侧编辑修正" onClick={() => setEditHolding(h)}>--</span>
                                  ) : marketValDisplay == null ? (
                                    <span className="text-[#888888]">—</span>
                                  ) : (
                                    <span>{rowSym}{marketValDisplay.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                                  )}
                                </td>
                                <td className="px-3 py-2 text-right text-[#ff4e33]">
                                  {posPct.toFixed(1)}%
                                </td>
                                <td className="px-3 py-2 text-center">
                                  {h.is_cash ? (
                                    <span className="text-[#888888]">—</span>
                                  ) : h.price_loaded === false ? (
                                    <span className="text-[#888888]">—</span>
                                  ) : (
                                    <span
                                      className={`inline-block min-w-[3rem] rounded px-1.5 py-0.5 text-xs ${
                                        pnl === 0 ? "bg-white/5 text-[#888888]" : isUp ? upBadge : downBadge
                                      }`}
                                    >
                                      {(pnl >= 0 ? "+" : "")}
                                      {pnl.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                    </span>
                                  )}
                                </td>
                                <td className="px-3 py-2 text-center">
                                  {h.is_cash ? (
                                    <span className="text-[#888888]">—</span>
                                  ) : h.price_loaded === false || pct == null ? (
                                    <span className="text-[#888888]">—</span>
                                  ) : (
                                    <span
                                      className={`inline-block min-w-[3.5rem] rounded px-1.5 py-0.5 text-xs ${
                                        pct === 0 ? "bg-white/5 text-[#888888]" : isUp ? upBadge : downBadge
                                      }`}
                                    >
                                      {(pct >= 0 ? "+" : "")}{pct.toFixed(1)}%
                                    </span>
                                  )}
                                </td>
                                <td className="px-3 py-2">
                                  {!h.is_cash && (
                                  <button
                                    onClick={() => setEditHolding(h)}
                                    className="rounded p-1.5 text-[#1976d2] hover:bg-white/10 hover:text-white"
                                    title="编辑"
                                  >
                                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                    </svg>
                                  </button>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
            </>
          )}
        </div>
      </div>

      {/* 右侧抽屉入口：收缩时显示的竖条 */}
      {!chatDrawerOpen && (
        <button
          onClick={() => setChatDrawerOpen(true)}
          className="fixed right-0 top-1/2 -translate-y-1/2 z-40 flex h-24 w-10 items-center justify-center rounded-l-lg border border-l-0 border-white/10 bg-[#0a0a0a] text-[#888888] hover:bg-[#1a1a1a] hover:text-white hover:border-[#00e701]/50 transition-colors"
          title="Ask PFA"
        >
          <span className="origin-center -rotate-90 whitespace-nowrap text-xs font-medium">Ask PFA</span>
        </button>
      )}

      {/* 右侧抽屉：展开时滑入 */}
      <div
        className={`fixed right-0 top-12 z-50 flex h-[calc(100vh-48px)] w-full sm:max-w-[400px] md:max-w-[480px] flex-col border-l border-white/10 bg-[#0A0F1E] shadow-2xl transition-transform duration-300 ease-out ${
          chatDrawerOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
          <span className="text-sm font-medium text-white">Ask PFA</span>
          <div className="flex items-center gap-1">
            <button
              onClick={handleNewChat}
              className="rounded p-1.5 text-[#888888] hover:bg-white/10 hover:text-white"
              title="新建对话"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </button>
            <button
              onClick={() => {
                setHistoryPanelOpen(true);
                loadHistorySessions();
              }}
              className="rounded p-1.5 text-[#888888] hover:bg-white/10 hover:text-white"
              title="历史记录"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </button>
            <button
              onClick={handleCloseChatDrawer}
              className="rounded p-1.5 text-[#888888] hover:bg-white/10 hover:text-white"
              title="收起"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && !streaming && (
            <div className="space-y-4">
              <div className="rounded-lg border border-[#00e701]/20 bg-[#00e701]/5 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg">👋</span>
                  <span className="text-sm font-medium text-white">欢迎使用 Ask PFA</span>
                </div>
                <p className="text-xs text-[#b1bad3] leading-relaxed">
                  我是你的 AI 投研助手，可以帮你分析持仓风险、解读市场新闻、记录交易操作。试试下方的快捷按钮，或直接输入你的问题。
                </p>
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className="space-y-2">
              <ChatMessage
                content={m.content}
                role={m.role as "user" | "assistant"}
                isStreaming={streaming && i === messages.length - 1}
              />
              {m.type === "confirm" && m.payload && !dismissedConfirmIds.has(i) && (
                <TradeConfirmCard
                  payload={m.payload}
                  onConfirm={(confirmed) => {
                    setDismissedConfirmIds((prev) => new Set(prev).add(i));
                    refreshPortfolio();
                    const p = m.payload!;
                    const acc = confirmed?.account ?? p.account;
                    const content =
                      p.action === "remove"
                        ? `✅ 已删除 **${p.name}**(${p.symbol}) 自 ${acc}`
                        : `✅ 已记录 **${p.name}**(${p.symbol}) ${confirmed?.quantity ?? p.quantity}股 @¥${((confirmed?.cost_price ?? p.cost_price) || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })} 至 ${acc}`;
                    setMessages((prev) => [...prev, { role: "assistant", content }]);
                  }}
                  onCancel={() => setDismissedConfirmIds((prev) => new Set(prev).add(i))}
                />
              )}
            </div>
          ))}
        </div>
        <div className="sticky bottom-0 border-t border-white/5 p-4">
          <div className="mb-3 flex flex-wrap gap-2">
            {[
              { label: "分析持仓", prompt: "分析一下我的持仓风险" },
              { label: "扫描风险", prompt: "帮我看下今天有哪些异动" },
              { label: "生成周报", prompt: "基于最近新闻，给我一份调仓建议" },
            ].map(({ label, prompt }) => (
              <button
                key={label}
                type="button"
                onClick={() => handleSendMessage(prompt)}
                disabled={streaming}
                className="rounded-lg border border-[#1976d2]/30 bg-[#1976d2]/10 px-3 py-1.5 text-xs font-medium text-[#b1bad3] transition-colors hover:border-[#1976d2]/50 hover:bg-[#1976d2]/20 hover:text-white disabled:opacity-50"
              >
                {label}
              </button>
            ))}
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage(input);
            }}
            className="flex gap-2 rounded-full border border-white/10 bg-[#0a0a0a] px-4 py-3"
          >
            <input
              type="text"
              placeholder="输入问题..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={streaming}
              className="flex-1 bg-transparent text-sm text-white placeholder:text-[#888888] outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={streaming || !input.trim()}
              className="rounded-full bg-[#00e701] px-4 py-1.5 text-sm font-medium text-black disabled:opacity-50"
            >
              发送
            </button>
          </form>
        </div>
      </div>

      {/* 抽屉展开时的遮罩（点击关闭） */}
      {chatDrawerOpen && (
        <div
          className="fixed left-0 right-0 top-12 bottom-0 z-40 bg-black/30 md:bg-black/20"
          onClick={handleCloseChatDrawer}
          aria-hidden="true"
        />
      )}

      {/* 历史记录侧边栏（首页 Ask PFA：全局 + 所有个股） */}
      {historyPanelOpen && (
        <>
          <div
            className="fixed inset-0 z-[60] bg-black/50"
            onClick={() => setHistoryPanelOpen(false)}
            aria-hidden="true"
          />
          <div className="fixed right-0 top-12 z-[70] flex h-[calc(100vh-48px)] w-full max-w-[280px] sm:w-[280px] flex-col border-l border-white/10 bg-[#0a0a0a] shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
              <span className="text-sm font-medium text-white">历史记录</span>
              <button
                onClick={() => setHistoryPanelOpen(false)}
                className="rounded p-1.5 text-[#888888] hover:bg-white/10 hover:text-white"
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
                      key={`${s.type}-${s.session_id}`}
                      onClick={() => handleSelectHistorySession(s)}
                      className="w-full rounded-lg border border-white/5 bg-black/30 px-3 py-2 text-left text-sm transition-colors hover:border-[#1976d2]/30 hover:bg-[#1976d2]/10"
                    >
                      <div className="truncate text-white">
                        {s.type === "ticker" && s.symbol_name ? `${s.symbol_name} ` : ""}
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

      <EntryModal
        open={entryOpen}
        onClose={() => setEntryOpen(false)}
        onAdded={refreshPortfolio}
        initialTab={entryOpenTab}
      />
      <EditAccountsModal
        open={editAccountsOpen}
        onClose={() => setEditAccountsOpen(false)}
        onUpdated={refreshPortfolio}
      />
      <EditHoldingModal
        open={editHolding !== null}
        holding={editHolding}
        onClose={() => setEditHolding(null)}
        onSaved={refreshPortfolio}
      />

      {/* 清空持仓二次确认 */}
      {clearConfirmOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60" onClick={() => setClearConfirmOpen(false)}>
          <div
            className="w-full max-w-sm rounded-xl border border-white/10 bg-[#0a0a0a] p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="mb-3 text-lg font-semibold text-white">确认清空</h3>
            <p className="mb-6 text-sm text-[#b1bad3]">
              确定要清空所有账户的持仓数据吗？此操作不可逆。
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setClearConfirmOpen(false)}
                className="flex-1 rounded-lg border border-white/20 py-2.5 text-sm font-medium text-white hover:bg-white/5"
              >
                取消
              </button>
              <button
                onClick={async () => {
                  setClearConfirmOpen(false);
                  try {
                    const r = await apiFetch(`${API_BASE}/api/portfolio/clear`, { method: "POST" });
                    if (r.ok) refreshPortfolio();
                  } catch {}
                }}
                className="flex-1 rounded-lg py-2.5 text-sm font-medium text-black"
                style={{ backgroundColor: "#EF4444" }}
              >
                确定清空
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
